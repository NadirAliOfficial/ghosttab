// Browser-only VPN switch (Chrome): whole browser or chosen sites through a local SOCKS exit. Never the Mac.
const EXITS = {US: 1081, CA: 1082};
const vget = async () => Object.assign({all: '', sites: {}}, (await chrome.storage.local.get('vpn')).vpn);
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; } };

async function vpnApply() {
  const v = await vget();
  if (!v.all && !Object.keys(v.sites).length) await chrome.proxy.settings.clear({scope: 'regular'});
  else {
    const pac = `var S=${JSON.stringify(Object.fromEntries(Object.entries(v.sites).map(([h, c]) => [h, EXITS[c]])))},A=${EXITS[v.all] || 0};
function FindProxyForURL(u,h){if(isPlainHostName(h)||h=='127.0.0.1'||h=='localhost')return 'DIRECT';
for(var d=h;d;d=d.indexOf('.')<0?'':d.slice(d.indexOf('.')+1)){if(S[d])return 'SOCKS5 127.0.0.1:'+S[d]}
return A?'SOCKS5 127.0.0.1:'+A:'DIRECT'}`;
    await chrome.proxy.settings.set({scope: 'regular', value: {mode: 'pac_script', pacScript: {data: pac}}});
  }
  for (const t of await chrome.tabs.query({})) vpnBadge(t);
}

async function vpnBadge(t) {
  if (!t || !t.id) return;
  const v = await vget(), h = host(t.url || '');
  let c = '';
  for (let d = h; d && !c; d = d.includes('.') ? d.slice(d.indexOf('.') + 1) : '') c = v.sites[d] || '';
  c = c || v.all;
  chrome.action.setBadgeText({tabId: t.id, text: c}).catch(() => {});
  chrome.action.setBadgeBackgroundColor({tabId: t.id, color: c === 'US' ? '#2563eb' : '#dc2626'}).catch(() => {});
  chrome.action.setTitle({tabId: t.id, title: 'VPN: ' + (c || 'off')}).catch(() => {});
}

async function vpnSet(cmd) {  // from b: 'US' | 'CA' | 'off' | '' (status)
  const v = await vget();
  if (cmd) { v.all = EXITS[String(cmd).toUpperCase()] ? String(cmd).toUpperCase() : ''; await chrome.storage.local.set({vpn: v}); await vpnApply(); }
  return 'all: ' + (v.all || 'off') + '; sites: ' + (Object.entries(v.sites).map(([h, c]) => h + '=' + c).join(', ') || 'none');
}

chrome.runtime.onMessage.addListener((m, _, reply) => {
  if (m.vpn === undefined) return;
  (async () => {
    const v = await vget();
    if (m.vpn === 'all') v.all = m.exit || '';
    if (m.vpn === 'site' && m.host) { if (m.exit) v.sites[m.host] = m.exit; else delete v.sites[m.host]; }
    await chrome.storage.local.set({vpn: v});
    await vpnApply();
    reply(await vget());
  })();
  return true;
});
chrome.tabs.onActivated.addListener(i => chrome.tabs.get(i.tabId).then(vpnBadge).catch(() => {}));
chrome.tabs.onUpdated.addListener((id, ch, t) => { if (ch.url || ch.status) vpnBadge(t); });
// Brave and other browsers: no VPN button (Chrome only)
(async () => {
  const brave = navigator.brave && await navigator.brave.isBrave().catch(() => false);
  if (brave) { chrome.action.disable(); chrome.action.setPopup({popup: ''}); chrome.proxy.settings.clear({scope: 'regular'}); }
  else vpnApply();
})();
