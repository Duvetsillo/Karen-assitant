// Reads Media Session + site metadata. No audio capture, injection or remote API.
const host = location.hostname;
const nextSelectors = ['[data-testid="control-button-skip-forward"]','ytmusic-player-bar .next-button','button.ytp-next-button'];
const previousSelectors = ['[data-testid="control-button-skip-back"]','ytmusic-player-bar .previous-button','button.ytp-prev-button'];
const button = selectors => selectors.map(s => document.querySelector(s)).find(e => e && !e.disabled && e.getAttribute('aria-disabled') !== 'true');
function snapshot() {
  if (host.includes('youtube.com') && document.querySelector('.html5-video-player.ad-showing')) return;
  const media = [...document.querySelectorAll('audio,video')].find(m => !m.paused) || document.querySelector('audio,video');
  if (!media) return;
  const metadata = navigator.mediaSession?.metadata;
  const meta = selector => document.querySelector(selector)?.content || '';
  const title = metadata?.title || meta('meta[property="og:title"]');
  if (!title) return;
  const artist = metadata?.artist || undefined, album = metadata?.album || undefined;
  const videoId = new URL(location.href).searchParams.get('v') || undefined;
  let category;
  if (host === 'open.spotify.com') {
    const link = document.querySelector('[data-testid="nowplaying-track-link"]')?.getAttribute('href') || '';
    category = link.includes('/track/') ? 'music' : link.includes('/episode/') || link.includes('/show/') ? 'podcast' : 'unknown';
  } else if (host.includes('youtube.com')) category = meta('meta[itemprop="genre"]') || undefined;
  const controls = ['play','pause','volume'];
  if (Number.isFinite(media.duration) && media.duration > 0) controls.push('seek');
  if (button(nextSelectors)) controls.push('next');
  if (button(previousSelectors)) controls.push('previous');
  const identity = `${host}:${videoId || location.pathname}:${title}:${artist || ''}`;
  return { sessionId: 'placeholder', source: 'browser', trackId: identity.slice(0,180), title: title.slice(0,500), artist, album,
    domain: host, videoId, category, mediaType: 'music', status: media.paused ? 'paused' : 'playing',
    duration: Number.isFinite(media.duration) ? media.duration : undefined, position: media.currentTime,
    controls, volume: media.volume, updatedAt: Date.now() };
}
let timer, lastSent = 0;
function publish() {
  if (timer) return;
  timer = setTimeout(() => { timer = undefined; lastSent = Date.now(); void chrome.runtime.sendMessage({ type: 'media', session: snapshot() }).catch(() => {}); }, 250);
}
for (const event of ['play','pause','ended','loadedmetadata','durationchange','seeked','volumechange']) document.addEventListener(event, publish, true);
document.addEventListener('timeupdate', () => { if (Date.now() - lastSent > 10000) publish(); }, true);
const observer = new MutationObserver(() => { if (Date.now() - lastSent > 2000) publish(); });
observer.observe(document.documentElement, { childList: true, subtree: true });
// Keep paused metadata from surviving tab/extension disconnects indefinitely.
const heartbeat = setInterval(() => { if (document.querySelector('audio,video')) publish(); }, 15000);
window.addEventListener('pagehide', () => { clearInterval(heartbeat); clearTimeout(timer); observer.disconnect(); void chrome.runtime.sendMessage({ type: 'media' }).catch(() => {}); });
chrome.runtime.onMessage.addListener((value, _sender, respond) => {
  if (value.type !== 'control') return;
  void (async () => {
    const request = value.request, current = snapshot();
    if (!current || current.trackId !== request.trackId || !current.controls.includes(request.action)) return { ok: false };
    const media = [...document.querySelectorAll('audio,video')].find(m => !m.paused) || document.querySelector('audio,video');
    if (request.action === 'play') await media.play();
    else if (request.action === 'pause') media.pause();
    else if (request.action === 'seek' && Number.isFinite(request.value) && request.value >= 0 && request.value <= media.duration) media.currentTime = request.value;
    else if (request.action === 'volume' && Number.isFinite(request.value) && request.value >= 0 && request.value <= 1) media.volume = request.value;
    else if (request.action === 'next') { const target = button(nextSelectors); if (!target) return { ok: false }; target.click(); }
    else if (request.action === 'previous') { const target = button(previousSelectors); if (!target) return { ok: false }; target.click(); }
    else return { ok: false };
    publish(); return { ok: true };
  })().then(respond).catch(() => respond({ ok: false }));
  return true;
});
publish();
