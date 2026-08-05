// ===== TAB NAVIGATION =====
function switchTab(tabName) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    
    const section = document.getElementById('section-' + tabName);
    const nav = document.querySelector(`[data-tab="${tabName}"]`);
    
    if (section) section.classList.add('active');
    if (nav) nav.classList.add('active');
    
    // Update header
    const titles = {
        overview: ['Overview', 'Real-time system metrics and analytics'],
        users: ['Users', 'Manage all registered subscribers'],
        topics: ['Topics', 'Topic categories and subscription breakdown'],
        logs: ['Delivery Logs', 'Message delivery history and status'],
        settings: ['Settings', 'System configuration and danger zone']
    };
    const t = titles[tabName] || ['Dashboard', ''];
    document.getElementById('page-title').textContent = t[0];
    document.getElementById('page-subtitle').textContent = t[1];
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ===== API HELPER =====
async function apiCall(url, method = 'POST', body = null) {
    const options = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) options.body = JSON.stringify(body);
    try {
        const resp = await fetch(url, options);
        return await resp.json();
    } catch (e) {
        console.error('API Error:', e);
        return { success: false, error: e.message };
    }
}

// ===== USER ACTIONS =====
async function pauseUser(chatId) {
    const result = await apiCall(`/admin/api/users/${chatId}/pause`);
    if (result.success) {
        showToast(`User ${chatId} paused`);
        // Update pill in UI
        const pill = document.getElementById(`status-${chatId}`);
        if (pill) {
            pill.className = 'pill pill-paused';
            pill.textContent = 'paused';
        }
        // Swap button
        const btn = document.getElementById(`toggle-${chatId}`);
        if (btn) {
            btn.title = 'Resume';
            btn.innerHTML = '▶';
            btn.className = 'btn-icon accent';
            btn.setAttribute('onclick', `resumeUser('${chatId}')`);
        }
    } else {
        showToast('Failed to pause user', 'error');
    }
}

async function resumeUser(chatId) {
    const result = await apiCall(`/admin/api/users/${chatId}/resume`);
    if (result.success) {
        showToast(`User ${chatId} resumed`);
        const pill = document.getElementById(`status-${chatId}`);
        if (pill) {
            pill.className = 'pill pill-active';
            pill.textContent = 'active';
        }
        const btn = document.getElementById(`toggle-${chatId}`);
        if (btn) {
            btn.title = 'Pause';
            btn.innerHTML = '⏸';
            btn.className = 'btn-icon amber';
            btn.setAttribute('onclick', `pauseUser('${chatId}')`);
        }
    } else {
        showToast('Failed to resume user', 'error');
    }
}

async function deleteUser(chatId) {
    if (!confirm(`Are you sure you want to delete user ${chatId}?`)) return;
    const result = await apiCall(`/admin/api/users/${chatId}/delete`);
    if (result.success) {
        showToast(`User ${chatId} deleted`);
        const row = document.getElementById(`row-${chatId}`);
        if (row) row.remove();
    } else {
        showToast('Failed to delete user', 'error');
    }
}

async function resendUser(chatId) {
    showToast(`Resending news to ${chatId}...`);
    const result = await apiCall(`/admin/api/users/${chatId}/resend`);
    if (result.success) {
        showToast(`News resent to ${chatId} successfully!`);
    } else {
        showToast('Failed to resend', 'error');
    }
}

// ===== SEARCH =====
function searchUsers() {
    const query = document.getElementById('user-search').value.toLowerCase();
    document.querySelectorAll('#users-tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

// ===== DELETE ALL MODAL =====
function openDeleteModal() {
    document.getElementById('delete-modal').classList.add('active');
    document.getElementById('delete-confirm-input').value = '';
    document.getElementById('delete-confirm-btn').disabled = true;
}

function closeDeleteModal() {
    document.getElementById('delete-modal').classList.remove('active');
}

function checkDeleteConfirmation() {
    const input = document.getElementById('delete-confirm-input').value;
    document.getElementById('delete-confirm-btn').disabled = (input !== 'DELETE');
}

async function confirmDeleteAll() {
    const input = document.getElementById('delete-confirm-input').value;
    if (input !== 'DELETE') return;
    
    const result = await apiCall('/admin/api/delete_all', 'POST', { confirmation: 'DELETE' });
    if (result.success) {
        showToast('All users deleted successfully');
        closeDeleteModal();
        setTimeout(() => location.reload(), 1500);
    } else {
        showToast('Failed to delete all users', 'error');
    }
}

// ===== BAR CHART ANIMATION =====
function animateBars() {
    document.querySelectorAll('.bar-fill').forEach(bar => {
        const target = bar.getAttribute('data-width');
        setTimeout(() => {
            bar.style.width = target + '%';
        }, 100);
    });
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    switchTab('overview');
    animateBars();
});
