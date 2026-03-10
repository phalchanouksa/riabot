const MAJOR_NAMES = ["IT", "BA", "HM", "GD", "MD", "ACC", "ME", "EE", "CE", "IE", "AE", "CHE", "EN", "TH", "CH", "BI"];
let clearedLogCount = 0;

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

let shouldUpdateClearCount = false;
let previousStatus = null;

function updateUI(state) {
    // Handle Clear Logic
    if (shouldUpdateClearCount) {
        clearedLogCount = state.logs.length;
        shouldUpdateClearCount = false;
    }

    // Check for completion to show notification or update UI state
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
        document.getElementById('evalPanel').style.display = 'none'; // Hide eval during training
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

        // Evaluation Panel Logic
        if (state.metrics.evaluation) {
            const evalMetrics = state.metrics.evaluation;
            document.getElementById('evalPanel').style.display = 'flex';
            document.getElementById('evalPanel').style.flexDirection = 'column';

            document.getElementById('evalTestAcc').textContent = (evalMetrics.test_accuracy * 100).toFixed(2) + '%';
            document.getElementById('evalTop3').textContent = (evalMetrics.top_k_accuracy * 100).toFixed(2) + '%';

            // Populate Table
            const tbody = document.querySelector('#classReportTable tbody');
            tbody.innerHTML = '';

            // Iterate through report
            for (const [key, value] of Object.entries(evalMetrics.classification_report)) {
                if (key === 'accuracy' || key === 'macro avg' || key === 'weighted avg') continue;

                const row = document.createElement('tr');
                row.style.borderBottom = '1px solid #f0f0f0';

                // Try to map class ID to Name
                let className = key;
                if (!isNaN(key) && MAJOR_NAMES[parseInt(key)]) {
                    className = MAJOR_NAMES[parseInt(key)];
                }

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

    // Logs
    const consoleDiv = document.getElementById('consoleOutput');
    const isAtBottom = consoleDiv.scrollHeight - consoleDiv.scrollTop - consoleDiv.clientHeight < 50;
    const prevScroll = consoleDiv.scrollTop;

    const visibleLogs = state.logs.slice(clearedLogCount);

    consoleDiv.innerHTML = '';

    if (visibleLogs.length === 0) {
        const entry = document.createElement('div');
        entry.className = 'log-bubble system';
        entry.textContent = clearedLogCount > 0 ? 'History cleared.' : 'Welcome to ML Engine. Ready to process data.';
        consoleDiv.appendChild(entry);
    }

    visibleLogs.forEach(log => {
        let className = 'log-bubble';
        if (log.toLowerCase().includes('error') || log.includes('!!!')) className += ' error';
        else if (log.toLowerCase().includes('warning')) className += ' warning';

        const entry = document.createElement('div');
        entry.className = className;
        entry.textContent = log;
        consoleDiv.appendChild(entry);
    });

    if (isAtBottom) {
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
    } else {
        consoleDiv.scrollTop = prevScroll;
    }

    // Button State
    const btn = document.getElementById('trainBtn');
    const fileInput = document.getElementById('fileInput');

    if (state.status === 'TRAINING') {
        btn.disabled = true;
        btn.innerHTML = '<span class="material-icons-outlined">hourglass_empty</span> Processing...';
        fileInput.disabled = true;
    } else {
        btn.disabled = false;
        btn.innerHTML = '<span class="material-icons-outlined">refresh</span> Start Retraining';
        fileInput.disabled = false;
    }
}

// Poll for status
setInterval(async () => {
    try {
        const response = await fetch('/api/ml/status/');
        const state = await response.json();
        updateUI(state);
    } catch (e) {
        console.error("Connection error", e);
    }
}, 1000);

// Handle Upload
document.getElementById('uploadForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    // Clear old logs when starting new training
    clearLogs();

    const formData = new FormData(this);
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
