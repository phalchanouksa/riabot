// Full 16-major name lookup (matches backend ALL_MAJOR_NAMES)
const ALL_MAJOR_NAMES = {
    0: "Agriculture",    1: "Architecture",   2: "Arts",          3: "Business",
    4: "Education",      5: "Finance",        6: "Government",    7: "Health",
    8: "Hospitality",    9: "Human Services", 10: "IT",           11: "Law",
    12: "Manufacturing", 13: "Sales",         14: "Science",      15: "Transport"
};

function showDetails(modelId) {
    const model = currentModels.find(m => m.id === modelId);
    if (!model) return;
    const c = model.config || {};
    const m = model.metrics || {};

    document.getElementById('modalTitle').textContent = `Model: ${model.id}`;

    // ── Helper ────────────────────────────────────────────────────────────
    const v = (val, fmt) => {
        if (val == null) return '—';
        if (fmt === '%') return (val * 100).toFixed(2) + '%';
        if (fmt === 'n') return val.toLocaleString();
        if (fmt === 'f') return val.toFixed(4);
        return val;
    };
    const card = (label, value, color) =>
        `<div style="background:#f8f9fa;padding:10px 14px;border-radius:10px;border:1px solid #eee;">
            <div style="font-size:11px;color:var(--text-secondary);margin-bottom:2px;">${label}</div>
            <div style="font-weight:600;font-size:16px;color:${color || 'var(--text-primary)'};">${value}</div>
        </div>`;

    // ── Trained Majors ────────────────────────────────────────────────────
    const enabledMajors = c.enabled_majors || null;
    let majorsHtml = '';
    if (enabledMajors && enabledMajors.length > 0) {
        const chips = enabledMajors.map(id =>
            `<span style="display:inline-block;padding:3px 10px;border-radius:100px;background:var(--accent-bg);color:var(--accent-color);font-size:11.5px;font-weight:500;margin:2px;">${ALL_MAJOR_NAMES[id] || 'Major ' + id}</span>`
        ).join('');
        majorsHtml = `
            <div style="margin-bottom:16px;">
                <div style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;font-weight:500;">
                    Trained Majors (${enabledMajors.length} / 16)
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;">${chips}</div>
            </div>`;
    } else {
        majorsHtml = `<div style="margin-bottom:16px;font-size:13px;color:var(--text-secondary);">Trained on all 16 majors (legacy model)</div>`;
    }

    // ── Config (top section) ──────────────────────────────────────────────
    const nSyn = v(c.n_synthetic, 'n');
    const nReal = v(c.n_real, 'n');
    const total = v(c.total_samples, 'n');
    const stoppedEp = c.stopped_epoch || '—';
    const bestEp = c.best_epoch || '—';
    const maxEp = c.max_epochs || '—';
    const finalLoss = v(c.final_loss, 'f');
    const testAcc = v(m.test_accuracy, '%');
    const top3Acc = v(m.top_k_accuracy, '%');

    const configHtml = `
        ${majorsHtml}
        <div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:8px;font-size:13px;">
            ${card('Test Accuracy', testAcc, 'var(--accent-color)')}
            ${card('Top-3 Accuracy', top3Acc, 'var(--success-color)')}
            ${card('Final Loss', finalLoss, finalLoss === '—' ? '' : '#e67700')}
            ${card('Synthetic Samples', nSyn, 'var(--accent-color)')}
            ${card('Real Samples', nReal, nReal === '—' || nReal === '0' ? 'var(--text-secondary)' : 'var(--success-color)')}
            ${card('Total Samples', total)}
            ${card('Epochs (ran / max)', stoppedEp + ' / ' + maxEp)}
            ${card('Best Epoch', bestEp)}
            ${card('Batch Size', c.batch_size || '—')}
        </div>
        <div style="margin-top:12px;font-size:12px;color:var(--text-secondary);">
            Trained: ${new Date(model.timestamp).toLocaleString()} &nbsp;|&nbsp;
            Patience: ${c.patience || '—'}
        </div>
    `;
    document.getElementById('modalConfig').innerHTML = configHtml;

    // ── Summary (weighted avg) ────────────────────────────────────────────
    let summaryHtml = '';
    if (m.classification_report && m.classification_report['weighted avg']) {
        const wa = m.classification_report['weighted avg'];
        summaryHtml = `
        <div style="background:#f8f9fa;padding:14px;border-radius:10px;font-size:13px;">
            <div style="font-weight:500;margin-bottom:8px;color:var(--text-primary);">Weighted Averages</div>
            <div style="display:flex;gap:24px;">
                <span>Precision: <strong>${(wa.precision * 100).toFixed(1)}%</strong></span>
                <span>Recall: <strong>${(wa.recall * 100).toFixed(1)}%</strong></span>
                <span>F1-Score: <strong>${(wa['f1-score'] * 100).toFixed(1)}%</strong></span>
                <span>Samples: <strong>${wa.support}</strong></span>
            </div>
        </div>`;
    }
    document.getElementById('modalSummary').innerHTML = summaryHtml;

    // ── Classification Report Table ───────────────────────────────────────
    const tbody = document.querySelector('#modalReportTable tbody');
    tbody.innerHTML = '';

    if (m.classification_report) {
        const classToName = {};
        if (enabledMajors) {
            enabledMajors.forEach((mid, idx) => {
                classToName[idx] = ALL_MAJOR_NAMES[mid] || `Major ${mid}`;
            });
        }

        for (const [key, value] of Object.entries(m.classification_report)) {
            if (key === 'accuracy' || key === 'macro avg' || key === 'weighted avg') continue;
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #f0f0f0';
            let className = key;
            if (!isNaN(key)) {
                const idx = parseInt(key);
                className = classToName[idx] || ALL_MAJOR_NAMES[idx] || key;
            }
            // Color-code F1 score
            const f1 = value['f1-score'] * 100;
            const f1Color = f1 >= 80 ? 'var(--success-color)' : f1 >= 50 ? '#e67700' : 'var(--error-color)';
            row.innerHTML = `
                <td style="padding: 8px; font-weight: 500;">${className}</td>
                <td style="padding: 8px;">${(value['precision'] * 100).toFixed(1)}%</td>
                <td style="padding: 8px;">${(value['recall'] * 100).toFixed(1)}%</td>
                <td style="padding: 8px; font-weight: 600; color: ${f1Color};">${f1.toFixed(1)}%</td>
                <td style="padding: 8px; color: #666;">${value['support']}</td>
            `;
            tbody.appendChild(row);
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 16px; text-align: center;">No detailed report available.</td></tr>';
    }

    // ── Confusion Matrix ──────────────────────────────────────────────────
    const cmThead = document.querySelector('#modalConfusionTable thead');
    const cmTbody = document.querySelector('#modalConfusionTable tbody');
    cmThead.innerHTML = '';
    cmTbody.innerHTML = '';

    const cm = m.confusion_matrix || (m.evaluation && m.evaluation.confusion_matrix);
    if (cm && cm.length > 0) {
        const classToName = {};
        if (enabledMajors) {
            enabledMajors.forEach((mid, idx) => {
                classToName[idx] = ALL_MAJOR_NAMES[mid] || `M${mid}`;
            });
        } else {
            for(let i=0; i<cm.length; i++) classToName[i] = ALL_MAJOR_NAMES[i] || `M${i}`;
        }

        const getShortName = (idx) => {
            const fullName = classToName[idx] || `C${idx}`;
            return fullName.substring(0, 3).toUpperCase();
        };

        let headerHtml = '<tr><th style="padding: 6px; border: 1px solid #e0e0e0; min-width: 80px; text-align: left; background: #f8f9fa;">Actual \\ Pred</th>';
        for (let i = 0; i < cm[0].length; i++) {
            headerHtml += `<th style="padding: 6px; border: 1px solid #e0e0e0; min-width: 30px; background: #f8f9fa;" title="${classToName[i]}">${getShortName(i)}</th>`;
        }
        headerHtml += '</tr>';
        cmThead.innerHTML = headerHtml;

        let maxVal = 0;
        for (let r = 0; r < cm.length; r++) {
            for (let c = 0; c < cm[r].length; c++) {
                if (cm[r][c] > maxVal) maxVal = cm[r][c];
            }
        }

        for (let r = 0; r < cm.length; r++) {
            let rowHtml = `<tr><td style="padding: 6px; border: 1px solid #e0e0e0; text-align: left; font-weight: 500; background: #f8f9fa; white-space: nowrap;" title="${classToName[r]}">${classToName[r]}</td>`;
            for (let c = 0; c < cm[r].length; c++) {
                const val = cm[r][c];
                const isDiagonal = r === c;
                const intensity = maxVal > 0 ? (val / maxVal) : 0;
                
                let bgColor = '#fff';
                let fgColor = '#333';
                if (val > 0) {
                    if (isDiagonal) {
                        const alpha = Math.max(0.1, intensity).toFixed(2);
                        bgColor = `rgba(32, 161, 68, ${alpha})`;
                        fgColor = intensity > 0.6 ? '#fff' : '#000';
                    } else {
                        const alpha = Math.max(0.1, Math.min(1, intensity * 2)).toFixed(2);
                        bgColor = `rgba(220, 53, 69, ${alpha})`;
                        fgColor = alpha > 0.6 ? '#fff' : '#000';
                    }
                }
                
                rowHtml += `<td style="padding: 6px; border: 1px solid #e0e0e0; background-color: ${bgColor}; color: ${fgColor};" title="Actual: ${classToName[r]} | Pred: ${classToName[c]}">${val}</td>`;
            }
            rowHtml += '</tr>';
            cmTbody.innerHTML += rowHtml;
        }
    } else {
        cmTbody.innerHTML = '<tr><td style="padding: 16px; text-align: center;">No confusion matrix available.</td></tr>';
    }

    document.getElementById('detailsModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('detailsModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function (event) {
    const modal = document.getElementById('detailsModal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

let currentModels = [];

async function loadModelHistory() {
    try {
        const response = await fetch('/api/ml/models/');
        const data = await response.json();
        currentModels = data.models || [];
        const tbody = document.querySelector('#modelHistoryTable tbody');
        tbody.innerHTML = '';

        if (!currentModels || currentModels.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 16px; text-align: center; color: #666;">No models found.</td></tr>';
            return;
        }

        currentModels.forEach(model => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #f0f0f0';

            // Format timestamp
            const date = new Date(model.timestamp);
            const dateStr = date.toLocaleString();

            // Metrics
            const acc = model.metrics.test_accuracy ? (model.metrics.test_accuracy * 100).toFixed(2) + '%' : '--';
            const top3 = model.metrics.top_k_accuracy ? (model.metrics.top_k_accuracy * 100).toFixed(2) + '%' : '--';

            // Status
            let statusHtml = '<span style="color: #666;">Inactive</span>';
            let actionsHtml = `
                <button onclick="showDetails('${model.id}')" style="cursor: pointer; color: var(--primary-color); background: none; border: none; font-weight: 500; margin-right: 8px;">Details</button>
                <button onclick="activateModel('${model.id}')" style="cursor: pointer; color: var(--accent-color); background: none; border: none; font-weight: 500;">Activate</button>
                <button onclick="deleteModel('${model.id}')" style="cursor: pointer; color: var(--error-color); background: none; border: none; margin-left: 8px;">Delete</button>
            `;

            if (model.is_active) {
                statusHtml = '<span style="color: var(--success-color); font-weight: 500;">Active</span>';
                actionsHtml = `
                    <button onclick="showDetails('${model.id}')" style="cursor: pointer; color: var(--primary-color); background: none; border: none; font-weight: 500; margin-right: 8px;">Details</button>
                    <span style="color: #ccc; margin-right: 8px;">Current</span>
                `;
            }

            row.innerHTML = `
                <td style="padding: 8px;">${dateStr}</td>
                <td style="padding: 8px;">${acc}</td>
                <td style="padding: 8px;">${top3}</td>
                <td style="padding: 8px;">${statusHtml}</td>
                <td style="padding: 8px; text-align: right;">${actionsHtml}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error("Error loading history:", e);
    }
}

async function activateModel(modelId) {
    if (!confirm("Are you sure you want to activate this model? It will be used for all future predictions.")) return;

    try {
        const response = await fetch('/api/ml/models/action/', {
            method: 'POST',
            body: JSON.stringify({ action: 'activate', model_id: modelId })
        });
        const result = await response.json();

        if (response.ok) {
            loadModelHistory();
            alert("Model activated successfully!");
        } else {
            alert("Error: " + result.error);
        }
    } catch (e) {
        alert("Network error");
    }
}

async function deleteModel(modelId) {
    if (!confirm("Are you sure you want to delete this model? This cannot be undone.")) return;

    try {
        const response = await fetch('/api/ml/models/action/', {
            method: 'POST',
            body: JSON.stringify({ action: 'delete', model_id: modelId })
        });
        const result = await response.json();

        if (response.ok) {
            loadModelHistory();
        } else {
            alert("Error: " + result.error);
        }
    } catch (e) {
        alert("Network error");
    }
}

// Initial Load
loadModelHistory();
loadDatasets();


// --- Dataset Management Logic ---

let currentDatasets = [];

async function loadDatasets() {
    try {
        const response = await fetch('/api/ml/datasets/');
        const data = await response.json();
        currentDatasets = data.datasets || [];
        const tbody = document.querySelector('#datasetsTable tbody');
        tbody.innerHTML = '';

        if (!currentDatasets || currentDatasets.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 16px; text-align: center; color: #666;">No datasets found. Upload a CSV file in the Retrain page.</td></tr>';
            return;
        }

        currentDatasets.forEach(dataset => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #f0f0f0';

            // Format date
            const date = new Date(dataset.modified);
            const dateStr = date.toLocaleString();

            // Format size
            const sizeKB = (dataset.size / 1024).toFixed(2);
            const sizeStr = sizeKB < 1024 ? `${sizeKB} KB` : `${(sizeKB / 1024).toFixed(2)} MB`;

            const actionsHtml = `
                <button onclick="showDatasetDetails('${dataset.filename}')" style="cursor: pointer; color: var(--primary-color); background: none; border: none; font-weight: 500; margin-right: 8px;">Details</button>
                <button onclick="deleteDataset('${dataset.filename}')" style="cursor: pointer; color: var(--error-color); background: none; border: none;">Delete</button>
            `;

            row.innerHTML = `
                <td style="padding: 8px; font-weight: 500;">${dataset.filename}</td>
                <td style="padding: 8px;">${sizeStr}</td>
                <td style="padding: 8px;">${dateStr}</td>
                <td style="padding: 8px;">${dataset.rows.toLocaleString()} rows</td>
                <td style="padding: 8px; text-align: right;">${actionsHtml}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error("Error loading datasets:", e);
    }
}

async function showDatasetDetails(filename) {
    try {
        const response = await fetch(`/api/ml/datasets/${filename}/`);
        const data = await response.json();

        if (!response.ok) {
            alert('Error: ' + data.error);
            return;
        }

        document.getElementById('datasetModalTitle').textContent = `Dataset: ${filename}`;

        // Format date
        const date = new Date(data.modified);
        const dateStr = date.toLocaleString();

        // Format size
        const sizeKB = (data.size / 1024).toFixed(2);
        const sizeStr = sizeKB < 1024 ? `${sizeKB} KB` : `${(sizeKB / 1024).toFixed(2)} MB`;

        let contentHtml = `
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin-bottom: 16px;">
                <p><strong>Filename:</strong> ${data.filename}</p>
                <p><strong>Size:</strong> ${sizeStr}</p>
                <p><strong>Modified:</strong> ${dateStr}</p>
                <p><strong>Total Rows:</strong> ${data.rows.toLocaleString()}</p>
                <p><strong>Columns:</strong> ${data.headers ? data.headers.length : 0}</p>
            </div>
        `;

        if (data.headers && data.headers.length > 0) {
            contentHtml += `
                <h3 style="font-size: 14px; font-weight: 500; margin-bottom: 8px;">Column Headers:</h3>
                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 16px; font-size: 12px;">
                    ${data.headers.join(', ')}
                </div>
            `;
        }

        if (data.preview && data.preview.length > 0) {
            contentHtml += `
                <h3 style="font-size: 14px; font-weight: 500; margin-bottom: 8px;">Preview (First 10 rows):</h3>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="border-bottom: 1px solid #e0e0e0;">
                                ${data.headers.map(h => `<th style="padding: 6px; text-align: left;">${h}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${data.preview.map(row => `
                                <tr style="border-bottom: 1px solid #f0f0f0;">
                                    ${row.map(cell => `<td style="padding: 6px;">${cell}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        document.getElementById('datasetModalContent').innerHTML = contentHtml;
        document.getElementById('datasetModal').style.display = 'block';
    } catch (e) {
        console.error("Error loading dataset details:", e);
        alert('Error loading dataset details');
    }
}

function closeDatasetModal() {
    document.getElementById('datasetModal').style.display = 'none';
}

// Close dataset modal when clicking outside
window.addEventListener('click', function (event) {
    const modal = document.getElementById('datasetModal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
});

async function deleteDataset(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}? This cannot be undone.`)) return;

    try {
        const response = await fetch(`/api/ml/datasets/${filename}/delete/`, {
            method: 'DELETE'
        });
        const result = await response.json();

        if (response.ok) {
            loadDatasets();
            alert('Dataset deleted successfully!');
        } else {
            alert('Error: ' + result.error);
        }
    } catch (e) {
        console.error("Error deleting dataset:", e);
        alert('Network error');
    }
}
