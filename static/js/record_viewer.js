// Record Viewer with Detailed Logs

async function viewRecordDetails(verificationId) {
    try {
        // Show loading
        showSpinner();
        
        // Fetch detailed record data
        const response = await fetch(`/api/record-details/${verificationId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch record details');
        }
        
        const data = await response.json();
        
        // Display in modal
        displayRecordDetailsModal(data);
        
        hideSpinner();
    } catch (error) {
        hideSpinner();
        showAlert('Failed to load record details: ' + error.message, 'danger');
    }
}

function displayRecordDetailsModal(data) {
    const { verification, call_logs, summary } = data;
    
    // Create modal HTML
    const modalHTML = `
        <div id="record-details-modal" class="modal active" style="display: block;">
            <div class="modal-content" style="max-width: 900px; max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h2>📋 Record Details</h2>
                    <button onclick="closeRecordDetailsModal()" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                
                <div class="modal-body">
                    <!-- Overview Section -->
                    <div class="card" style="margin-bottom: 1rem;">
                        <div class="card-header">📊 Overview</div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem;">
                            <div><strong>Verification ID:</strong> ${verification.verification_id}</div>
                            <div><strong>Status:</strong> ${getStatusBadge(verification.status)}</div>
                            <div><strong>Customer:</strong> ${verification.customer_name}</div>
                            <div><strong>Company:</strong> ${verification.company_name}</div>
                            <div><strong>Customer Phone:</strong> ${verification.customer_phone}</div>
                            <div><strong>Company Phone:</strong> ${verification.company_phone}</div>
                            <div><strong>Attempts:</strong> ${verification.attempt_count}</div>
                            <div><strong>Priority:</strong> ${verification.priority}</div>
                        </div>
                    </div>
                    
                    <!-- Summary Stats -->
                    <div class="card" style="margin-bottom: 1rem;">
                        <div class="card-header">📈 Summary</div>
                        <div class="stats-grid" style="grid-template-columns: repeat(4, 1fr);">
                            <div class="stat-card">
                                <div class="stat-value">${summary.total_attempts}</div>
                                <div class="stat-label">Total Attempts</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${summary.total_call_duration}s</div>
                                <div class="stat-label">Call Duration</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${summary.has_transcript ? '✅' : '❌'}</div>
                                <div class="stat-label">Has Transcript</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${summary.needs_follow_up ? '⚠️' : '✅'}</div>
                                <div class="stat-label">Follow-up</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Customer Information -->
                    <div class="card" style="margin-bottom: 1rem;">
                        <div class="card-header">👤 Customer Information</div>
                        <div style="padding: 1rem;">
                            ${verification.customer_email ? `<div><strong>Email:</strong> ${verification.customer_email}</div>` : ''}
                            ${verification.customer_address ? `<div><strong>Address:</strong> ${verification.customer_address}</div>` : ''}
                            ${verification.account_number ? `<div><strong>Account Number:</strong> ${verification.account_number}</div>` : ''}
                            ${verification.customer_date_of_birth ? `<div><strong>Date of Birth:</strong> ${verification.customer_date_of_birth}</div>` : ''}
                            ${verification.customer_ssn_last4 ? `<div><strong>SSN Last 4:</strong> ${verification.customer_ssn_last4}</div>` : ''}
                            ${verification.additional_customer_info ? `<div><strong>Additional Info:</strong> <pre>${JSON.stringify(verification.additional_customer_info, null, 2)}</pre></div>` : ''}
                        </div>
                    </div>
                    
                    <!-- Verification Results -->
                    ${verification.call_summary || verification.account_exists !== null ? `
                    <div class="card" style="margin-bottom: 1rem;">
                        <div class="card-header">✅ Verification Results</div>
                        <div style="padding: 1rem;">
                            ${verification.account_exists !== null ? `
                                <div style="margin-bottom: 1rem;">
                                    <strong>Account Exists:</strong> 
                                    <span class="badge badge-${verification.account_exists ? 'success' : 'danger'}">
                                        ${verification.account_exists ? 'Yes' : 'No'}
                                    </span>
                                </div>
                            ` : ''}
                            ${verification.call_outcome ? `
                                <div style="margin-bottom: 1rem;">
                                    <strong>Call Outcome:</strong> ${verification.call_outcome}
                                </div>
                            ` : ''}
                            ${verification.call_summary ? `
                                <div style="margin-bottom: 1rem;">
                                    <strong>Summary:</strong><br>
                                    <div style="background: #f5f5f5; padding: 1rem; border-radius: 5px; margin-top: 0.5rem;">
                                        ${verification.call_summary}
                                    </div>
                                </div>
                            ` : ''}
                            ${verification.account_details ? `
                                <div>
                                    <strong>Account Details:</strong><br>
                                    <pre style="background: #f5f5f5; padding: 1rem; border-radius: 5px; margin-top: 0.5rem;">${JSON.stringify(verification.account_details, null, 2)}</pre>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- Transcript -->
                    ${verification.transcript ? `
                    <div class="card" style="margin-bottom: 1rem;">
                        <div class="card-header">🎙️ Call Transcript</div>
                        <div style="padding: 1rem;">
                            <div style="background: #f9f9f9; border: 1px solid #ddd; padding: 1rem; border-radius: 5px; max-height: 300px; overflow-y: auto; font-family: monospace; white-space: pre-wrap;">
${verification.transcript}
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <!-- Call Logs -->
                    <div class="card">
                        <div class="card-header">📞 Call History (${call_logs.length} calls)</div>
                        <div style="padding: 1rem;">
                            ${call_logs.length > 0 ? call_logs.map((log, index) => `
                                <div class="call-log-entry" style="background: ${index % 2 === 0 ? '#f9f9f9' : '#fff'}; padding: 1rem; border-radius: 5px; margin-bottom: 1rem; border-left: 4px solid ${getCallOutcomeColor(log.call_outcome)};">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                        <strong>Attempt #${log.attempt_number}</strong>
                                        <span class="badge badge-${getCallStatusBadgeType(log.call_status)}">${log.call_status || 'unknown'}</span>
                                    </div>
                                    
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9em; color: #666;">
                                        <div><strong>Call SID:</strong> ${log.call_sid || 'N/A'}</div>
                                        <div><strong>Outcome:</strong> ${log.call_outcome || 'N/A'}</div>
                                        <div><strong>From:</strong> ${log.from_number}</div>
                                        <div><strong>To:</strong> ${log.to_number}</div>
                                        <div><strong>Duration:</strong> ${log.duration_seconds || 0}s</div>
                                        <div><strong>Created:</strong> ${new Date(log.created_at).toLocaleString()}</div>
                                    </div>
                                    
                                    ${log.initiated_at ? `<div style="margin-top: 0.5rem; font-size: 0.85em;"><strong>Initiated:</strong> ${new Date(log.initiated_at).toLocaleString()}</div>` : ''}
                                    ${log.answered_at ? `<div style="font-size: 0.85em;"><strong>Answered:</strong> ${new Date(log.answered_at).toLocaleString()}</div>` : ''}
                                    ${log.completed_at ? `<div style="font-size: 0.85em;"><strong>Completed:</strong> ${new Date(log.completed_at).toLocaleString()}</div>` : ''}
                                    
                                    ${log.error_message ? `
                                        <div style="margin-top: 0.5rem; padding: 0.5rem; background: #ffebee; border-radius: 3px;">
                                            <strong style="color: #d32f2f;">Error:</strong> ${log.error_message}
                                        </div>
                                    ` : ''}
                                    
                                    ${log.conversation_log ? `
                                        <div style="margin-top: 0.5rem;">
                                            <strong>Conversation Log:</strong>
                                            <pre style="background: #f5f5f5; padding: 0.5rem; border-radius: 3px; margin-top: 0.25rem; font-size: 0.85em; max-height: 150px; overflow-y: auto;">${JSON.stringify(log.conversation_log, null, 2)}</pre>
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('') : '<div style="text-align: center; color: #999; padding: 2rem;">No call logs available</div>'}
                        </div>
                    </div>
                    
                    <!-- Timestamps -->
                    <div class="card" style="margin-top: 1rem;">
                        <div class="card-header">🕒 Timestamps</div>
                        <div style="padding: 1rem; font-size: 0.9em;">
                            <div><strong>Created:</strong> ${new Date(verification.created_at).toLocaleString()}</div>
                            <div><strong>Updated:</strong> ${new Date(verification.updated_at).toLocaleString()}</div>
                            ${verification.last_attempt_at ? `<div><strong>Last Attempt:</strong> ${new Date(verification.last_attempt_at).toLocaleString()}</div>` : ''}
                            ${verification.completed_at ? `<div><strong>Completed:</strong> ${new Date(verification.completed_at).toLocaleString()}</div>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeRecordDetailsModal()">Close</button>
                    ${verification.status === 'failed' || verification.status === 'needs_human' ? `
                        <button class="btn btn-primary" onclick="retryVerification('${verification.verification_id}')">🔄 Retry</button>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('record-details-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function getCallOutcomeColor(outcome) {
    const colors = {
        'account_found': '#4CAF50',
        'account_not_found': '#FF9800',
        'needs_verification': '#2196F3',
        'needs_human': '#FF9800',
        'no_answer': '#9E9E9E',
        'voicemail': '#9E9E9E',
        'failed': '#f44336',
        'busy': '#FF9800'
    };
    return colors[outcome] || '#ddd';
}

function getCallStatusBadgeType(status) {
    const types = {
        'completed': 'success',
        'initiated': 'info',
        'ringing': 'info',
        'answered': 'success',
        'failed': 'danger',
        'busy': 'warning',
        'no-answer': 'warning'
    };
    return types[status] || 'gray';
}

function closeRecordDetailsModal() {
    const modal = document.getElementById('record-details-modal');
    if (modal) {
        modal.remove();
    }
}

async function retryVerification(verificationId) {
    if (!confirm('Are you sure you want to retry this verification?')) {
        return;
    }
    
    try {
        showSpinner();
        
        const response = await fetch(`/api/verifications/${verificationId}/retry`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to retry verification');
        }
        
        hideSpinner();
        showAlert('Verification reset to pending!', 'success');
        closeRecordDetailsModal();
        
        // Reload page after delay
        setTimeout(() => location.reload(), 1500);
    } catch (error) {
        hideSpinner();
        showAlert('Failed to retry: ' + error.message, 'danger');
    }
}

// Make viewRecordDetails available globally
window.viewRecordDetails = viewRecordDetails;
window.closeRecordDetailsModal = closeRecordDetailsModal;
window.retryVerification = retryVerification;
