// Batch Monitoring JavaScript

class BatchMonitor {
    constructor() {
        this.currentBatchId = null;
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    async checkCurrentBatch() {
        try {
            const response = await fetch('/api/batch/current');
            const data = await response.json();
            
            if (data.batch_id) {
                this.currentBatchId = data.batch_id;
                this.showMonitor(data);
                this.connectWebSocket(data.batch_id);
            } else {
                this.hideMonitor();
            }
        } catch (error) {
            console.error('Error checking current batch:', error);
        }
    }

    showMonitor(batchData) {
        const monitorDiv = document.getElementById('batch-monitor');
        if (!monitorDiv) return;

        monitorDiv.style.display = 'block';
        this.updateUI(batchData);
    }

    hideMonitor() {
        const monitorDiv = document.getElementById('batch-monitor');
        if (monitorDiv) {
            monitorDiv.style.display = 'none';
        }
    }

    updateUI(data) {
        // Update status badge
        const statusBadge = document.getElementById('batch-status');
        if (statusBadge) {
            statusBadge.textContent = data.status.toUpperCase();
            statusBadge.className = `badge badge-${this.getStatusColor(data.status)}`;
        }

        // Update progress
        const progressBar = document.getElementById('batch-progress-bar');
        const progressText = document.getElementById('batch-progress-text');
        if (progressBar && data.total > 0) {
            const percentage = Math.round((data.processed / data.total) * 100);
            progressBar.style.width = percentage + '%';
            progressText.textContent = `${data.processed} / ${data.total} (${percentage}%)`;
        }

        // Update counts
        if (document.getElementById('batch-successful')) {
            document.getElementById('batch-successful').textContent = data.successful || 0;
        }
        if (document.getElementById('batch-failed')) {
            document.getElementById('batch-failed').textContent = data.failed || 0;
        }

        // Update current call info
        if (data.current_customer_name) {
            document.getElementById('current-customer').textContent = data.current_customer_name;
            document.getElementById('current-company').textContent = data.current_company_name;
            document.getElementById('current-call-info').style.display = 'block';
        } else {
            document.getElementById('current-call-info').style.display = 'none';
        }

        // Update transcript
        if (data.live_transcript) {
            document.getElementById('live-transcript-content').textContent = data.live_transcript;
            document.getElementById('live-transcript-section').style.display = 'block';
        }

        // Update logs
        if (data.logs && data.logs.length > 0) {
            this.updateLogs(data.logs);
        }

        // Update control buttons
        this.updateControlButtons(data.status);
    }

    updateLogs(logs) {
        const logsContainer = document.getElementById('batch-logs');
        if (!logsContainer) return;

        // Show last 20 logs
        const recentLogs = logs.slice(-20).reverse();
        
        logsContainer.innerHTML = recentLogs.map(log => `
            <div class="log-entry log-${log.level}">
                <span class="log-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
                <span class="log-level">[${log.level.toUpperCase()}]</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
    }

    updateControlButtons(status) {
        const pauseBtn = document.getElementById('batch-pause-btn');
        const resumeBtn = document.getElementById('batch-resume-btn');
        const stopBtn = document.getElementById('batch-stop-btn');

        if (status === 'running') {
            if (pauseBtn) pauseBtn.style.display = 'inline-block';
            if (resumeBtn) resumeBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-block';
        } else if (status === 'paused') {
            if (pauseBtn) pauseBtn.style.display = 'none';
            if (resumeBtn) resumeBtn.style.display = 'inline-block';
            if (stopBtn) stopBtn.style.display = 'inline-block';
        } else {
            if (pauseBtn) pauseBtn.style.display = 'none';
            if (resumeBtn) resumeBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'none';
        }
    }

    getStatusColor(status) {
        const colors = {
            'running': 'success',
            'paused': 'warning',
            'stopped': 'danger',
            'completed': 'info',
            'failed': 'danger',
            'idle': 'gray'
        };
        return colors[status] || 'gray';
    }

    connectWebSocket(batchId) {
        if (this.websocket) {
            this.websocket.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/batch/ws/${batchId}`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.websocket.onclose = () => {
            console.log('WebSocket closed');
            this.attemptReconnect(batchId);
        };

        // Keep connection alive
        this.pingInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
            }
        }, 30000); // Ping every 30 seconds
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial':
                this.updateUI(data.data);
                break;
            case 'progress':
                this.updateProgress(data);
                break;
            case 'current_call':
                this.updateCurrentCall(data);
                break;
            case 'log':
                this.addLog(data.log);
                break;
            case 'transcript':
                this.updateTranscript(data.transcript);
                break;
            case 'status':
                this.updateStatus(data.status);
                break;
        }
    }

    updateProgress(data) {
        const progressBar = document.getElementById('batch-progress-bar');
        const progressText = document.getElementById('batch-progress-text');
        if (progressBar && data.total > 0) {
            const percentage = Math.round((data.processed / data.total) * 100);
            progressBar.style.width = percentage + '%';
            progressText.textContent = `${data.processed} / ${data.total} (${percentage}%)`;
        }
        
        if (document.getElementById('batch-successful')) {
            document.getElementById('batch-successful').textContent = data.successful;
        }
        if (document.getElementById('batch-failed')) {
            document.getElementById('batch-failed').textContent = data.failed;
        }
    }

    updateCurrentCall(data) {
        document.getElementById('current-customer').textContent = data.customer_name;
        document.getElementById('current-company').textContent = data.company_name;
        document.getElementById('current-call-info').style.display = 'block';
    }

    addLog(log) {
        const logsContainer = document.getElementById('batch-logs');
        if (!logsContainer) return;

        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${log.level}`;
        logEntry.innerHTML = `
            <span class="log-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
            <span class="log-level">[${log.level.toUpperCase()}]</span>
            <span class="log-message">${log.message}</span>
        `;
        
        logsContainer.insertBefore(logEntry, logsContainer.firstChild);
        
        // Keep only last 20 logs
        while (logsContainer.children.length > 20) {
            logsContainer.removeChild(logsContainer.lastChild);
        }
    }

    updateTranscript(transcript) {
        document.getElementById('live-transcript-content').textContent = transcript;
        document.getElementById('live-transcript-section').style.display = 'block';
        
        // Auto-scroll to bottom
        const transcriptDiv = document.getElementById('live-transcript-content');
        transcriptDiv.scrollTop = transcriptDiv.scrollHeight;
    }

    updateStatus(status) {
        const statusBadge = document.getElementById('batch-status');
        if (statusBadge) {
            statusBadge.textContent = status.toUpperCase();
            statusBadge.className = `badge badge-${this.getStatusColor(status)}`;
        }
        
        this.updateControlButtons(status);
        
        // If completed or stopped, close monitor after a delay
        if (status === 'completed' || status === 'stopped') {
            setTimeout(() => {
                this.cleanup();
                this.hideMonitor();
            }, 5000);
        }
    }

    attemptReconnect(batchId) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
            setTimeout(() => {
                this.connectWebSocket(batchId);
            }, 2000 * this.reconnectAttempts);
        }
    }

    async pauseBatch() {
        if (!this.currentBatchId) return;
        
        try {
            const response = await fetch(`/api/batch/${this.currentBatchId}/pause`, {
                method: 'POST'
            });
            if (response.ok) {
                console.log('Batch paused');
            }
        } catch (error) {
            console.error('Error pausing batch:', error);
            alert('Failed to pause batch');
        }
    }

    async resumeBatch() {
        if (!this.currentBatchId) return;
        
        try {
            const response = await fetch(`/api/batch/${this.currentBatchId}/resume`, {
                method: 'POST'
            });
            if (response.ok) {
                console.log('Batch resumed');
            }
        } catch (error) {
            console.error('Error resuming batch:', error);
            alert('Failed to resume batch');
        }
    }

    async stopBatch() {
        if (!this.currentBatchId) return;
        
        if (!confirm('Are you sure you want to stop the batch? This cannot be undone.')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/batch/${this.currentBatchId}/stop`, {
                method: 'POST'
            });
            if (response.ok) {
                console.log('Batch stopped');
            }
        } catch (error) {
            console.error('Error stopping batch:', error);
            alert('Failed to stop batch');
        }
    }

    cleanup() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
        this.currentBatchId = null;
    }
}

// Global batch monitor instance
const batchMonitor = new BatchMonitor();

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('batch-monitor')) {
        batchMonitor.checkCurrentBatch();
        
        // Attach button handlers
        const pauseBtn = document.getElementById('batch-pause-btn');
        const resumeBtn = document.getElementById('batch-resume-btn');
        const stopBtn = document.getElementById('batch-stop-btn');
        
        if (pauseBtn) pauseBtn.onclick = () => batchMonitor.pauseBatch();
        if (resumeBtn) resumeBtn.onclick = () => batchMonitor.resumeBatch();
        if (stopBtn) stopBtn.onclick = () => batchMonitor.stopBatch();
    }
});
