const draw = v => {
  document.querySelectorAll('[data-a]').forEach(b => b.classList.toggle('on', (v.all || '') === b.dataset.a));
  const ip = document.getElementById('ip'); ip.textContent = 'checking…';
  fetch('https://ipinfo.io/json', {cache: 'no-store'}).then(r => r.json())
    .then(r => ip.textContent = r.country + ' · ' + r.ip)
    .catch(() => ip.textContent = 'VPN not running: open the Chrome US app once');
};
chrome.storage.local.get('vpn', r => draw(Object.assign({all: '', sites: {}}, r.vpn)));
document.querySelectorAll('[data-a]').forEach(b => b.onclick = () => chrome.runtime.sendMessage({vpn: 'all', exit: b.dataset.a}, draw));
