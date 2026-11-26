const endpoint = 'http://127.0.0.1:18796';
const hosts = new Set(['open.spotify.com','music.apple.com','music.youtube.com','www.youtube.com','youtube.com']);
let epoch = 0;
async function configuration() {
  const config = await chrome.storage.local.get(['token','client']);
  if (!config.client) { config.client = crypto.randomUUID(); await chrome.storage.local.set({ client: config.client }); }
  return config;
}
async function post(value) {
  const config = await configuration();
  if (!/^[\w-]{43}$/.test(config.token || '')) return;
  const response = await fetch(`${endpoint}/events?client=${config.client}`, { method: 'POST', headers: { Authorization: `Bearer ${config.token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(value), signal: AbortSignal.timeout(5000) });
  if (!response.ok) throw new Error('Karen no aceptó la conexión.');
}
chrome.runtime.onMessage.addListener((value, sender, respond) => {
  let host; try { host = new URL(sender.url).hostname; } catch { return; }
  if (!sender.tab || !hosts.has(host) || value.type !== 'media') return;
  // The authenticated extension supplies only reports from its own allowed tab.
  const message = value.session ? { type: 'session', tabId: sender.tab.id, session: { ...value.session, domain: host } } : { type: 'remove', tabId: sender.tab.id };
  void post(message).then(() => respond({ ok: true })).catch(() => respond({ ok: false }));
  return true;
});
chrome.tabs.onRemoved.addListener(tabId => { void post({ type: 'remove', tabId }).catch(() => {}); });
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
async function listen() {
  const current = ++epoch;
  while (current === epoch) {
    const config = await configuration();
    if (!/^[\w-]{43}$/.test(config.token || '')) return;
    try {
      const response = await fetch(`${endpoint}/commands?client=${config.client}`, { headers: { Authorization: `Bearer ${config.token}` }, signal: AbortSignal.timeout(28000) });
      if (!response.ok) throw new Error();
      for (const request of await response.json()) {
        const tabId = Number(request.sessionId.split(':').at(-1));
        let ok = false;
        try { ok = (await chrome.tabs.sendMessage(tabId, { type: 'control', request })).ok === true; } catch {}
        await post({ type: 'result', id: request.id, ok });
      }
    } catch { await new Promise(resolve => setTimeout(resolve, 5000)); }
  }
}
chrome.storage.onChanged.addListener(changes => { if (changes.token) void listen(); });
chrome.runtime.onStartup.addListener(() => { void listen(); });
void listen();
