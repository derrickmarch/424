// Main JavaScript for Account Verifier UI

const API_BASE = '';

// Utility Functions
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

function showSpinner() {
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.id = 'loading-spinner';
    document.body.appendChild(spinner);
}

function hideSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.remove();
}

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            // Redirect to login on unauthorized
            if (response.status === 401) {
                window.location.href = '/login';
                return Promise.reject(new Error('Not authenticated'));
            }
            let errorMsg = 'API request failed';
            try {
                const error = await response.json();
                errorMsg = error.detail || errorMsg;
            } catch (_) { /* ignore parse errors */ }
            throw new Error(errorMsg);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        showSpinner();
        
        // Load stats
        const stats = await apiCall('/api/verifications/stats/summary');
        displayStats(stats);
        
        // Load schedule status
        const schedule = await apiCall('/api/verifications/schedule/status');
        displayScheduleStatus(schedule);
        
        // Load recent verifications
        const verifications = await apiCall('/api/verifications/?limit=10');
        displayRecentVerifications(verifications);
        
        // Load Twilio usage data
        await loadUsageData();
        
        // Load system mode badge
        await loadSystemModeBadge();
        
        hideSpinner();
    } catch (error) {
        hideSpinner();
        showAlert('Failed to load dashboard: ' + error.message, 'danger');
    }
}

async function loadSystemModeBadge() {
    try {
        const badge = document.getElementById('system-mode-badge');
        if (!badge) return; // Badge doesn't exist on this page
        
        const mode = await apiCall('/api/settings/mode');
        
        if (mode.test_mode) {
            badge.innerHTML = '🧪 TEST MODE';
            badge.className = 'badge badge-warning';
            badge.title = 'System is running in test mode with mock services';
        } else {
            badge.innerHTML = '📞 LIVE MODE';
            badge.className = 'badge badge-success';
            badge.title = 'System is running in live mode with real APIs';
        }
    } catch (error) {
        console.error('Failed to load system mode:', error);
        const badge = document.getElementById('system-mode-badge');
        if (badge) {
            badge.innerHTML = '❓ UNKNOWN';
            badge.className = 'badge badge-gray';
        }
    }
}

async function loadUsageData() {
    try {
        const usage = await apiCall('/api/usage/provider');
        try {
            const providerSetting = await apiCall('/api/settings/telephony_provider');
            const prov = (providerSetting && providerSetting.setting_value) ? providerSetting.setting_value : 'twilio';
            const labelEl = document.getElementById('current-provider-label');
            if (labelEl) labelEl.textContent = prov.toUpperCase();
        } catch (e) { /* no-op */ }
        displayUsageData(usage);
    } catch (error) {
        console.error('Failed to load usage data:', error);
        const balEl = document.getElementById('provider-balance'); if (balEl) balEl.textContent = 'Error';
        const stEl = document.getElementById('provider-status'); if (stEl) stEl.textContent = 'Error';
    }
}

function displayUsageData(usage) {
    // Display balance
    if (usage.balance && usage.balance !== 'N/A') {
        const balance = parseFloat(usage.balance);
        document.getElementById('provider-balance').textContent = `${usage.currency} ${balance.toFixed(2)}`;
    } else {
        document.getElementById('provider-balance').textContent = usage.error ? 'Error' : 'N/A';
    }
    
    // Display minutes and calls
    document.getElementById('provider-minutes').textContent = usage.usage?.total_minutes || 0;
    document.getElementById('provider-calls').textContent = usage.usage?.total_calls || 0;
    
    // Display account status
    const status = usage.account_status || usage.status || 'unknown';
    let statusBadge = '';
    if (status === 'active') {
        statusBadge = '<span class="badge badge-success">Active</span>';
    } else if (status === 'suspended') {
        statusBadge = '<span class="badge badge-danger">Suspended</span>';
    } else {
        statusBadge = '<span class="badge badge-warning">' + status + '</span>';
    }
    document.getElementById('twilio-status').innerHTML = statusBadge;
    
    // Update last refresh time
    const now = new Date();
    document.getElementById('usage-last-update').textContent = now.toLocaleTimeString();
}

async function refreshUsageData() {
    try {
        showSpinner();
        await loadUsageData();
        hideSpinner();
        showAlert('Usage data refreshed!', 'success');
    } catch (error) {
        hideSpinner();
        showAlert('Failed to refresh usage data: ' + error.message, 'danger');
    }
}

function displayStats(stats) {
    document.getElementById('total-verifications').textContent = stats.total_verifications;
    document.getElementById('verified-count').textContent = stats.verified;
    document.getElementById('pending-count').textContent = stats.pending;
    document.getElementById('success-rate').textContent = stats.success_rate + '%';
}

function displayScheduleStatus(schedule) {
    const statusEl = document.getElementById('scheduler-status');
    const nextRunEl = document.getElementById('next-run');
    
    if (schedule.is_running) {
        statusEl.innerHTML = '<span class="badge badge-success">Running</span>';
    } else {
        statusEl.innerHTML = '<span class="badge badge-danger">Stopped</span>';
    }
    
    if (schedule.next_run_at) {
        const nextRun = new Date(schedule.next_run_at);
        nextRunEl.textContent = nextRun.toLocaleString();
    } else {
        nextRunEl.textContent = 'Not scheduled';
    }
}

function displayRecentVerifications(verifications) {
    const tbody = document.getElementById('recent-verifications-tbody');
    tbody.innerHTML = '';
    
    if (verifications.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No verifications yet</td></tr>';
        return;
    }
    
    verifications.forEach(v => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${v.verification_id}</td>
            <td>${v.customer_name}</td>
            <td>${v.company_name}</td>
            <td>${getStatusBadge(v.status)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewVerification('${v.verification_id}')">
                    View
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge badge-warning">Pending</span>',
        'calling': '<span class="badge badge-info">Calling</span>',
        'verified': '<span class="badge badge-success">Verified</span>',
        'not_found': '<span class="badge badge-danger">Not Found</span>',
        'needs_human': '<span class="badge badge-warning">Needs Human</span>',
        'failed': '<span class="badge badge-danger">Failed</span>'
    };
    return badges[status] || status;
}

// Verification Functions
async function createVerification(formData) {
    try {
        showSpinner();
        
        const data = {
            verification_id: formData.get('verification_id'),
            customer_name: formData.get('customer_name'),
            customer_phone: formData.get('customer_phone'),
            company_name: formData.get('company_name'),
            company_phone: formData.get('company_phone'),
            customer_email: formData.get('customer_email') || null,
            customer_address: formData.get('customer_address') || null,
            account_number: formData.get('account_number') || null,
            customer_date_of_birth: formData.get('customer_date_of_birth') || null,
            customer_ssn_last4: formData.get('customer_ssn_last4') || null,
            customer_ssn_full: formData.get('customer_ssn_full') || null,
            verification_instruction: formData.get('verification_instruction') || null,
            priority: parseInt(formData.get('priority')) || 0
        };
        
        await apiCall('/api/verifications/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        hideSpinner();
        showAlert('Verification created successfully!', 'success');
        
        // Redirect to list page
        setTimeout(() => window.location.href = '/verifications', 1500);
        
    } catch (error) {
        hideSpinner();
        showAlert('Failed to create verification: ' + error.message, 'danger');
    }
}

async function loadVerifications() {
    try {
        showSpinner();
        
        const verifications = await apiCall('/api/verifications/?limit=100');
        displayVerificationsList(verifications);
        
        hideSpinner();
    } catch (error) {
        hideSpinner();
        showAlert('Failed to load verifications: ' + error.message, 'danger');
    }
}

function displayVerificationsList(verifications) {
    const tbody = document.getElementById('verifications-tbody');
    tbody.innerHTML = '';
    
    if (verifications.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No verifications found</td></tr>';
        return;
    }
    
    verifications.forEach(v => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${v.verification_id}</td>
            <td>${v.customer_name}</td>
            <td>${v.customer_phone}</td>
            <td>${v.company_name}</td>
            <td>${getStatusBadge(v.status)}</td>
            <td>${v.attempt_count}</td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm btn-primary" onclick="viewVerification('${v.verification_id}')">View</button>
                    <button class="btn btn-sm btn-secondary" onclick="editVerification('${v.verification_id}')">Edit</button>
                    <button class="btn btn-sm btn-warning" onclick="clearVerification('${v.verification_id}')">Clear</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteVerification('${v.verification_id}')">Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function deleteVerification(verificationId) {
   if (!confirm(`Delete verification ${verificationId}? This cannot be undone.`)) return;
   try {
       await apiCall(`/api/verifications/${verificationId}`, { method: 'DELETE' });
       showAlert('Verification deleted', 'success');
       loadVerifications();
   } catch (e) {
       showAlert('Failed to delete: ' + e.message, 'danger');
   }
}

async function clearVerification(verificationId) {
   if (!confirm(`Clear status for ${verificationId}? This will reset attempts and remove logs.`)) return;
   try {
       await apiCall(`/api/verifications/${verificationId}/clear`, { method: 'POST' });
       showAlert('Verification cleared', 'success');
       loadVerifications();
   } catch (e) {
       showAlert('Failed to clear: ' + e.message, 'danger');
   }
}

async function editVerification(verificationId) {
    try {
        const v = await apiCall(`/api/verifications/${verificationId}`);
        // Populate modal form
        document.getElementById('edit-verification-id').value = v.verification_id;
        document.getElementById('edit-customer-name').value = v.customer_name || '';
        document.getElementById('edit-customer-phone').value = v.customer_phone || '';
        document.getElementById('edit-company-name').value = v.company_name || '';
        document.getElementById('edit-company-phone').value = v.company_phone || '';
        document.getElementById('edit-account-number').value = v.account_number || '';
        document.getElementById('edit-customer-email').value = v.customer_email || '';
        document.getElementById('edit-customer-address').value = v.customer_address || '';
        document.getElementById('edit-priority').value = v.priority || 0;
        openModal('edit-verification-modal');
    } catch (e) {
        showAlert('Failed to load for edit: ' + e.message, 'danger');
    }
}

// Handle edit modal submit
(function attachEditHandler(){
    document.addEventListener('DOMContentLoaded', () => {
        const form = document.getElementById('edit-verification-form');
        if (!form) return;
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const id = document.getElementById('edit-verification-id').value;
                const payload = {
                    verification_id: id,
                    customer_name: document.getElementById('edit-customer-name').value,
                    customer_phone: document.getElementById('edit-customer-phone').value,
                    company_name: document.getElementById('edit-company-name').value,
                    company_phone: document.getElementById('edit-company-phone').value,
                    customer_email: document.getElementById('edit-customer-email').value || null,
                    customer_address: document.getElementById('edit-customer-address').value || null,
                    account_number: document.getElementById('edit-account-number').value || null,
                    customer_date_of_birth: null,
                    customer_ssn_last4: null,
                    customer_ssn_full: null,
                    additional_customer_info: null,
                    verification_instruction: null,
                    information_to_collect: null,
                    priority: parseInt(document.getElementById('edit-priority').value || '0', 10)
                };
                await apiCall(`/api/verifications/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                showAlert('Verification updated', 'success');
                closeModal('edit-verification-modal');
                loadVerifications();
            } catch (err) {
                showAlert('Failed to save: ' + err.message, 'danger');
            }
        });
    });
})();

async function viewVerification(verificationId) {
    // Use the new detailed record viewer
    if (typeof viewRecordDetails !== 'undefined') {
        viewRecordDetails(verificationId);
    } else {
        // Fallback to simple view
        try {
            showSpinner();
            
            const verification = await apiCall(`/api/verifications/${verificationId}`);
            displayVerificationDetails(verification);
            
            hideSpinner();
        } catch (error) {
            hideSpinner();
            showAlert('Failed to load verification: ' + error.message, 'danger');
        }
    }
}

function displayVerificationDetails(v) {
    const modal = document.getElementById('verification-modal');
    const content = document.getElementById('verification-details');
    
    content.innerHTML = `
        <div class="form-group">
            <strong>Verification ID:</strong> ${v.verification_id}
        </div>
        <div class="form-group">
            <strong>Customer Name:</strong> ${v.customer_name}
        </div>
        <div class="form-group">
            <strong>Customer Phone:</strong> ${v.customer_phone}
        </div>
        <div class="form-group">
            <strong>Company:</strong> ${v.company_name}
        </div>
        <div class="form-group">
            <strong>Status:</strong> ${getStatusBadge(v.status)}
        </div>
        <div class="form-group">
            <strong>Attempts:</strong> ${v.attempt_count}
        </div>
        ${v.call_summary ? `<div class="form-group"><strong>Summary:</strong> ${v.call_summary}</div>` : ''}
        ${v.account_exists !== null ? `<div class="form-group"><strong>Account Exists:</strong> ${v.account_exists ? 'Yes' : 'No'}</div>` : ''}
    `;
    
    modal.classList.add('active');
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
}

// CSV Functions
async function handleCSVUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showSpinner();
        
        const response = await fetch('/api/csv/import', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        hideSpinner();
        
        if (response.ok) {
            showAlert(result.message, 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showAlert(result.detail || 'Upload failed', 'danger');
        }
    } catch (error) {
        hideSpinner();
        showAlert('Upload failed: ' + error.message, 'danger');
    }
}

async function downloadCSV() {
    try {
        showSpinner();
        
        const response = await fetch('/api/csv/export');
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'verifications_export.csv';
        a.click();
        
        hideSpinner();
        showAlert('CSV downloaded successfully!', 'success');
    } catch (error) {
        hideSpinner();
        showAlert('Download failed: ' + error.message, 'danger');
    }
}

// Scheduler Functions
async function triggerScheduler() {
    try {
        showSpinner();
        
        const result = await apiCall('/api/verifications/schedule/trigger', {
            method: 'POST'
        });
        
        hideSpinner();
        
        if (result.batch_id) {
            showAlert('Batch processing started!', 'success');
            
            // Show the batch monitor if it exists
            if (typeof batchMonitor !== 'undefined') {
                batchMonitor.currentBatchId = result.batch_id;
                batchMonitor.showMonitor(result);
                batchMonitor.connectWebSocket(result.batch_id);
            }
        } else {
            showAlert(result.message || 'No pending verifications to process', 'info');
        }
    } catch (error) {
        hideSpinner();
        showAlert('Failed to trigger scheduler: ' + error.message, 'danger');
    }
}

// Logout function
async function logout() {
    if (!confirm('Are you sure you want to logout?')) {
        return;
    }
    
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // Redirect to login page
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        showAlert('Failed to logout. Please try again.', 'danger');
    }
}

// Initialize page-specific functions
async function loadDashboardMode() {
    try {
        const res = await fetch('/api/settings/mode');
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('system-mode-badge');
            const btn = document.getElementById('toggle-mode-btn-dashboard');
            if (badge) {
                if (data.test_mode) {
                    badge.innerHTML = '🧪 TEST MODE';
                    badge.className = 'badge badge-warning';
                } else {
                    badge.innerHTML = '📞 LIVE MODE';
                    badge.className = 'badge badge-success';
                }
                const note = document.getElementById('mode-inline-note');
                if (note) note.style.display = data.test_mode ? 'block' : 'none';
            }
            if (btn) btn.disabled = false;
        }
    } catch (e) { console.error('Failed to load dashboard mode', e); }
}

async function toggleDashboardMode() {
    if (!confirm('Toggle between Test Mode and Live Mode? On local, you may need to restart the service for changes to fully apply. Continue?')) return;
    const btn = document.getElementById('toggle-mode-btn-dashboard');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Toggling...'; }
    try {
        const res = await fetch('/api/settings/mode/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
        const data = await res.json();
        if (res.ok) {
            alert('✅ ' + data.message + (data.restart_required ? '\nOn local, please restart the server to apply.' : ''));
            await loadDashboardMode();
        } else {
            alert('❌ Failed to toggle mode: ' + (data.detail || 'Unknown error'));
        }
    } catch (e) {
        alert('❌ Failed to toggle mode: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '🔄 Toggle Mode'; }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    
    if (page === 'dashboard') {
        loadDashboard();
        // Refresh dashboard every 30 seconds
        setInterval(loadDashboard, 30000);
        // Refresh usage data every 60 seconds
       setInterval(loadUsageData, 60000);
       // Load mode badge and enable toggle on dashboard
       loadDashboardMode();
   } else if (page === 'verifications') {
       loadVerifications();
    }
});
