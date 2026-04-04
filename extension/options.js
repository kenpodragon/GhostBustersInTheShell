document.addEventListener('DOMContentLoaded', async () => {
  // Load and display config
  try {
    const resp = await fetch(chrome.runtime.getURL('config.json'));
    const config = await resp.json();
    document.getElementById('config-display').textContent = JSON.stringify(config, null, 2);

    // Test connection via background worker (has host_permissions for localhost)
    document.getElementById('test-btn').addEventListener('click', () => {
      const statusEl = document.getElementById('status');
      statusEl.className = 'status';
      statusEl.textContent = 'Testing...';

      chrome.runtime.sendMessage({ type: 'checkHealth' }, (connected) => {
        if (connected) {
          const url = `http://${config.backend_host}:${config.backend_port}/api/health`;
          statusEl.className = 'status ok';
          statusEl.textContent = `Connected! Backend: ${url}`;
        } else {
          statusEl.className = 'status err';
          statusEl.textContent = 'Connection failed. Is Docker running?';
        }
      });
    });
  } catch (err) {
    document.getElementById('config-display').textContent = 'Error loading config.json: ' + err.message;
  }
});
