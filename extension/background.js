// 后台：开一个豆瓣标签页并注入抓取循环，把内容脚本抓到的海报存进下载目录。
// 数据流：popup(导入清单/控制) -> background(开标签页/下载) -> content.js(逐个检索+抓图)。
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "open-session") {
    startSession(msg)
      .then(r => sendResponse({ ok: true, version: r && r.version }))
      .catch(e => sendResponse({ ok: false, error: String(e) }));
    return true; // async
  }
  if (msg.type === "save-image") {
    chrome.downloads.download({
      url: msg.dataUrl,
      filename: "poster-wall/" + msg.file,
      conflictAction: "overwrite",
      saveAs: false,
    }, (id) => sendResponse({ ok: !!id }));
    return true;
  }
  if (msg.type === "save-results") {
    const blob = new Blob([JSON.stringify(msg.results, null, 1)], { type: "application/json" });
    const reader = new FileReader();
    reader.onload = () => chrome.downloads.download({
      url: reader.result,
      filename: "poster-wall/results.json",
      conflictAction: "overwrite",
      saveAs: false,
    });
    reader.readAsDataURL(blob);
    sendResponse({ ok: true });
    return false;
  }
});

async function startSession({ items, delaySec, onlyMissing }) {
  // 标签页常驻：内容脚本随页面存活，定时器不会被 MV3 service worker 冻结。
  // 旧的豆瓣标签页直接复用（导航会清掉旧注入），清单从消息里带过去。
  let tab = null;
  const tabs = await chrome.tabs.query({ url: "https://movie.douban.com/*" });
  if (tabs.length) {
    tab = tabs[0];
    await chrome.tabs.update(tab.id, { active: true, url: "https://movie.douban.com/" });
  } else {
    tab = await chrome.tabs.create({ url: "https://movie.douban.com/" });
  }
  await waitForComplete(tab.id);
  // 页面刚打开时注入；若已注入过，executeScript 会重复执行——content.js 有幂等守卫。
  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
  await sleep(1200); // 等登录态和页面就绪
  let version = null;
  try {
    const pong = await chrome.tabs.sendMessage(tab.id, { type: "ping" });
    version = pong && pong.version;
  } catch (_) { /* 旧版内容脚本不认识 ping */ }
  const queue = items && items.length ? items : (await chrome.storage.local.get("queue")).queue || [];
  await chrome.tabs.sendMessage(tab.id, { type: "start", items: queue, delaySec, onlyMissing });
  return { version };
}

function waitForComplete(tabId) {
  return new Promise(resolve => {
    chrome.tabs.get(tabId, t => {
      if (t.status === "complete") return resolve();
      chrome.tabs.onUpdated.addListener(function listener(id, info) {
        if (id === tabId && info.status === "complete") {
          chrome.tabs.onUpdated.removeListener(listener);
          resolve();
        }
      });
    });
  });
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
