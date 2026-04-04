// GBIS Background Service Worker
// Loads config.json on install/startup, caches API URLs, monitors backend health

let config = {
  backendUrl: 'http://localhost:8066',
  frontendUrl: 'http://localhost:5176'
};

async function loadConfig() {
  try {
    const resp = await fetch(chrome.runtime.getURL('config.json'));
    const data = await resp.json();
    config.backendUrl = `http://${data.backend_host}:${data.backend_port}`;
    config.frontendUrl = `http://${data.frontend_host}:${data.frontend_port}`;
    await chrome.storage.local.set({ config });
    console.log('GBIS config loaded:', config);
  } catch (err) {
    console.error('GBIS config load failed, using defaults:', err);
  }
}

async function checkHealth() {
  try {
    const resp = await fetch(`${config.backendUrl}/api/health`, {
      signal: AbortSignal.timeout(3000)
    });
    const data = await resp.json();
    const connected = data.status === 'ok';
    await chrome.storage.local.set({ connected });
    return connected;
  } catch {
    await chrome.storage.local.set({ connected: false });
    return false;
  }
}

chrome.runtime.onInstalled.addListener(async () => {
  await loadConfig();
  await checkHealth();
});

chrome.runtime.onStartup.addListener(async () => {
  await loadConfig();
  await checkHealth();
});

// Respond to messages from popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'getConfig') {
    sendResponse(config);
    return false;
  }
  if (msg.type === 'checkHealth') {
    checkHealth().then(sendResponse);
    return true; // async
  }
  return false;
});
