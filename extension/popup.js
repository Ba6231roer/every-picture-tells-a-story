// popup：导入清单、控制抓取、显示进度。
const $ = s => document.querySelector(s);
let queue = [];

$("#file").addEventListener("change", e => {
  const f = e.target.files[0];
  if (!f) return;
  f.text().then(t => {
    const data = JSON.parse(t);
    queue = data.items || data;    // 兼容 {items:[...]} 或裸数组
    if (!Array.isArray(queue) || !queue.length) throw new Error("清单为空");
    const noFile = queue.filter(x => !x.file).length;
    $("#queueName").textContent = `已导入 ${queue.length} 部：${f.name}` +
      (noFile ? `（${noFile} 条缺 file 字段=旧版清单，保存会用豆瓣ID名。请重跑 export_for_extension.py）` : "");
    $("#start").disabled = false;
  }).catch(err => { $("#queueName").textContent = "导入失败：" + err.message; });
});

$("#start").onclick = async () => {
  const src = document.querySelector("input[name=src]:checked").value;
  const base = { delaySec: +$("#delay").value || 6, onlyMissing: $("#onlyMissing").checked };
  let msg;
  if (src === "douban") {
    // 豆瓣影单模式：清单由内容脚本现场解析（标题+条目号），无需文件
    msg = { type: "open-session", mode: "douban", status: $("#status").value, ...base };
  } else {
    if (!queue.length) { log("先导入清单文件"); return; }
    // 清单直接随消息传给内容脚本（不走 storage 中转，旧导入不会再被用到）
    await chrome.storage.local.set({ queue, progress: { total: queue.length, done: 0, ok: 0, fail: 0 } });
    msg = { type: "open-session", items: queue, ...base };
  }
  const resp = await chrome.runtime.sendMessage(msg);
  if (resp && resp.ok) {
    log(src === "douban" ? "正在解析豆瓣影单…" : "已连接豆瓣标签页，注入内容脚本 " +
        (resp.version ? "v" + resp.version : "") +
        (resp.version && +resp.version >= 2 ? "" : " ⚠ 内容脚本是旧版：请到 chrome://extensions 重新加载插件"));
  } else {
    log("启动失败：" + (resp && resp.error));
  }
  setButtons(true);
};

$("#pause").onclick = () => sendToTab({ type: "pause" });
$("#resume").onclick = () => sendToTab({ type: "resume" });
$("#export").onclick = () => sendToTab({ type: "export" });

function sendToTab(msg) {
  chrome.tabs.query({ url: "https://movie.douban.com/*" }, tabs => {
    if (!tabs.length) { log("豆瓣标签页不在了，重新点开始"); return; }
    chrome.tabs.sendMessage(tabs[0].id, msg, () => void chrome.runtime.lastError);
  });
}

function setButtons(running) {
  $("#start").disabled = running;
  $("#pause").disabled = !running;
  $("#resume").disabled = !running;
  $("#export").disabled = !running;
}

chrome.storage.onChanged.addListener((ch, area) => {
  if (area !== "local" || !ch.progress) return;
  const p = ch.progress.newValue || {};
  $("#bar").firstElementChild.style.width = p.total ? (100 * p.done / p.total) + "%" : "0";
  if (ch.last) $("#log").textContent = ch.last.newValue;
});

chrome.storage.local.get(["progress", "last"], ({ progress, last }) => {
  if (progress && progress.total) {
    $("#bar").firstElementChild.style.width = (100 * progress.done / progress.total) + "%";
    setButtons(progress.done < progress.total);
  }
  if (last) $("#log").textContent = last;
});

function log(t) { $("#log").textContent = t; }
