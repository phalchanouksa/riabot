// --- Model History Logic ---

let currentModels = [];
const MAJOR_NAMES = ["IT", "BA", "HM", "GD", "MD", "ACC", "ME", "EE", "CE", "IE", "AE", "CHE", "EN", "TH", "CH", "BI"];

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

function showDetails(modelId) {
    const model = currentModels.find(m => m.id === modelId);
    if (!model) return;

    document.getElementById('modalTitle').textContent = `Model Details: ${model.id}`;

    // Config
    const configHtml = `
        <p><strong>Max Epochs:</strong> ${model.config.max_epochs}</p>
        <p><strong>Patience:</strong> ${model.config.patience}</p>
        <p><strong>Batch Size:</strong> ${model.config.batch_size}</p>
        <p><strong>Synthetic Samples:</strong> ${model.config.n_synthetic || 'N/A'}</p>
    `;
    document.getElementById('modalConfig').innerHTML = configHtml;

    // Summary
    const summaryHtml = `
        <p><strong>Test Accuracy:</strong> ${(model.metrics.test_accuracy * 100).toFixed(2)}%</p>
        <p><strong>Top-3 Accuracy:</strong> ${(model.metrics.top_k_accuracy * 100).toFixed(2)}%</p>
        <p><strong>Loss:</strong> ${model.metrics.loss ? model.metrics.loss.toFixed(4) : 'N/A'}</p>
    `;
    document.getElementById('modalSummary').innerHTML = summaryHtml;

    // Report Table
    const tbody = document.querySelector('#modalReportTable tbody');
    tbody.innerHTML = '';

    if (model.metrics.classification_report) {
        for (const [key, value] of Object.entries(model.metrics.classification_report)) {
            if (key === 'accuracy' || key === 'macro avg' || key === 'weighted avg') continue;

            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #e0e0e0';

            let className = key;
            if (!isNaN(key) && MAJOR_NAMES[parseInt(key)]) {
                className = MAJOR_NAMES[parseInt(key)];
            }

            row.innerHTML = `
                <td style="padding: 8px; font-weight: 500;">${className}</td>
                <td style="padding: 8px;">${(value['precision'] * 100).toFixed(1)}%</td>
                <td style="padding: 8px;">${(value['recall'] * 100).toFixed(1)}%</td>
                <td style="padding: 8px;">${(value['f1-score'] * 100).toFixed(1)}%</td>
                <td style="padding: 8px; color: #666;">${value['support']}</td>
            `;
            tbody.appendChild(row);
        }
    } else {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 16px; text-align: center;">No detailed report available.</td></tr>';
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
