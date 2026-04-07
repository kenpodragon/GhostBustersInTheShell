// GBIS Chrome Extension — Popup Logic

let config = null;
let aiEnabled = false;
let currentMode = 'scan';
let lastAnalysis = null;
let lastText = null;

// --- State Persistence ---

async function saveState() {
  await chrome.storage.local.set({
    popupState: {
      text: document.getElementById('text-input').value,
      mode: currentMode,
      lastAnalysis,
      lastText,
      outputText: document.getElementById('text-output').value,
      hasResults: document.getElementById('results-section').style.display !== 'none',
      hasOutput: document.getElementById('output-section').style.display !== 'none',
    }
  });
}

async function restoreState() {
  const { popupState } = await chrome.storage.local.get('popupState');
  if (!popupState) return;

  if (popupState.mode && popupState.mode !== currentMode) {
    switchMode(popupState.mode);
  }
  if (popupState.text) {
    document.getElementById('text-input').value = popupState.text;
  }
  if (popupState.lastAnalysis) {
    lastAnalysis = popupState.lastAnalysis;
    lastText = popupState.lastText;
    displayResults(lastAnalysis);
  }
  if (popupState.outputText) {
    document.getElementById('text-output').value = popupState.outputText;
    if (popupState.hasOutput) {
      document.getElementById('output-section').style.display = 'block';
    }
  }
}

// --- Init ---

document.addEventListener('DOMContentLoaded', async () => {
  await init();
  bindEvents();
  await restoreState();
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

  // Close button — clears saved state and closes
  document.getElementById('close-btn').addEventListener('click', async () => {
    await chrome.storage.local.remove('popupState');
    window.close();
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

  // Update AI toggle button
  const aiBtn = document.getElementById('ai-toggle-btn');
  aiBtn.classList.toggle('on', aiEnabled);
  aiBtn.classList.toggle('off', !aiEnabled);
  aiBtn.title = aiEnabled ? 'AI is on — click to disable' : 'AI is off — click to enable';

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
  document.getElementById('ai-toggle-btn').addEventListener('click', handleAiToggle);
  document.getElementById('analyze-btn').addEventListener('click', handleAnalyze);
  document.getElementById('generate-btn').addEventListener('click', handleGenerate);
  document.getElementById('rewrite-btn').addEventListener('click', handleRewrite);
  document.getElementById('report-btn').addEventListener('click', handleViewReport);
  document.getElementById('scan-page-btn').addEventListener('click', handleScanPage);
}

async function handleAiToggle() {
  try {
    const newState = !aiEnabled;
    await apiCall('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ ai_enabled: newState })
    });
    aiEnabled = newState;
    updateModeToggle();
  } catch (err) {
    alert('Failed to toggle AI: ' + err.message);
  }
}

function switchMode(mode) {
  currentMode = mode;

  // Update toggle buttons
  document.getElementById('mode-scan').classList.toggle('mode-active', mode === 'scan');
  document.getElementById('mode-generate').classList.toggle('mode-active', mode === 'generate');

  // Update UI visibility
  const scanPageSection = document.getElementById('scan-page-section');
  const profileSection = document.getElementById('profile-section');
  const analyzeBtn = document.getElementById('analyze-btn');
  const generateBtn = document.getElementById('generate-btn');
  const textInput = document.getElementById('text-input');

  scanPageSection.style.display = mode === 'scan' ? 'block' : 'none';
  profileSection.style.display = mode === 'generate' ? 'block' : 'none';
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
    await saveState();
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
    await saveState();
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
    await saveState();
  } catch (err) {
    alert('Rewrite failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'REWRITE';
  }
}

// --- View Report ---

async function handleViewReport() {
  if (!lastAnalysis || !lastText) {
    alert('No analysis to view. Run an analysis first.');
    return;
  }

  const btn = document.getElementById('report-btn');
  btn.disabled = true;
  btn.innerHTML = 'SAVING<span class="spinner"></span>';

  try {
    const body = {
      text: lastText,
      result: lastAnalysis,
      source: window._lastPageUrl ? 'page_scan' : (currentMode === 'generate' ? 'generate' : 'manual'),
      page_url: window._lastPageUrl || null
    };

    const data = await apiCall('/analysis-history', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    chrome.tabs.create({ url: `${config.frontendUrl}/report/${data.id}` });
  } catch (err) {
    alert('Failed to save report: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'VIEW FULL REPORT';
  }
}

// --- Scan Page ---

async function handleScanPage() {
  const btn = document.getElementById('scan-page-btn');
  btn.disabled = true;
  btn.innerHTML = 'SCANNING<span class="spinner"></span>';

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) throw new Error('No active tab');

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractPageContent
    });

    const result = results[0]?.result;
    if (!result || !result.text) {
      alert('Could not extract text from this page.');
      return;
    }

    // Populate textarea with extracted text
    document.getElementById('text-input').value = result.text;

    // Store page URL for later (report handoff)
    window._lastPageUrl = tab.url;

    // Auto-switch to scan mode if in generate
    if (currentMode !== 'scan') {
      switchMode('scan');
    }
    await saveState();
  } catch (err) {
    alert('Scan failed: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Scan This Page';
  }
}

// This function is injected into the page — must be self-contained
function extractPageContent() {
  // Priority 1: User has text selected
  const selection = window.getSelection().toString().trim();
  if (selection.length > 0) {
    return { text: selection, source: 'selection' };
  }

  // Priority 2: Smart extraction
  const STRIP_SELECTORS = [
    'nav', 'header', 'footer', 'aside',
    '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
    'script', 'style', 'noscript', 'iframe',
    '.ad', '.ads', '.advertisement', '.sidebar',
    '[class*="cookie"]', '[class*="popup"]', '[class*="modal"]'
  ];

  // Try semantic elements
  const semantic = document.querySelector('article') ||
                   document.querySelector('main') ||
                   document.querySelector('[role="main"]');

  if (semantic) {
    const clone = semantic.cloneNode(true);
    clone.querySelectorAll('script, style, nav, aside, [role="navigation"]').forEach(e => e.remove());
    return { text: clone.innerText.trim(), source: 'semantic' };
  }

  // Fallback: largest text-dense block
  const bodyClone = document.body.cloneNode(true);
  STRIP_SELECTORS.forEach(sel => {
    bodyClone.querySelectorAll(sel).forEach(el => el.remove());
  });

  const blocks = bodyClone.querySelectorAll('div, section, article, main');
  let best = null;
  let bestScore = 0;

  blocks.forEach(block => {
    const text = block.innerText.trim();
    const ratio = text.length / (block.innerHTML.length || 1);
    const score = text.length * ratio;
    if (score > bestScore && text.length > 200) {
      bestScore = score;
      best = block;
    }
  });

  if (best) {
    return { text: best.innerText.trim(), source: 'largest_block' };
  }

  return { text: bodyClone.innerText.trim(), source: 'body' };
}
