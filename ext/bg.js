// GhostTab bridge: b CLI -> native host (unix socket) -> this worker -> chrome.debugger (CDP)
const D = {};      // attached tabs: tabId -> {files, timer}
const IDLE = 20000; // detach after this long without commands (hides the "debugging" bar)
let port = null;

function connect() {
  try { port = chrome.runtime.connectNative('com.ghosttab.bridge'); } catch (e) { setTimeout(connect, 5000); return; }
  port.onMessage.addListener(m => handle(m).then(
    r => port && port.postMessage({id: m.id, ok: true, r}),
    e => port && port.postMessage({id: m.id, ok: false, e: String((e && e.message) || e)})));
  port.onDisconnect.addListener(() => { port = null; setTimeout(connect, 3000); });
}
connect();
chrome.runtime.onStartup.addListener(() => {});

const cdp = (tabId, m, p) => chrome.debugger.sendCommand({tabId}, m, p || {});

async function attach(tabId) {
  if (!D[tabId]) {
    try { await chrome.debugger.attach({tabId}, '1.3'); }
    catch (e) { if (!/already attached/i.test(e.message)) throw e; }
    D[tabId] = {};
    await cdp(tabId, 'Page.enable');
    await cdp(tabId, 'Emulation.setFocusEmulationEnabled', {enabled: true}).catch(() => {});
  }
  clearTimeout(D[tabId].timer);
  D[tabId].timer = setTimeout(() => chrome.debugger.detach({tabId}).catch(() => {}).finally(() => delete D[tabId]), IDLE);
}
chrome.debugger.onDetach.addListener(s => { if (D[s.tabId]) clearTimeout(D[s.tabId].timer); delete D[s.tabId]; });
chrome.debugger.onEvent.addListener(async (s, m, p) => {
  const d = D[s.tabId];
  if (m !== 'Page.fileChooserOpened' || !d || !d.files) return;
  const files = d.files; d.files = null;
  try { await cdp(s.tabId, 'DOM.setFileInputFiles', {files, backendNodeId: p.backendNodeId}); } catch (e) {}
  cdp(s.tabId, 'Page.setInterceptFileChooserDialog', {enabled: false}).catch(() => {});
});

async function ghost(create = true) {
  const {gw} = await chrome.storage.local.get('gw');
  if (gw) { try { const w = await chrome.windows.get(gw, {populate: true}); return w.tabs[0].id; } catch (e) {} }
  if (!create) return null;
  const w = await chrome.windows.create({url: 'about:blank', state: 'minimized', focused: false});
  await chrome.storage.local.set({gw: w.id});
  return w.tabs[0].id;
}

async function front() {
  const {gw} = await chrome.storage.local.get('gw');
  const ws = (await chrome.windows.getAll({populate: true, windowTypes: ['normal']})).filter(w => w.id !== gw);
  const w = ws.find(w => w.focused) || ws.sort((a, b) => (b.lastFocused || 0) - (a.lastFocused || 0))[0];
  if (!w) throw new Error('no browser window');
  return w.tabs.find(t => t.active).id;
}

function out(v) {
  if (v === undefined || v === null) return 'missing value';
  return typeof v === 'object' ? JSON.stringify(v) : String(v);
}

async function handle(m) {
  if (m.op === 'ping') return 'pong';
  if (m.op === 'closeghost') {
    const t = await ghost(false);
    if (t) { const tab = await chrome.tabs.get(t); await chrome.windows.remove(tab.windowId); }
    await chrome.storage.local.remove('gw');
    return 'closed';
  }
  const tabId = m.bg ? await ghost() : await front();
  if (m.op === 'nav') { await chrome.tabs.update(tabId, {url: m.url}); return 'ok'; }
  await attach(tabId);
  switch (m.op) {
    case 'eval': {
      const r = await cdp(tabId, 'Runtime.evaluate', {expression: 'window.__gtMain=1;' + m.code, returnByValue: true,
        allowUnsafeEvalBlockedByCSP: true, userGesture: true, replMode: true});
      if (r.exceptionDetails) {
        const ex = r.exceptionDetails.exception || {};
        if (ex.className === 'SyntaxError') return 'missing value';
        return 'ERR: ' + (ex.description || r.exceptionDetails.text).split('\n')[0];
      }
      return out(r.result.value);
    }
    case 'click': {
      const base = {x: m.x, y: m.y, button: 'left'};
      await cdp(tabId, 'Input.dispatchMouseEvent', {...base, type: 'mouseMoved', button: 'none'});
      for (let c = 1; c <= (m.n || 1); c++) {
        await cdp(tabId, 'Input.dispatchMouseEvent', {...base, type: 'mousePressed', clickCount: c});
        await cdp(tabId, 'Input.dispatchMouseEvent', {...base, type: 'mouseReleased', clickCount: c});
      }
      return 'ok';
    }
    case 'key': {
      const k = {key: m.key, code: m.code, windowsVirtualKeyCode: m.kc, nativeVirtualKeyCode: m.kc, modifiers: m.mod || 0};
      if (m.commands) k.commands = m.commands;
      await cdp(tabId, 'Input.dispatchKeyEvent', {...k, type: m.text ? 'keyDown' : 'rawKeyDown', text: m.text});
      await cdp(tabId, 'Input.dispatchKeyEvent', {...k, type: 'keyUp'});
      return 'ok';
    }
    case 'type': await cdp(tabId, 'Input.insertText', {text: m.text}); return 'ok';
    case 'files': {
      const r = await cdp(tabId, 'Runtime.evaluate', {expression: m.expr});
      if (!r.result.objectId) throw new Error('no element for ' + m.expr);
      await cdp(tabId, 'DOM.setFileInputFiles', {files: m.files, objectId: r.result.objectId});
      return 'ok';
    }
    case 'arm':
      D[tabId].files = m.files;
      await cdp(tabId, 'Page.setInterceptFileChooserDialog', {enabled: true});
      return 'ok';
    case 'armed': return D[tabId].files ? 'waiting' : 'used';
    case 'shot': return (await cdp(tabId, 'Page.captureScreenshot', {format: 'png'})).data;
  }
  throw new Error('unknown op ' + m.op);
}
