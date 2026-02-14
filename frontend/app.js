const state = {
  documentId: null,
  pageCount: 0,
  currentPage: 1,
  lastResult: null,
};

const el = {
  fileInput: document.getElementById('fileInput'),
  documentSelect: document.getElementById('documentSelect'),
  status: document.getElementById('status'),
  queryInput: document.getElementById('queryInput'),
  voiceBtn: document.getElementById('voiceBtn'),
  searchBtn: document.getElementById('searchBtn'),
  timeline: document.getElementById('timeline'),
  pdfFrame: document.getElementById('pdfFrame'),
  results: document.getElementById('results'),
  history: document.getElementById('history'),
  smoothing: document.getElementById('smoothing'),
  threshold: document.getElementById('threshold'),
  topK: document.getElementById('topK'),
  exportBtn: document.getElementById('exportBtn'),
};

async function api(path, options = {}) {
  const resp = await fetch(path, options);
  if (!resp.ok) throw new Error(await resp.text());
  return resp.json();
}

function setStatus(msg) {
  el.status.textContent = msg;
}

async function loadDocuments() {
  const docs = await api('/api/documents');
  el.documentSelect.innerHTML = '';
  docs.forEach((d) => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.filename} (${d.page_count}p)`;
    el.documentSelect.appendChild(opt);
  });
  if (docs.length) {
    state.documentId = docs[0].id;
    state.pageCount = docs[0].page_count;
    el.documentSelect.value = state.documentId;
    showPdf();
    drawTimeline(new Array(state.pageCount).fill(0));
    loadHistory();
  }
}

async function uploadFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  setStatus('Ingesting PDF...');
  const data = await api('/api/upload', { method: 'POST', body: fd });
  state.documentId = data.document_id;
  state.pageCount = data.page_count;
  await loadDocuments();
  setStatus(`Loaded ${data.filename}`);
}

function showPdf(page = 1) {
  state.currentPage = page;
  el.pdfFrame.src = `/api/document/${state.documentId}/file#page=${page}`;
}

async function runSearch() {
  const query = el.queryInput.value.trim();
  if (!query || !state.documentId) return;
  setStatus('Searching...');
  const result = await api('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      document_id: Number(state.documentId),
      query,
      smoothing: Number(el.smoothing.value),
      threshold: Number(el.threshold.value),
      top_k: Number(el.topK.value),
    }),
  });
  state.lastResult = result;
  renderResults(result.passages);
  drawTimeline(result.smoothed_scores, result.raw_scores);
  loadHistory();
  setStatus(`Done (${result.backend})`);
}

function renderResults(passages) {
  el.results.innerHTML = '';
  passages.forEach((p) => {
    const li = document.createElement('li');

    const heading = document.createElement('b');
    heading.textContent = `p.${p.page}`;
    li.appendChild(heading);
    li.appendChild(document.createTextNode(` score=${p.score.toFixed(3)}`));

    const snippet = document.createElement('div');
    snippet.className = 'small';
    snippet.textContent = p.snippet;
    li.appendChild(snippet);

    li.onclick = () => showPdf(p.page);
    el.results.appendChild(li);
  });
}

async function loadHistory() {
  if (!state.documentId) return;
  const rows = await api(`/api/document/${state.documentId}/history`);
  el.history.innerHTML = '';
  rows.forEach((r) => {
    const li = document.createElement('li');
    li.textContent = `${r.query} (s=${r.smoothing}, t=${r.threshold}, k=${r.top_k})`;
    li.onclick = () => {
      el.queryInput.value = r.query;
      el.smoothing.value = r.smoothing;
      el.threshold.value = r.threshold;
      el.topK.value = r.top_k;
      runSearch();
    };
    el.history.appendChild(li);
  });
}

function drawTimeline(scores, rawScores = null) {
  const canvas = el.timeline;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const n = scores.length || state.pageCount;
  if (!n) return;

  ctx.fillStyle = '#0f1521';
  ctx.fillRect(0, 0, w, h);

  for (let i = 0; i < n; i++) {
    const v = scores[i] || 0;
    const x = (i / Math.max(1, n - 1)) * w;
    const barW = w / n + 1;
    const alpha = 0.12 + v * 0.88;
    ctx.fillStyle = `rgba(255,70,70,${alpha})`;
    ctx.fillRect(x, 0, barW, h);
  }

  ctx.beginPath();
  ctx.strokeStyle = '#7ec8ff';
  ctx.lineWidth = 3;
  for (let i = 0; i < n; i++) {
    const x = (i / Math.max(1, n - 1)) * w;
    const y = h - (scores[i] || 0) * (h - 20) - 10;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  const cx = ((state.currentPage - 1) / Math.max(1, n - 1)) * w;
  ctx.beginPath();
  ctx.strokeStyle = '#ffffff';
  ctx.setLineDash([4, 4]);
  ctx.moveTo(cx, 0);
  ctx.lineTo(cx, h);
  ctx.stroke();
  ctx.setLineDash([]);

  canvas.onclick = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const idx = Math.round((x / rect.width) * (n - 1));
    showPdf(idx + 1);
    drawTimeline(scores, rawScores);
  };

  canvas.onmousemove = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const idx = Math.round((x / rect.width) * (n - 1));
    const score = scores[idx] || 0;
    canvas.title = `Page ${idx + 1} • score ${score.toFixed(3)}${rawScores ? ` • raw ${(rawScores[idx] || 0).toFixed(3)}` : ''}`;
  };
}

function setupVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    el.voiceBtn.disabled = true;
    el.voiceBtn.title = 'Speech API unavailable in this browser';
    return;
  }
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.continuous = false;
  recognition.interimResults = false;

  el.voiceBtn.onclick = () => recognition.start();
  recognition.onresult = (event) => {
    const text = event.results[0][0].transcript;
    el.queryInput.value = text;
  };
}

el.fileInput.onchange = (e) => uploadFile(e.target.files[0]);
el.documentSelect.onchange = () => {
  state.documentId = Number(el.documentSelect.value);
  const label = el.documentSelect.options[el.documentSelect.selectedIndex].text;
  const match = label.match(/\((\d+)p\)/);
  state.pageCount = match ? Number(match[1]) : 0;
  showPdf(1);
  drawTimeline(new Array(state.pageCount).fill(0));
  loadHistory();
};
el.searchBtn.onclick = runSearch;
el.exportBtn.onclick = async () => {
  if (!state.lastResult) return;
  const data = await api(`/api/export/${state.documentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state.lastResult),
  });
  setStatus(`Exported ${data.json} and ${data.csv}`);
};

setupVoice();
loadDocuments();
