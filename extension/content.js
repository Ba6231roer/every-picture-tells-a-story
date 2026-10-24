// 内容脚本：跑在 movie.douban.com 标签页里，逐个"检索→选条目→抓海报→回传下载"。
// 同源 fetch 自动带上你的豆瓣登录态；每部之间按设定间隔等待，避免触发限流。
(() => {
  if (window.__pfwInjected) return;   // 幂等：重复注入不叠加
  window.__pfwInjected = true;

  const state = {
    queue: [], delaySec: 6, onlyMissing: true,
    running: false, index: 0, results: [], progress: { total: 0, done: 0, ok: 0, fail: 0 },
  };

  // 豆瓣影单 → 待抓队列（标题+条目号；有 subject 的条目走"条目号直抓"，最可靠）
  const safeFile = (t, y) => {
    const map = { "\\": "／", "/": "／", ":": "：", "*": "＊", "?": "？", '"': "＂", "<": "＜", ">": "＞", "|": "｜" };
    const s = (t || "untitled").replace(/[\\/:*?"<>|]/g, ch => map[ch]).trim().replace(/\.+$/, "");
    return (s || "untitled") + "_" + (y || "未知") + ".jpg";
  };

  async function crawlDoubanList(status) {
    const items = [];
    const seen = new Set();
    for (let start = 0; start < 400; start += 20) {
      log(`解析影单：第 ${start / 20 + 1} 页，已得 ${items.length} 部…`);
      const r = await fetch(`https://movie.douban.com/mine?status=${status}&start=${start}`,
                            { credentials: "include" });
      if (!r.ok) throw new Error("影单页 HTTP " + r.status);
      const doc = new DOMParser().parseFromString(await r.text(), "text/html");
      const nodes = [...doc.querySelectorAll(".item")];
      if (!nodes.length) {
        if (start === 0) throw new Error("影单页结构未识别（可能未登录，或豆瓣改版）");
        break;
      }
      for (const n of nodes) {
        const a = n.querySelector("a[href*='/subject/']");
        if (!a) continue;
        const m = a.getAttribute("href").match(/subject\/(\d+)/);
        if (!m || seen.has(m[1])) continue;
        seen.add(m[1]);
        const title = a.textContent.replace(/\s+/g, " ").trim() || ("豆瓣条目 " + m[1]);
        const starEl = n.querySelector("[class*='allstar']");
        const starM = starEl ? String(starEl.className).match(/allstar(\d+)/) : null;
        items.push({ title, subject: m[1],
                     rating: starM ? Math.round(+starM[1] / 10) + "星" : null,
                     file: safeFile(title, null) });
      }
      if (!doc.querySelector(".next a")) break;
      await sleep(1200);
    }
    return items;
  }

  chrome.runtime.onMessage.addListener((msg, _s, sendResponse) => {
    if (msg.type === "ping") { sendResponse({ version: 2 }); return false; }
    if (msg.type === "start") {
      state.delaySec = Math.max(3, msg.delaySec || 6);
      state.onlyMissing = msg.onlyMissing !== false;
      state.index = 0;
      state.results = [];
      state.running = true;
      save();
      if (msg.mode === "douban") {
        crawlDoubanList(msg.status || "done").then(items => {
          if (!items.length) { log("影单为空或未登录豆瓣"); state.running = false; save(); return; }
          state.queue = items;
          state.progress = { total: items.length, done: 0, ok: 0, fail: 0 };
          log(`影单解析完成：${items.length} 部，开始抓取`);
          save();
          loop();
        }).catch(e => { log("影单解析失败：" + e.message); state.running = false; save(); });
      } else {
        state.queue = msg.items || [];
        state.progress = { total: state.queue.length, done: 0, ok: 0, fail: 0 };
        loop();
      }
      sendResponse({ ok: true });
    }
    if (msg.type === "pause") { state.running = false; save(); sendResponse({ ok: true }); }
    if (msg.type === "resume") { if (!state.running) { state.running = true; save(); loop(); } sendResponse({ ok: true }); }
    if (msg.type === "export") {
      chrome.runtime.sendMessage({ type: "save-results", results: { done: doneList(), failed: failedList() } });
      sendResponse({ ok: true });
    }
    if (msg.type === "status") sendResponse(state.progress);
    return false;
  });

  const norm = s => (s || "").toLowerCase()
    .replace(/\s*[(（][^()（）]*[)）]\s*$/g, "")
    .replace(/[\s·・.\-_:：,，。!！?？'’"”/]+/g, "");
  // 港台译名连接词折叠："007之黄金眼" vs 清单里的 "007黄金眼"
  const fold = s => norm(s).replace(/[之的]/g, "");

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const save = () => chrome.storage.local.set({ progress: state.progress, last: lastLine() });
  const doneList = () => state.results.filter(r => r.ok);
  const failedList = () => state.results.filter(r => !r.ok);
  let lastText = "待开始";
  const lastLine = () => lastText;

  function log(t) { lastText = t; save(); }

  async function loop() {
    while (state.running && state.index < state.queue.length) {
      const item = state.queue[state.index];
      try {
        const r = await grabOne(item);
        state.results.push(r);
        r.ok ? state.progress.ok++ : state.progress.fail++;
      } catch (e) {
        state.results.push({ title: item.title, ok: false, reason: String(e).slice(0, 120) });
        state.progress.fail++;
      }
      state.progress.done = ++state.index;
      log(`[${state.progress.done}/${state.progress.total}] ` +
          (state.results[state.results.length - 1].ok ? "✓ " : "✗ ") + item.title);
      save();
      if (state.running && state.index < state.queue.length) {
        await sleep(state.delaySec * 1000 + Math.random() * 2000);
      }
    }
    if (state.index >= state.queue.length) {
      state.running = false;
      log(`完成：${state.progress.ok} 成功 / ${state.progress.fail} 失败，点击"导出结果"`);
      save();
    }
  }

  async function api(url) {
    const r = await fetch(url, { credentials: "include" });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  function pick(cands, title, year) {
    const nq = norm(title), fq = fold(title);
    let best = null, bestScore = 0;
    for (const c of cands) {
      if (!c.title) continue;
      const ct = norm(c.title), cf = fold(c.title);
      let s = 0;
      if (ct === nq || (fq && cf === fq)) s = 100;
      else if (ct.startsWith(nq) || nq.startsWith(ct) || (fq && (cf.startsWith(fq) || fq.startsWith(cf)))) s = 80;
      else if (nq.includes(ct) || ct.includes(nq) || (fq && (fq.includes(cf) || cf.includes(fq)))) s = 60;
      if (!s) continue;
      if (year && c.year) s += Math.max(0, 12 - Math.abs(+c.year - year) * 2);
      if (s > bestScore && c.img) { best = c; bestScore = s; }
    }
    return bestScore >= 60 ? best : null;
  }

  // 豆瓣 suggest 对整名查询的首条基本就是对的（实测 007黄金眼→007之黄金眼、
  // Baby Walkure→辣妹刺客 各只返回 1 条）：评分不中时取第一条带图的，标记 loose 供抽查。
  function firstWithImg(cands) {
    return cands.find(c => c.img) || null;
  }

  // 指定条目号直抓：suggest 查不到的冷门片，清单里带 subject（豆瓣条目数字 ID），
  // 内容脚本带登录态抓条目页解析 og:image。
  async function fromSubject(id) {
    try {
      const r = await fetch(`https://movie.douban.com/subject/${id}/`, { credentials: "include" });
      const html = await r.text();
      const m = html.match(/og:image" content="([^"]+)"/) || html.match(/og:image[^>]*content="([^"]+)"/);
      return m ? { id: String(id), img: m[1].replace("/s_ratio_poster/", "/photo/") } : null;
    } catch (_) {
      return null;
    }
  }

  async function grabOne(item) {
    let c = null, loose = false;
    if (item.subject) {
      c = await fromSubject(item.subject);
      if (!c) return { title: item.title, ok: false, reason: "条目页解析失败 " + item.subject };
    }
    if (!c) {
      const q = encodeURIComponent(item.title);
      const data = await api(`https://movie.douban.com/j/subject_suggest?q=${q}`);
      if (!Array.isArray(data) || !data.length) return { title: item.title, ok: false, reason: "豆瓣无匹配" };
      c = pick(data, item.title, item.year);
      if (!c) {
        c = firstWithImg(data);
        loose = true;
      }
      if (!c) return { title: item.title, ok: false, reason: "候选都没有海报图" };
    }
    const bytes = await fetchImage(c.img).catch(() => null);
    if (!bytes) return { title: item.title, ok: false, reason: "海报下载失败 " + (c.title || item.title) };
    const dataUrl = "data:image/jpeg;base64," + btoaBytes(bytes);
    // 文件名直接用海报墙的标准名（导出清单时带上的 item.file），合并脚本按名字对应
    const file = item.file || ((c.id || "x" + Date.now()) + ".jpg");
    const resp = await chrome.runtime.sendMessage({ type: "save-image", dataUrl, file });
    if (!resp || !resp.ok) return { title: item.title, ok: false, reason: "保存失败" };
    return { title: item.title, ok: true, loose, matched: c.title || item.title, doubanId: c.id,
             doubanTitle: c.title || item.title, doubanYear: c.year || item.year, file };
  }

  async function fetchImage(url) {
    if (!url) return null;
    const r = await fetch(url, { credentials: "omit" });
    if (!r.ok) return null;
    const buf = await r.arrayBuffer();
    return buf.byteLength > 4000 && buf.byteLength < 8e6 ? new Uint8Array(buf) : null;
  }

  function btoaBytes(u8) {
    let s = "";
    const chunk = 0x8000;
    for (let i = 0; i < u8.length; i += chunk) {
      s += String.fromCharCode.apply(null, u8.subarray(i, i + chunk));
    }
    return btoa(s);
  }
})();
