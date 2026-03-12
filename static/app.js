/* ═══════════════════════════════════════════════════════════
   ResumeRank — App Logic with Auth, Tutorial & Dark Mode
   ═══════════════════════════════════════════════════════════ */

let currentUser = null;
let selectedFiles = [];
let currentJobId = null;
let pollingInterval = null;
let currentResults = null;

// ── Interactive Spotlight Tour ─────────────────────────────
const TOUR_STEPS = [
    {
        target: '#jd-input',
        title: 'Paste Your Job Description',
        desc: 'Start here — paste the full job description. The AI uses this to understand exactly what skills, experience, and qualifications matter most.',
        position: 'bottom',
    },
    {
        target: '#dropzone',
        title: 'Upload Resumes',
        desc: 'Drag & drop resume files (PDF, DOCX, TXT) or a ZIP archive with up to 200 resumes. They\'ll be parsed automatically.',
        position: 'bottom',
    },
    {
        target: '#analyze-btn',
        title: 'Run the Analysis',
        desc: 'Once both fields are filled, click here. The AI runs a 3-stage pipeline: parsing → embedding similarity → Claude deep evaluation.',
        position: 'top',
    },
    {
        target: '#theme-toggle',
        title: 'Dark Mode',
        desc: 'Prefer dark mode? Toggle it here. Your preference is saved to your account automatically.',
        position: 'bottom-left',
    },
    {
        target: '#user-avatar',
        title: 'Your Account',
        desc: 'Click your avatar to change your API key, replay this tutorial, or sign out. You\'re all set — let\'s rank some resumes! 🚀',
        position: 'bottom-left',
    },
];

let tourStep = 0;
let tourActive = false;
let tourElements = {}; // { backdrop, spotlight, tooltip }

function showTutorial() {
    tourStep = 0;
    tourActive = true;
    createTourElements();
    renderTourStep();
}

function createTourElements() {
    // Clean up any previous tour elements
    destroyTour();

    const root = document.getElementById('tour-root');

    // Backdrop
    const backdrop = document.createElement('div');
    backdrop.className = 'tour-backdrop';
    backdrop.id = 'tour-backdrop';
    root.appendChild(backdrop);

    // Spotlight
    const spotlight = document.createElement('div');
    spotlight.className = 'tour-spotlight';
    spotlight.id = 'tour-spotlight';
    root.appendChild(spotlight);

    // Tooltip
    const tooltip = document.createElement('div');
    tooltip.className = 'tour-tooltip';
    tooltip.id = 'tour-tooltip';
    root.appendChild(tooltip);

    tourElements = { backdrop, spotlight, tooltip };

    // Block clicks on backdrop
    backdrop.addEventListener('click', (e) => e.stopPropagation());
}

function renderTourStep() {
    if (!tourActive || tourStep >= TOUR_STEPS.length) {
        endTour();
        return;
    }

    const step = TOUR_STEPS[tourStep];
    const targetEl = document.querySelector(step.target);
    if (!targetEl) { tourStep++; renderTourStep(); return; }

    // Scroll target into view
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // Wait for scroll to finish before positioning
    setTimeout(() => {
        positionSpotlight(targetEl);
        positionTooltip(targetEl, step);
    }, 400);
}

function positionSpotlight(el) {
    const rect = el.getBoundingClientRect();
    const pad = 8;
    const { spotlight } = tourElements;
    spotlight.style.top = (rect.top - pad) + 'px';
    spotlight.style.left = (rect.left - pad) + 'px';
    spotlight.style.width = (rect.width + pad * 2) + 'px';
    spotlight.style.height = (rect.height + pad * 2) + 'px';
}

function positionTooltip(el, step) {
    const rect = el.getBoundingClientRect();
    const { tooltip } = tourElements;
    const totalSteps = TOUR_STEPS.length;

    // Build tooltip content
    tooltip.innerHTML = `
        <p class="tour-tooltip-step">Step ${tourStep + 1} of ${totalSteps}</p>
        <h3 class="tour-tooltip-title">${step.title}</h3>
        <p class="tour-tooltip-desc">${step.desc}</p>
        <div class="tour-tooltip-footer">
            <div class="tour-dots">
                ${TOUR_STEPS.map((_, i) => `<div class="tour-dot ${i === tourStep ? 'active' : ''}"></div>`).join('')}
            </div>
            <div style="display:flex;gap:8px;">
                <button class="tour-btn tour-btn-skip" id="tour-skip">Skip</button>
                <button class="tour-btn tour-btn-next" id="tour-next">${tourStep === totalSteps - 1 ? "Let's Go!" : 'Next'}</button>
            </div>
        </div>
    `;

    // Position the tooltip based on step.position
    const gap = 16;
    tooltip.style.removeProperty('top');
    tooltip.style.removeProperty('bottom');
    tooltip.style.removeProperty('left');
    tooltip.style.removeProperty('right');

    switch (step.position) {
        case 'bottom':
            tooltip.style.top = (rect.bottom + gap) + 'px';
            tooltip.style.left = Math.max(16, rect.left + rect.width / 2 - 170) + 'px';
            break;
        case 'top':
            tooltip.style.top = (rect.top - gap - tooltip.offsetHeight - 20) + 'px';
            tooltip.style.left = Math.max(16, rect.left + rect.width / 2 - 170) + 'px';
            break;
        case 'bottom-left':
            tooltip.style.top = (rect.bottom + gap) + 'px';
            tooltip.style.right = (window.innerWidth - rect.right) + 'px';
            break;
    }

    // Ensure tooltip stays on screen
    requestAnimationFrame(() => {
        const tRect = tooltip.getBoundingClientRect();
        if (tRect.right > window.innerWidth - 16) {
            tooltip.style.left = 'auto';
            tooltip.style.right = '16px';
        }
        if (tRect.bottom > window.innerHeight - 16) {
            tooltip.style.top = (rect.top - gap - tRect.height) + 'px';
        }
    });

    // Button handlers
    document.getElementById('tour-next').addEventListener('click', () => {
        tourStep++;
        renderTourStep();
    });
    document.getElementById('tour-skip').addEventListener('click', () => {
        endTour();
    });
}

function endTour() {
    tourActive = false;
    destroyTour();
    fetch('/api/tutorial-seen', { method: 'POST' });
    if (currentUser) currentUser.has_seen_tutorial = true;
}

function destroyTour() {
    const root = document.getElementById('tour-root');
    if (root) root.innerHTML = '';
    tourElements = {};
}


// ── Init ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    initTheme();
    initDropzone();
    initButtons();
    initUserMenu();
});


// ── Auth ───────────────────────────────────────────────────
async function checkAuth() {
    try {
        const res = await fetch('/auth/me');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }
        currentUser = await res.json();

        // Set user info in header
        const avatar = document.getElementById('user-avatar');
        const name = document.getElementById('user-name');
        const email = document.getElementById('user-email');

        if (currentUser.picture) avatar.src = currentUser.picture;
        else avatar.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="20" fill="%236366f1"/><text x="20" y="26" text-anchor="middle" fill="white" font-size="18">' + (currentUser.name?.[0] || '?') + '</text></svg>';
        name.textContent = currentUser.name || 'User';
        email.textContent = currentUser.email;

        // Apply saved theme
        if (currentUser.theme) {
            document.documentElement.setAttribute('data-theme', currentUser.theme);
            document.getElementById('theme-toggle').textContent = currentUser.theme === 'dark' ? '☀️' : '🌙';
        }

        // Show API key modal if no key set
        if (!currentUser.has_api_key) {
            showApiKeyModal();
        } else if (!currentUser.has_seen_tutorial) {
            showTutorial();
        }
    } catch (e) {
        window.location.href = '/login';
    }
}


// ── Theme ──────────────────────────────────────────────────
function initTheme() {
    const toggle = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
        toggle.textContent = saved === 'dark' ? '☀️' : '🌙';
    }

    toggle.addEventListener('click', async () => {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        toggle.textContent = next === 'dark' ? '☀️' : '🌙';
        localStorage.setItem('theme', next);
        try {
            await fetch('/api/theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: next }),
            });
        } catch (e) { /* ignore */ }
    });
}


// ── User Menu ──────────────────────────────────────────────
function initUserMenu() {
    const avatar = document.getElementById('user-avatar');
    const dropdown = document.getElementById('user-dropdown');

    avatar.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('open');
    });

    document.addEventListener('click', () => dropdown.classList.remove('open'));

    document.getElementById('logout-btn').addEventListener('click', () => {
        window.location.href = '/auth/logout';
    });

    document.getElementById('change-key-btn').addEventListener('click', () => {
        dropdown.classList.remove('open');
        showApiKeyModal();
    });

    document.getElementById('show-tutorial-btn').addEventListener('click', () => {
        dropdown.classList.remove('open');
        showTutorial();
    });
}


// ── API Key Modal ──────────────────────────────────────────
function showApiKeyModal() {
    const overlay = document.getElementById('apikey-overlay');
    overlay.classList.remove('hidden');

    const saveBtn = document.getElementById('apikey-save');
    const input = document.getElementById('apikey-input');
    const error = document.getElementById('apikey-error');
    input.value = '';
    error.textContent = '';

    const newSaveBtn = saveBtn.cloneNode(true);
    saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);

    newSaveBtn.addEventListener('click', async () => {
        const key = input.value.trim();
        if (!key) { error.textContent = 'Please enter your API key.'; return; }
        if (!key.startsWith('sk-ant-')) { error.textContent = 'Key should start with sk-ant-'; return; }

        newSaveBtn.disabled = true;
        newSaveBtn.querySelector('.btn-text').textContent = 'Validating...';
        error.textContent = '';

        try {
            const res = await fetch('/api/save-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key }),
            });
            if (!res.ok) {
                const data = await res.json();
                error.textContent = data.detail || 'Failed to save key.';
                newSaveBtn.disabled = false;
                newSaveBtn.querySelector('.btn-text').textContent = 'Save & Continue';
                return;
            }
            overlay.classList.add('hidden');
            currentUser.has_api_key = true;
            if (!currentUser.has_seen_tutorial) {
                showTutorial();
            }
        } catch (e) {
            error.textContent = 'Network error. Please try again.';
            newSaveBtn.disabled = false;
            newSaveBtn.querySelector('.btn-text').textContent = 'Save & Continue';
        }
    });
}


function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        addFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => addFiles(e.target.files));
}

function addFiles(fileList) {
    for (const f of fileList) {
        if (!selectedFiles.some(s => s.name === f.name)) {
            selectedFiles.push(f);
        }
    }
    renderFileList();
    updateAnalyzeButton();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
    updateAnalyzeButton();
}

function renderFileList() {
    const container = document.getElementById('file-list');
    container.innerHTML = selectedFiles.map((f, i) => `
        <div class="file-chip">
            <span>${f.name}</span>
            <button class="file-chip-remove" onclick="removeFile(${i})">×</button>
        </div>
    `).join('');
}

function updateAnalyzeButton() {
    const jd = document.getElementById('jd-input').value.trim();
    document.getElementById('analyze-btn').disabled = !(jd && selectedFiles.length > 0);
}


// ── Buttons ────────────────────────────────────────────────
function initButtons() {
    document.getElementById('jd-input').addEventListener('input', updateAnalyzeButton);
    document.getElementById('analyze-btn').addEventListener('click', startAnalysis);
    document.getElementById('export-btn')?.addEventListener('click', exportCSV);
    document.getElementById('new-search-btn')?.addEventListener('click', resetUI);
    document.getElementById('modal-close')?.addEventListener('click', () => {
        document.getElementById('modal-overlay').classList.add('hidden');
    });
    document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) e.currentTarget.classList.add('hidden');
    });
}


// ── Analysis ───────────────────────────────────────────────
async function startAnalysis() {
    const jd = document.getElementById('jd-input').value.trim();
    if (!jd || selectedFiles.length === 0) return;

    // Check API key first
    if (!currentUser.has_api_key) {
        showApiKeyModal();
        return;
    }

    // Build form data
    const formData = new FormData();
    formData.append('job_description', jd);
    selectedFiles.forEach(f => formData.append('files', f));

    // Show progress
    showSection('progress');
    updateProgress('parsing', 'Parsing resumes...', 'Extracting text from uploaded files', 0);

    try {
        const res = await fetch('/api/analyze', { method: 'POST', body: formData });
        if (!res.ok) {
            const data = await res.json();
            alert(data.detail || 'Analysis failed');
            showSection('upload');
            return;
        }
        const { job_id } = await res.json();
        currentJobId = job_id;
        startPolling();
    } catch (e) {
        alert('Network error: ' + e.message);
        showSection('upload');
    }
}

function startPolling() {
    pollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${currentJobId}`);
            const status = await res.json();

            switch (status.status) {
                case 'parsing':
                    updateProgress('parsing', 'Parsing resumes...', 'Extracting text from uploaded files', 10);
                    break;
                case 'embedding':
                    updateProgress('embedding', 'Analyzing similarity...', 'Computing semantic embeddings', 30);
                    break;
                case 'evaluating':
                    const pct = status.total_eval ? Math.round((status.progress / status.total_eval) * 60) + 30 : 50;
                    updateProgress('evaluating', 'Deep evaluation...', `Claude is evaluating ${status.progress || 0} of ${status.total_eval || '?'} candidates`, pct);
                    break;
                case 'complete':
                    clearInterval(pollingInterval);
                    updateProgress('complete', 'Complete!', 'Loading results...', 100);
                    setTimeout(fetchResults, 500);
                    break;
                case 'error':
                    clearInterval(pollingInterval);
                    alert('Error: ' + (status.error || 'Unknown error'));
                    showSection('upload');
                    break;
            }
        } catch (e) { /* retry */ }
    }, 2000);
}

async function fetchResults() {
    try {
        const res = await fetch(`/api/results/${currentJobId}`);
        const data = await res.json();
        currentResults = data;
        renderResults(data);
        showSection('results');
    } catch (e) {
        alert('Failed to load results');
        showSection('upload');
    }
}


// ── Progress UI ────────────────────────────────────────────
function updateProgress(stage, title, detail, pct) {
    document.getElementById('progress-title').textContent = title;
    document.getElementById('progress-detail').textContent = detail;
    document.getElementById('progress-bar').style.width = pct + '%';
    document.getElementById('progress-count').textContent = pct > 0 ? `${pct}%` : '';
}


// ── Results Rendering ──────────────────────────────────────
function renderResults(data) {
    const grid = document.getElementById('results-grid');
    const subtitle = document.getElementById('results-subtitle');
    const results = data.results;

    subtitle.textContent = `${results.length} candidates evaluated · Top ${results.length} from ${data.all_resumes?.length || '?'} resumes`;

    grid.innerHTML = results.map((r, i) => {
        const scoreClass = r.composite_score >= 70 ? 'score-high' : r.composite_score >= 40 ? 'score-mid' : 'score-low';
        const rankClass = r.rank <= 3 ? `rank-${r.rank}` : 'rank-default';
        return `
            <div class="result-card" onclick="showDetail(${i})" style="animation-delay: ${i * 0.05}s">
                <div class="result-rank ${rankClass}">${r.rank}</div>
                <div class="result-info">
                    <div class="result-name">${r.filename}</div>
                    <div class="result-summary">${r.summary || ''}</div>
                </div>
                <div class="result-score">
                    <div class="score-value ${scoreClass}">${r.composite_score}</div>
                    <div class="score-label">Score</div>
                </div>
            </div>
        `;
    }).join('');

    // Render all resumes table
    const tbody = document.getElementById('all-resumes-tbody');
    if (data.all_resumes) {
        const evaluated = new Set(results.map(r => r.filename));
        tbody.innerHTML = data.all_resumes.map((r, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${r.filename}</td>
                <td>${(r.embedding_score * 100).toFixed(1)}%</td>
                <td><span class="status-badge ${evaluated.has(r.filename) ? 'status-evaluated' : 'status-screened'}">${evaluated.has(r.filename) ? 'Evaluated' : 'Screened'}</span></td>
            </tr>
        `).join('');
    }
}


// ── Detail Modal ───────────────────────────────────────────
function showDetail(index) {
    const r = currentResults.results[index];
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');
    const scoreClass = r.composite_score >= 70 ? 'score-high' : r.composite_score >= 40 ? 'score-mid' : 'score-low';

    const dimensions = [
        { label: 'Skills Match', key: 'skills_match' },
        { label: 'Experience Relevance', key: 'experience_relevance' },
        { label: 'Education Fit', key: 'education_fit' },
        { label: 'Achievements', key: 'achievements' },
        { label: 'Communication', key: 'communication_quality' },
    ];

    body.innerHTML = `
        <p class="modal-rank">Rank #${r.rank}</p>
        <h2 class="modal-name">${r.filename}</h2>
        <div class="modal-score-row">
            <span class="modal-score-big ${scoreClass}">${r.composite_score}</span>
            <span class="modal-score-label">/ 100 composite score</span>
        </div>
        <div class="dimension-list">
            ${dimensions.map(d => {
        const val = r[d.key] || 0;
        const color = val >= 70 ? 'var(--green)' : val >= 40 ? 'var(--orange)' : 'var(--red)';
        return `
                    <div class="dimension">
                        <span class="dimension-label">${d.label}</span>
                        <div class="dimension-bar-wrap">
                            <div class="dimension-bar"><div class="dimension-bar-fill" style="width:${val}%;background:${color}"></div></div>
                            <span class="dimension-value">${val}</span>
                        </div>
                    </div>
                `;
    }).join('')}
        </div>
        <p class="modal-section-title">Summary</p>
        <p class="modal-summary">${r.summary || 'No summary available.'}</p>
        ${r.key_strengths?.length ? `
            <p class="modal-section-title">Strengths</p>
            <div class="tag-list">${r.key_strengths.map(s => `<span class="tag-green">${s}</span>`).join('')}</div>
        ` : ''}
        ${r.gaps?.length ? `
            <p class="modal-section-title">Gaps</p>
            <div class="tag-list">${r.gaps.map(g => `<span class="tag-red">${g}</span>`).join('')}</div>
        ` : ''}
    `;

    overlay.classList.remove('hidden');
}


// ── Section Switching ──────────────────────────────────────
function showSection(section) {
    ['upload-section', 'progress-section', 'results-section', 'hero-section'].forEach(id => {
        document.getElementById(id)?.classList.add('hidden');
    });
    switch (section) {
        case 'upload':
            document.getElementById('hero-section').classList.remove('hidden');
            document.getElementById('upload-section').classList.remove('hidden');
            break;
        case 'progress':
            document.getElementById('progress-section').classList.remove('hidden');
            break;
        case 'results':
            document.getElementById('results-section').classList.remove('hidden');
            break;
    }
}


// ── Reset UI ───────────────────────────────────────────────
function resetUI() {
    selectedFiles = [];
    currentJobId = null;
    currentResults = null;
    if (pollingInterval) clearInterval(pollingInterval);
    document.getElementById('jd-input').value = '';
    renderFileList();
    updateAnalyzeButton();
    showSection('upload');
}


// ── CSV Export ──────────────────────────────────────────────
function exportCSV() {
    if (!currentResults) return;
    const headers = ['Rank', 'Filename', 'Composite Score', 'Skills Match', 'Experience', 'Education', 'Achievements', 'Communication', 'Summary'];
    const rows = currentResults.results.map(r => [
        r.rank, r.filename, r.composite_score,
        r.skills_match || 0, r.experience_relevance || 0, r.education_fit || 0,
        r.achievements || 0, r.communication_quality || 0,
        `"${(r.summary || '').replace(/"/g, '""')}"`,
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'resume_rankings.csv';
    a.click();
}
