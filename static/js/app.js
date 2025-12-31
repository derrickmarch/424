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
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
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
        const usage = await apiCall('/api/usage/twilio');
        displayUsageData(usage);
    } catch (error) {
        console.error('Failed to load usage data:', error);
        document.getElementById('twilio-balance').textContent = 'Error';
        document.getElementById('twilio-status').textContent = 'Error';
    }
}

function displayUsageData(usage) {
    // Display balance
    if (usage.balance && usage.balance !== 'N/A') {
        const balance = parseFloat(usage.balance);
        document.getElementById('twilio-balance').textContent = `${usage.currency} ${balance.toFixed(2)}`;
    } else {
        document.getElementById('twilio-balance').textContent = usage.error ? 'Error' : 'N/A';
    }
    
    // Display minutes and calls
    document.getElementById('twilio-minutes').textContent = usage.usage?.total_minutes || 0;
    document.getElementById('twilio-calls').textContent = usage.usage?.total_calls || 0;
    
    // Display account status
    const status = usage.account_status || 'unknown';
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
                <button class="btn btn-sm btn-primary" onclick="viewVerification('${v.verification_id}')">
                    View
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

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
document.addEventListener('DOMContentLoaded', () => {
    const page = document.body.dataset.page;
    
    if (page === 'dashboard') {
        loadDashboard();
        // Refresh dashboard every 30 seconds
        setInterval(loadDashboard, 30000);
        // Refresh usage data every 60 seconds
        setInterval(loadUsageData, 60000);
    } else if (page === 'verifications') {
        loadVerifications();
    }
});
