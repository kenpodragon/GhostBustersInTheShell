document.addEventListener('DOMContentLoaded', async () => {
  // Load and display config
  try {
    const resp = await fetch(chrome.runtime.getURL('config.json'));
    const config = await resp.json();
    document.getElementById('config-display').textContent = JSON.stringify(config, null, 2);

    // Test connection
    document.getElementById('test-btn').addEventListener('click', async () => {
      const statusEl = document.getElementById('status');
      statusEl.className = 'status';
      statusEl.textContent = 'Testing...';

      try {
        const url = `http://${config.backend_host}:${config.backend_port}/api/health`;
        const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
        const data = await r.json();
        if (data.status === 'ok') {
          statusEl.className = 'status ok';
          statusEl.textContent = `Connected! Backend: ${url}, DB: ${data.db || 'ok'}`;
        } else {
          throw new Error('Unexpected response');
        }
      } catch (err) {
        statusEl.className = 'status err';
        statusEl.textContent = `Connection failed: ${err.message}. Is Docker running?`;
      }
    });
  } catch (err) {
    document.getElementById('config-display').textContent = 'Error loading config.json: ' + err.message;
  }
});
