document.getElementById('pair').addEventListener('submit', async event => {
  event.preventDefault(); const token = document.getElementById('token').value.trim();
  if (!/^[\w-]{43}$/.test(token)) return;
  await chrome.storage.local.set({ token }); document.getElementById('token').value = '';
  document.getElementById('status').textContent = 'Código guardado. Activa Música en Karen y recarga la pestaña multimedia.';
});
document.getElementById('forget').addEventListener('click', async () => { await chrome.storage.local.remove('token'); document.getElementById('status').textContent = 'Código eliminado.'; });
