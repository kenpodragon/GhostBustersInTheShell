// GBIS Chrome Extension — Popup Logic

let config = null;
let aiEnabled = false;
let currentMode = 'scan';
let lastAnalysis = null;
let lastText = null;

// --- Init ---

document.addEventListener('DOMContentLoaded', async () => {
  await init();
  bindEvents();
});

async function init() {
  // Load config from background
  config = await sendMessage({ type: 'getConfig' });
  if (!config) {
    config = { backendUrl: 'http://localhost:8066', frontendUrl: 'http://localhost:5176' };
  }

  // Set dashboard link
  document.getElementById('dashboard-link').href = config.frontendUrl;
  document.getElementById('dashboard-link').addEventListener('click', (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: config.frontendUrl });
  });

  // Options button
  document.getElementById('options-btn').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Check backend health
  await updateConnectionStatus();

  // Check AI status + load profiles
  await checkAiStatus();
  await loadVoiceProfiles();
}

function sendMessage(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, resolve);
  });
}

async function apiCall(path, options = {}) {
  const url = `${config.backendUrl}/api${path}`;
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || `HTTP ${resp.status}`);
  return data;
}

// --- Connection Status ---

async function updateConnectionStatus() {
  const dot = document.getElementById('status-dot');
  const connected = await sendMessage({ type: 'checkHealth' });
  dot.classList.toggle('online', connected);
  dot.classList.toggle('offline', !connected);
  dot.title = connected ? 'Connected to backend' : 'Backend offline';
}

// --- AI Status ---

async function checkAiStatus() {
  try {
    const settings = await apiCall('/settings');
    aiEnabled = settings.ai_enabled;
    updateModeToggle();
  } catch {
    aiEnabled = false;
    updateModeToggle();
  }
}

function updateModeToggle() {
  const toggle = document.getElementById('mode-toggle');
  toggle.style.display = aiEnabled ? 'flex' : 'none';

  // Generate mode requires AI
  if (!aiEnabled && currentMode === 'generate') {
    switchMode('scan');
  }
}

// --- Voice Profiles ---

async function loadVoiceProfiles() {
  const select = document.getElementById('profile-select');
  try {
    const profiles = await apiCall('/voice-profiles');
    select.innerHTML = '<option value="">None (baseline only)</option>';
    profiles.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      if (p.is_active) opt.selected = true;
      select.appendChild(opt);
    });
  } catch {
    select.innerHTML = '<option value="">Failed to load profiles</option>';
  }
}

// --- Mode Switching ---

function bindEvents() {
  document.getElementById('mode-scan').addEventListener('click', () => switchMode('scan'));
  document.getElementById('mode-generate').addEventListener('click', () => switchMode('generate'));
  document.getElementById('analyze-btn').addEventListener('click', handleAnalyze);
  document.getElementById('generate-btn').addEventListener('click', handleGenerate);
  document.getElementById('rewrite-btn').addEventListener('click', handleRewrite);
  document.getElementById('report-btn').addEventListener('click', handleViewReport);
  document.getElementById('scan-page-btn').addEventListener('click', handleScanPage);
}

function switchMode(mode) {
  currentMode = mode;

  // Update toggle buttons
  document.getElementById('mode-scan').classList.toggle('mode-active', mode === 'scan');
  document.getElementById('mode-generate').classList.toggle('mode-active', mode === 'generate');

  // Update UI visibility
  const scanPageSection = document.getElementById('scan-page-section');
  const analyzeBtn = document.getElementById('analyze-btn');
  const generateBtn = document.getElementById('generate-btn');
  const textInput = document.getElementById('text-input');

  scanPageSection.style.display = mode === 'scan' ? 'block' : 'none';
  analyzeBtn.style.display = mode === 'scan' ? 'block' : 'none';
  generateBtn.style.display = mode === 'generate' ? 'block' : 'none';

  textInput.placeholder = mode === 'scan'
    ? 'Paste text to scan for AI patterns...'
    : 'Write a prompt for the AI to generate content with your voice...';

  // Hide results when switching
  hideResults();
}

function hideResults() {
  document.getElementById('results-section').style.display = 'none';
  document.getElementById('post-actions').style.display = 'none';
  document.getElementById('output-section').style.display = 'none';
}

// --- Analyze ---

async function handleAnalyze() {
  const text = document.getElementById('text-input').value.trim();
  if (!text) return;

  const btn = document.getElementById('analyze-btn');
  btn.disabled = true;
  btn.innerHTML = 'ANALYZING<span class="spinner"></span>';

  try {
    const result = await apiCall('/analyze', {
      method: 'POST',
      body: JSON.stringify({ text, use_ai: aiEnabled })
    });
    lastAnalysis = result;
    lastText = text;
    displayResults(result);
  } catch (err) {
    alert('Analysis failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'ANALYZE';
  }
}

// --- Display Results ---

function displayResults(result) {
  const section = document.getElementById('results-section');
  const postActions = document.getElementById('post-actions');

  // Score value
  const scoreEl = document.getElementById('score-value');
  const score = result.overall_score;
  scoreEl.textContent = score.toFixed(1);
  scoreEl.className = 'score-value ' + getScoreClass(score);

  // Classification badge
  const badge = document.getElementById('classification-badge');
  if (result.classification) {
    const cls = result.classification;
    badge.textContent = cls.label;
    badge.className = 'classification-badge ' + categoryToClass(cls.category);
    badge.title = `${cls.confidence} confidence`;
  } else {
    badge.textContent = '';
    badge.className = 'classification-badge';
  }

  // Score gauge marker
  const marker = document.getElementById('score-marker');
  marker.style.left = Math.min(score, 100) + '%';

  // Pattern count
  const patternEl = document.getElementById('pattern-count');
  const count = (result.detected_patterns || result.patterns || []).length;
  patternEl.textContent = count > 0
    ? `${count} pattern${count !== 1 ? 's' : ''} detected`
    : 'No AI patterns detected';

  section.style.display = 'block';
  postActions.style.display = 'flex';
}

function getScoreClass(score) {
  if (score <= 15) return 'clean';
  if (score <= 35) return 'ghost-touched';
  return 'ghost-written';
}

function categoryToClass(category) {
  if (!category) return '';
  return category.replace(/_/g, '-');
}

// --- Generate ---

async function handleGenerate() {
  const prompt = document.getElementById('text-input').value.trim();
  if (!prompt) return;

  const profileId = document.getElementById('profile-select').value;
  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.innerHTML = 'GENERATING<span class="spinner"></span>';

  try {
    const body = {
      text: prompt,
      use_ai: true,
      comment: 'GENERATE: Create original content based on the prompt above.'
    };
    if (profileId) body.voice_profile_id = parseInt(profileId);

    const result = await apiCall('/rewrite', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    const generated = result.rewritten_text || result.text || '';
    if (!generated) throw new Error('No content generated');

    // Show generated text in output
    document.getElementById('text-output').value = generated;
    document.getElementById('output-section').style.display = 'block';

    // Switch to scan mode and auto-analyze the generated text
    document.getElementById('text-input').value = generated;
    switchMode('scan');
    await handleAnalyze();
  } catch (err) {
    alert('Generation failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'GENERATE';
  }
}

// --- Rewrite ---

async function handleRewrite() {
  const text = document.getElementById('text-input').value.trim();
  if (!text) return;

  const profileId = document.getElementById('profile-select').value;
  const btn = document.getElementById('rewrite-btn');
  btn.disabled = true;
  btn.innerHTML = 'REWRITING<span class="spinner"></span>';

  try {
    const body = {
      text,
      use_ai: true,
      comment: 'Rewrite this text to sound more human while preserving meaning.'
    };
    if (profileId) body.voice_profile_id = parseInt(profileId);

    const result = await apiCall('/rewrite', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    const rewritten = result.rewritten_text || result.text || '';
    if (!rewritten) throw new Error('No rewritten text returned');

    // Show rewritten text in output
    document.getElementById('text-output').value = rewritten;
    document.getElementById('output-section').style.display = 'block';

    // Auto-analyze the rewritten text
    document.getElementById('text-input').value = rewritten;
    await handleAnalyze();
  } catch (err) {
    alert('Rewrite failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'REWRITE';
  }
}

// --- Placeholder handlers (implemented in later tasks) ---

async function handleViewReport() {
  // Task 8 — needs backend analysis-history endpoint
  alert('View Full Report will be available after backend setup.');
}

async function handleScanPage() {
  // Task 9 — content script injection
  alert('Scan This Page will be available soon.');
}
