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

// place 'tab': agent tabs sit in the user's own window, never activated, in a "GhostTab" group (he can watch them)
// place 'win': one minimized window (old behaviour)
async function place() { return (await chrome.storage.local.get('place')).place || 'tab'; }

// each b session (Claude session) gets its own tabs and its own group; state keys are suffixed with the session id
const K = (m, k) => k + ':' + (m.s || 'default');
async function sget(m, k) { return (await chrome.storage.local.get(K(m, k)))[K(m, k)]; }
async function sset(m, o) { const x = {}; for (const k in o) x[K(m, k)] = o[k]; await chrome.storage.local.set(x); }
const COLORS = ['purple', 'blue', 'green', 'orange', 'cyan', 'pink', 'red', 'yellow'];

async function gtabs(m) {
  const live = [];
  for (const id of (await sget(m, 'gt')) || []) { try { await chrome.tabs.get(id); live.push(id); } catch (e) {} }
  return live;
}

async function mainWin() {
  const ws = (await chrome.windows.getAll({windowTypes: ['normal']})).filter(w => w.state !== 'minimized' && !w.incognito);
  const w = ws.find(w => w.focused) || ws[0];
  return w ? w.id : (await chrome.windows.create({url: 'about:blank', state: 'minimized', focused: false})).id;
}

async function addTab(m, url) {
  const gt = await gtabs(m);
  const windowId = gt.length ? (await chrome.tabs.get(gt[0])).windowId : await mainWin();
  const t = await chrome.tabs.create({windowId, url: url || 'about:blank', active: false});
  try {
    const gg = await sget(m, 'gg');
    let groupId;
    try { groupId = await chrome.tabs.group({tabIds: [t.id], ...(gg ? {groupId: gg} : {createProperties: {windowId}})}); }
    catch (e) { groupId = await chrome.tabs.group({tabIds: [t.id], createProperties: {windowId}}); }
    await sset(m, {gg: groupId});
    const name = m.name || 'GhostTab';
    const color = COLORS[[...name].reduce((h, c) => h * 31 + c.charCodeAt(0) >>> 0, 7) % COLORS.length];
    if (chrome.tabGroups) await chrome.tabGroups.update(groupId, {title: name, color, collapsed: false});
  } catch (e) {}
  gt.push(t.id);
  await sset(m, {gt, gcur: t.id});
  return t.id;
}

async function ghost(m, create = true) {
  if (await place() === 'tab') {
    const gt = await gtabs(m), gcur = await sget(m, 'gcur');
    if (gt.includes(gcur)) return gcur;
    if (gt.length) { await sset(m, {gcur: gt[gt.length - 1]}); return gt[gt.length - 1]; }
    return create ? addTab(m) : null;
  }
  const gw = await sget(m, 'gw');
  if (gw) { try { const w = await chrome.windows.get(gw, {populate: true}); return (w.tabs.find(t => t.active) || w.tabs[0]).id; } catch (e) {} }
  if (!create) return null;
  const w = await chrome.windows.create({url: 'about:blank', state: 'minimized', focused: false});
  await sset(m, {gw: w.id});
  return w.tabs[0].id;
}

async function front() {
  const all = await chrome.storage.local.get(null);
  const gws = Object.keys(all).filter(k => k.startsWith('gw')).map(k => all[k]);
  const ws = (await chrome.windows.getAll({populate: true, windowTypes: ['normal']})).filter(w => !gws.includes(w.id));
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
  if (m.op === 'place') {
    if (m.where) await chrome.storage.local.set({place: m.where});
    return place();
  }
  if (m.op === 'closeghost') {
    for (const id of await gtabs(m)) await chrome.tabs.remove(id).catch(() => {});
    const gw = await sget(m, 'gw');
    if (gw) await chrome.windows.remove(gw).catch(() => {});
    await chrome.storage.local.remove(['gw', 'gt', 'gcur', 'gg'].map(k => K(m, k)));
    return 'closed';
  }
  if (m.op === 'reload') { setTimeout(() => chrome.runtime.reload(), 100); return 'reloading'; }
  if (m.bg && /^(tabs|newtab|tab|closetab)$/.test(m.op) && await place() === 'tab') {
    await ghost(m);
    const gt = await gtabs(m), gcur = await sget(m, 'gcur');
    const tabs = await Promise.all(gt.map(id => chrome.tabs.get(id)));
    if (m.op === 'tabs') return tabs.map((t, i) => (i + 1) + ' | ' + t.title + ' | ' + t.url).join('\n') + '\nactive: ' + (gt.indexOf(gcur) + 1);
    if (m.op === 'newtab') { await addTab(m, m.url); return 'ok'; }
    if (m.op === 'tab') { const id = gt[m.i - 1]; if (!id) throw new Error('no tab ' + m.i); await sset(m, {gcur: id}); return 'ok'; }
    if (m.op === 'closetab') {
      if (gt.length < 2) throw new Error('last agent tab; use go instead');
      await chrome.tabs.remove(gcur);
      await sset(m, {gt: gt.filter(i => i !== gcur), gcur: gt.filter(i => i !== gcur).pop()});
      return 'ok';
    }
  }
  const tabId = m.bg ? await ghost(m) : await front();
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
    case 'resource': {
      // the browser's own network stack with the user's cookies, no CORS; returns base64 chunks
      const ft = await cdp(tabId, 'Page.getFrameTree');
      const r = await cdp(tabId, 'Network.loadNetworkResource', {frameId: ft.frameTree.frame.id, url: m.url, options: {disableCache: false, includeCredentials: true}});
      if (!r.resource.success) throw new Error('HTTP ' + (r.resource.httpStatusCode || r.resource.netErrorName));
      const parts = [];
      for (;;) {
        const c = await cdp(tabId, 'IO.read', {handle: r.resource.stream, size: 1 << 20});
        parts.push(c.base64Encoded ? c.data : btoa(unescape(encodeURIComponent(c.data))));
        if (c.eof) break;
      }
      cdp(tabId, 'IO.close', {handle: r.resource.stream}).catch(() => {});
      return JSON.stringify(parts);
    }
    case 'shot': return (await cdp(tabId, 'Page.captureScreenshot', {format: 'png'})).data;
  }
  throw new Error('unknown op ' + m.op);
}
