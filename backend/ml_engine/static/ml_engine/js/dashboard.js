// Full NEA 16-major name table (class index 0..N-1 → display name via enabled_majors order)
const ALL_MAJOR_NAMES = {
    0: "Agriculture",     1: "Architecture",    2: "Arts",          3: "Business",
    4: "Education",       5: "Finance",         6: "Government",    7: "Health",
    8: "Hospitality",     9: "Human Services",  10: "IT",           11: "Law",
    12: "Manufacturing",  13: "Sales",          14: "Science",      15: "Transport"
};

let clearedLogCount = 0;
let enabledMajorIds = []; // Filled from /api/ml/major-config/

// ─── Major Config ────────────────────────────────────────────────────────────
async function loadMajorConfig() {
    try {
        const res = await fetch('/api/ml/major-config/');
        if (!res.ok) return;
        const data = await res.json();
        enabledMajorIds = data.majors.filter(m => m.enabled).map(m => m.id);
        renderMajorCheckboxes(data.majors);
    } catch (e) {
        console.warn('Could not load major config', e);
    }
}

function renderMajorCheckboxes(majors) {
    const container = document.getElementById('majorCheckboxes');
    if (!container) return;
    container.innerHTML = '';
    majors.forEach(m => {
        const label = document.createElement('label');
        label.className = 'major-chip' + (m.enabled ? ' enabled' : '');
        label.title = `ID: ${m.id}`;
        label.innerHTML = `
            <input type="checkbox" value="${m.id}" ${m.enabled ? 'checked' : ''}>
            <span>${m.name}</span>
        `;
        label.querySelector('input').addEventListener('change', function() {
            label.classList.toggle('enabled', this.checked);
            syncEnabledMajors();
        });
        container.appendChild(label);
    });
    syncEnabledMajors();
}

function syncEnabledMajors() {
    const checkboxes = document.querySelectorAll('#majorCheckboxes input[type=checkbox]');
    enabledMajorIds = Array.from(checkboxes).filter(c => c.checked).map(c => parseInt(c.value));
    const countEl = document.getElementById('majorSelectionCount');
    if (countEl) countEl.textContent = `${enabledMajorIds.length} / 16 selected`;
    const trainBtn = document.getElementById('trainBtn');
    if (trainBtn) trainBtn.disabled = enabledMajorIds.length < 2;
}

async function selectAllMajors() {
    document.querySelectorAll('#majorCheckboxes input[type=checkbox]').forEach(c => {
        c.checked = true;
        c.closest('label').classList.add('enabled');
    });
    syncEnabledMajors();
}

async function clearAllMajors() {
    document.querySelectorAll('#majorCheckboxes input[type=checkbox]').forEach(c => {
        c.checked = false;
        c.closest('label').classList.remove('enabled');
    });
    syncEnabledMajors();
}

// ─── File / UI helpers ────────────────────────────────────────────────────────
function updateFileName(input) {
    const label = document.getElementById('fileNameLabel');
    if (input.files && input.files.length > 0) {
        label.textContent = input.files[0].name;
        label.style.color = '#1f1f1f';
    } else {
        label.textContent = 'Select CSV dataset (optional)';
        label.style.color = '#444746';
    }
}

function clearLogs() {
    const consoleDiv = document.getElementById('consoleOutput');
    consoleDiv.innerHTML = '';
    shouldUpdateClearCount = true;
}

function copyLogs() {
    const consoleDiv = document.getElementById('consoleOutput');
    const text = consoleDiv.innerText;
    navigator.clipboard.writeText(text).then(() => {
        // Brief visual feedback
        const btn = document.querySelector('[onclick="copyLogs()"] .material-icons-outlined');
        if (btn) {
            btn.textContent = 'check';
            setTimeout(() => { btn.textContent = 'content_copy'; }, 1200);
        }
    }).catch(() => {
        // Fallback for older browsers
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    });
}

let shouldUpdateClearCount = false;
let previousStatus = null;

function updateUI(state) {
    if (shouldUpdateClearCount) {
        clearedLogCount = state.logs.length;
        shouldUpdateClearCount = false;
    }

    if (previousStatus === 'TRAINING' && state.status === 'COMPLETED') {
        // Training finished
    }
    previousStatus = state.status;

    if (state.logs.length < clearedLogCount) {
        clearedLogCount = 0;
    }

    // Status Pill
    const pill = document.getElementById('statusPill');
    const icon = pill.querySelector('.material-icons-outlined');
    if (state.status === 'TRAINING') {
        pill.childNodes[2].textContent = ' Training...';
        icon.textContent = 'sync';
        document.getElementById('evalPanel').style.display = 'none';
    } else if (state.status === 'COMPLETED') {
        pill.childNodes[2].textContent = ' Completed';
        icon.textContent = 'check_circle';
    } else if (state.status === 'ERROR') {
        pill.childNodes[2].textContent = ' Error';
        icon.textContent = 'error';
        pill.style.color = 'var(--error-color)';
    } else {
        pill.childNodes[2].textContent = ' Ready';
        icon.textContent = 'check_circle';
        pill.style.color = 'var(--text-primary)';
    }

    // Progress
    if (state.total_epochs > 0) {
        const percent = Math.round((state.current_epoch / state.total_epochs) * 100);
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('epochValue').textContent = `${state.current_epoch} / ${state.total_epochs}`;
    } else {
        document.getElementById('progressBar').style.width = '0%';
        document.getElementById('epochValue').textContent = '--';
    }

    // Metrics
    if (state.metrics) {
        if (state.metrics.loss) {
            document.getElementById('lossValue').textContent = parseFloat(state.metrics.loss).toFixed(4);
        }
        let acc = null;
        if (state.metrics.valid_accuracy) acc = state.metrics.valid_accuracy;
        else if (state.metrics.accuracy) acc = state.metrics.accuracy;
        if (acc !== null) {
            document.getElementById('accuracyValue').textContent = (parseFloat(acc) * 100).toFixed(2) + '%';
        }

        // Evaluation Panel
        if (state.metrics.evaluation) {
            const evalMetrics = state.metrics.evaluation;
            document.getElementById('evalPanel').style.display = 'flex';
            document.getElementById('evalPanel').style.flexDirection = 'column';
            document.getElementById('evalTestAcc').textContent = (evalMetrics.test_accuracy * 100).toFixed(2) + '%';
            document.getElementById('evalTop3').textContent = (evalMetrics.top_k_accuracy * 100).toFixed(2) + '%';

            const tbody = document.querySelector('#classReportTable tbody');
            tbody.innerHTML = '';

            // Build class-index → major-name map from current enabledMajorIds
            const classToName = {};
            enabledMajorIds.forEach((mid, idx) => {
                classToName[idx] = ALL_MAJOR_NAMES[mid] || `Major ${mid}`;
            });

            for (const [key, value] of Object.entries(evalMetrics.classification_report)) {
                if (key === 'accuracy' || key === 'macro avg' || key === 'weighted avg') continue;
                const row = document.createElement('tr');
                row.style.borderBottom = '1px solid #f0f0f0';
                const className = (!isNaN(key) && classToName[parseInt(key)]) ? classToName[parseInt(key)] : key;
                row.innerHTML = `
                    <td style="padding: 8px; font-weight: 500;">${className}</td>
                    <td style="padding: 8px;">${(value['precision'] * 100).toFixed(1)}%</td>
                    <td style="padding: 8px;">${(value['recall'] * 100).toFixed(1)}%</td>
                    <td style="padding: 8px;">${(value['f1-score'] * 100).toFixed(1)}%</td>
                    <td style="padding: 8px; color: var(--text-secondary);">${value['support']}</td>
                `;
                tbody.appendChild(row);
            }
        }
    }

    // Logs — terminal style
    const consoleDiv = document.getElementById('consoleOutput');
    const isAtBottom = consoleDiv.scrollHeight - consoleDiv.scrollTop - consoleDiv.clientHeight < 50;
    const prevScroll = consoleDiv.scrollTop;
    const visibleLogs = state.logs.slice(clearedLogCount);
    consoleDiv.innerHTML = '';

    if (visibleLogs.length === 0) {
        const msg = clearedLogCount > 0 ? 'History cleared.' : 'Ready. Click "Start Retraining" to begin.';
        consoleDiv.innerHTML = `<span style="color:#569cd6;">$</span> <span style="color:#6a9955;">${msg}</span>`;
    }

    visibleLogs.forEach(log => {
        const line = document.createElement('div');
        line.style.padding = '1px 0';

        // Color based on content
        let color = '#d4d4d4'; // default light gray
        let prefix = '<span style="color:#569cd6;">$</span> ';
        if (log.toLowerCase().includes('error') || log.includes('!!!')) {
            color = '#f44747';
            prefix = '<span style="color:#f44747;">!</span> ';
        } else if (log.toLowerCase().includes('warning') || log.toLowerCase().includes('stop')) {
            color = '#cca700';
            prefix = '<span style="color:#cca700;">~</span> ';
        } else if (log.toLowerCase().includes('complete') || log.toLowerCase().includes('saved') || log.toLowerCase().includes('activated')) {
            color = '#6a9955';
            prefix = '<span style="color:#6a9955;">&#10004;</span> ';
        } else if (log.startsWith('Epoch ')) {
            color = '#9cdcfe';
            prefix = '<span style="color:#4ec9b0;">></span> ';
        }

        line.innerHTML = prefix + `<span style="color:${color};">${log}</span>`;
        consoleDiv.appendChild(line);
    });

    if (isAtBottom) {
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    } else {
        consoleDiv.scrollTop = prevScroll;
    }

    // Button State
    const btn = document.getElementById('trainBtn');
    const stopBtn = document.getElementById('stopBtn');
    const fileInput = document.getElementById('fileInput');
    if (state.status === 'TRAINING' || state.status === 'STOPPING') {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-icons-outlined">hourglass_empty</span> Processing...';
        fileInput.disabled = true;
        if (stopBtn) stopBtn.style.display = (state.status === 'STOPPING') ? 'none' : 'inline-flex';
    } else {
        btn.disabled = enabledMajorIds.length < 2;
        btn.innerHTML = '<span class="material-icons-outlined">refresh</span> Start Retraining';
        fileInput.disabled = false;
        if (stopBtn) stopBtn.style.display = 'none';
    }
}

// Poll for status
let stoppingStartedAt = null;
setInterval(async () => {
    try {
        const response = await fetch('/api/ml/status/');
        const state = await response.json();

        // Safety: auto-reset if STOPPING hangs for 15+ seconds
        if (state.status === 'STOPPING') {
            if (!stoppingStartedAt) stoppingStartedAt = Date.now();
            if (Date.now() - stoppingStartedAt > 15000) {
                await fetch('/api/ml/stop/', { method: 'POST' }); // will reset to IDLE
                stoppingStartedAt = null;
            }
        } else {
            stoppingStartedAt = null;
        }

        updateUI(state);
    } catch (e) {
        console.error("Connection error", e);
    }
}, 1000);

// Stop training
async function stopTraining() {
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) {
        stopBtn.disabled = true;
        stopBtn.textContent = 'Stopping...';
    }
    try {
        await fetch('/api/ml/stop/', { method: 'POST' });
    } catch (e) {
        console.error('Stop error', e);
    }
}

// Handle Upload — inject enabled_majors as hidden form field
document.getElementById('uploadForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    if (enabledMajorIds.length < 2) {
        alert('Please select at least 2 majors before training.');
        return;
    }

    clearLogs();

    const formData = new FormData(this);
    // Append enabled majors as comma-separated string
    formData.set('enabled_majors', enabledMajorIds.join(','));

    const btn = document.getElementById('trainBtn');
    btn.disabled = true;
    btn.innerHTML = 'Uploading...';

    try {
        const response = await fetch('/api/ml/retrain/', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok) {
            alert(`Error: ${result.error}`);
            btn.disabled = false;
            btn.innerHTML = '<span class="material-icons-outlined">refresh</span> Start Retraining';
        } else {
            clearedLogCount = 0;
        }
    } catch (error) {
        alert("Network error.");
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons-outlined">refresh</span> Start Retraining';
    }
});

// Init
loadMajorConfig();
