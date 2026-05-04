/**
 * AI 测试用例生成器 v3.0 - 全功能版
 * 新增：回收站、复制用例、导入用例、API Key 查看/隐藏、全屏模式
 */

// ========== 后端 API 地址配置 ==========
// 部署时修改此处为后端服务的实际地址，例如 "https://your-backend.railway.app"
// 本地开发时留空即可（使用相对路径，由同源服务器处理）
const API_BASE = 'https://testcase-generator-production.up.railway.app';

// ========== 认证管理 ==========
function getToken() { return localStorage.getItem('tcg_token'); }
function setToken(token) { localStorage.setItem('tcg_token', token); }
function clearToken() { localStorage.removeItem('tcg_token'); }
function getUser() { try { return JSON.parse(localStorage.getItem('tcg_user')); } catch { return null; } }
function setUser(user) { localStorage.setItem('tcg_user', JSON.stringify(user)); }
function clearUser() { localStorage.removeItem('tcg_user'); }

function checkAuth() {
    const token = getToken();
    if (!token) {
        showAuthPage();
        return false;
    }
    showMainApp();
    return true;
}

function showAuthPage() {
    document.getElementById('authPage').style.display = 'flex';
    document.getElementById('mainApp').style.display = 'none';
}

function showMainApp() {
    document.getElementById('authPage').style.display = 'none';
    document.getElementById('mainApp').style.display = '';
    const user = getUser();
    if (user) document.getElementById('userName').textContent = user.username;
}

function switchToRegister() {
    document.getElementById('authLoginForm').style.display = 'none';
    document.getElementById('authRegisterForm').style.display = '';
    document.getElementById('authError').style.display = 'none';
    document.getElementById('regError').style.display = 'none';
}

function switchToLogin() {
    document.getElementById('authLoginForm').style.display = '';
    document.getElementById('authRegisterForm').style.display = 'none';
    document.getElementById('authError').style.display = 'none';
    document.getElementById('regError').style.display = 'none';
}

async function doLogin() {
    const username = document.getElementById('authUsername').value.trim();
    const password = document.getElementById('authPassword').value;
    const errEl = document.getElementById('authError');
    if (!username || !password) { errEl.textContent = '请输入用户名和密码'; errEl.style.display = ''; return; }
    errEl.style.display = 'none';
    try {
        const resp = await fetch(API_BASE + '/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || '登录失败');
        setToken(data.token);
        setUser(data.user);
        showMainApp();
        loadQuickStats();
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = '';
    }
}

async function doRegister() {
    const username = document.getElementById('regUsername').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regPasswordConfirm').value;
    const errEl = document.getElementById('regError');
    if (!username || !password) { errEl.textContent = '请输入用户名和密码'; errEl.style.display = ''; return; }
    if (password.length < 6) { errEl.textContent = '密码至少6个字符'; errEl.style.display = ''; return; }
    if (password !== confirm) { errEl.textContent = '两次密码不一致'; errEl.style.display = ''; return; }
    errEl.style.display = 'none';
    try {
        const resp = await fetch(API_BASE + '/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || '注册失败');
        setToken(data.token);
        setUser(data.user);
        showMainApp();
    } catch (e) {
        errEl.textContent = e.message;
        errEl.style.display = '';
    }
}

function doLogout() {
    clearToken();
    clearUser();
    showAuthPage();
    switchToLogin();
}

// ========== 全局状态 ==========
let currentDocId = null;
let allDocuments = [];
let docSearchTimer = null;
let tcSearchTimer = null;
let docPage = 1;
let tcPage = 1;
let trashPage = 1;
let viewMode = 'table';
let selectedPriority = null;
let apiKeyVisible = false;
let sortOrder = 'asc';
let logPage = 1;
let _lastDeletedIds = [];
let _lastDeletedType = '';
let _globalDragCounter = 0;
let _pendingUploadFiles = [];
let _draftSaveTimer = null;
let _isGenerating = false;  // 生成状态标记
const DRAFT_KEY = 'tcg_generate_draft';
const GEN_STATE_KEY = 'tcg_gen_state';  // 生成进度持久化

// ========== API ==========
async function api(url, options = {}) {
    const fullUrl = API_BASE + url;
    const defaultHeaders = {};
    if (!(options.body instanceof FormData)) defaultHeaders['Content-Type'] = 'application/json';
    const token = getToken();
    if (token) defaultHeaders['Authorization'] = 'Bearer ' + token;
    const resp = await fetch(fullUrl, { ...options, headers: { ...defaultHeaders, ...options.headers } });
    if (resp.status === 401) {
        clearToken(); clearUser(); showAuthPage();
        throw new Error('登录已过期，请重新登录');
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    return resp;
}
async function apiJson(url, options = {}) { return (await api(url, options)).json(); }

// ========== Toast 通知系统 (v3.3 堆叠式) ==========
const _toastContainer = (() => {
    let c = document.getElementById('toastContainer');
    if (!c) {
        c = document.createElement('div');
        c.id = 'toastContainer';
        c.className = 'toast-container';
        document.body.appendChild(c);
    }
    return c;
})();

function showToast(message, type = 'info') {
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span class="toast-msg">${escHtml(String(message))}</span><button class="toast-close" onclick="this.closest('.toast-item').classList.add('fade-out');setTimeout(()=>this.closest('.toast-item')?.remove(),300)">&times;</button>`;
    _toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }
    }, 3000);
}
// 向后兼容
const toast = showToast;

// ========== Command Palette (v3.3) ==========
let _cmdPaletteOpen = false;
let _cmdSelectedIdx = 0;
let _cmdFiltered = [];

const _commands = [
    { name: '上传文档', icon: '📤', shortcut: 'Ctrl+U', action() { document.querySelector('.nav-item[data-view="upload"]')?.click(); } },
    { name: 'AI生成用例', icon: '🤖', shortcut: 'Ctrl+G', action() { if (allDocuments.length) openGenerateModal(allDocuments[0].id, allDocuments[0].filename); else showToast('请先上传文档','warning'); } },
    { name: '导出Excel', icon: '📊', shortcut: 'Ctrl+E', action() { doExport('excel'); } },
    { name: '导出CSV', icon: '📄', shortcut: '', action() { doExport('csv'); } },
    { name: '搜索用例', icon: '🔍', shortcut: 'Ctrl+Shift+F', action() { document.querySelector('.nav-item[data-view="testcases"]')?.click(); setTimeout(()=>document.getElementById('tcSearch')?.focus(),100); } },
    { name: '切换主题', icon: '🌓', shortcut: '', action() { toggleTheme(); } },
    { name: '查看统计', icon: '📊', shortcut: '', action() { document.querySelector('.nav-item[data-view="stats"]')?.click(); } },
    { name: '清空用例', icon: '🧹', shortcut: '', action() { clearAllTestcases(); } },
    { name: '打开回收站', icon: '🗑️', shortcut: '', action() { document.querySelector('.nav-item[data-view="trash"]')?.click(); } },
    { name: '操作日志', icon: '📜', shortcut: '', action() { document.querySelector('.nav-item[data-view="logs"]')?.click(); } },
    { name: 'Prompt模板管理', icon: '📝', shortcut: '', action() { document.querySelector('.nav-item[data-view="settings"]')?.click(); } },
    { name: '设置', icon: '⚙️', shortcut: '', action() { document.querySelector('.nav-item[data-view="settings"]')?.click(); } },
    { name: '自动化测试', icon: '🤖', shortcut: '', action() { document.querySelector('.nav-item[data-view="executor"]')?.click(); } },
    { name: '测试套件', icon: '📦', shortcut: '', action() { document.querySelector('.nav-item[data-view="suites"]')?.click(); } },
    { name: '执行仪表盘', icon: '📊', shortcut: '', action() { document.querySelector('.nav-item[data-view="dashboard"]')?.click(); } },
    { name: '测试报告', icon: '📄', shortcut: '', action() { document.querySelector('.nav-item[data-view="reports"]')?.click(); } },
    { name: '环境检测', icon: '🔧', shortcut: '', action() { document.querySelector('.nav-item[data-view="env"]')?.click(); } },
];

function openCommandPalette() {
    const modal = document.getElementById('commandPaletteModal');
    if (!modal) return;
    _cmdPaletteOpen = true;
    _cmdSelectedIdx = 0;
    modal.classList.add('show');
    const input = document.getElementById('cmdPaletteInput');
    input.value = '';
    input.focus();
    renderCommandList('');
}

function closeCommandPalette() {
    _cmdPaletteOpen = false;
    document.getElementById('commandPaletteModal')?.classList.remove('show');
}

function renderCommandList(filter) {
    const q = filter.toLowerCase().trim();
    _cmdFiltered = q ? _commands.filter(c => c.name.toLowerCase().includes(q) || c.icon.includes(q)) : [..._commands];
    if (_cmdSelectedIdx >= _cmdFiltered.length) _cmdSelectedIdx = 0;
    const list = document.getElementById('cmdPaletteList');
    if (!list) return;
    list.innerHTML = _cmdFiltered.map((c, i) =>
        `<div class="cmd-item${i === _cmdSelectedIdx ? ' active' : ''}" data-idx="${i}" onmouseenter="_cmdSelectedIdx=${i};renderCommandList(document.getElementById('cmdPaletteInput').value)" onclick="executeCommand(${i})">
            <span class="cmd-icon">${c.icon}</span>
            <span class="cmd-name">${escHtml(c.name)}</span>
            ${c.shortcut ? `<span class="cmd-shortcut">${c.shortmap || c.shortcut}</span>` : ''}
        </div>`
    ).join('');
}

function executeCommand(idx) {
    const cmd = _cmdFiltered[idx];
    if (cmd) { closeCommandPalette(); cmd.action(); }
}

document.getElementById('cmdPaletteInput')?.addEventListener('input', e => {
    _cmdSelectedIdx = 0;
    renderCommandList(e.target.value);
});

document.getElementById('cmdPaletteInput')?.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); _cmdSelectedIdx = Math.min(_cmdSelectedIdx + 1, _cmdFiltered.length - 1); renderCommandList(e.target.value); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); _cmdSelectedIdx = Math.max(_cmdSelectedIdx - 1, 0); renderCommandList(e.target.value); }
    else if (e.key === 'Enter') { e.preventDefault(); executeCommand(_cmdSelectedIdx); }
    else if (e.key === 'Escape') { closeCommandPalette(); }
});

// ========== Inline Editing (v3.3) ==========
const _editableFields = ['title', 'module', 'steps', 'expected_result', 'priority', 'case_type'];
let _editingCell = null;

function startInlineEdit(td, tcId, field) {
    if (_editingCell) return; // already editing
    _editingCell = { td, tcId, field, original: td.innerHTML };
    const currentText = td.textContent.trim();
    let input;

    if (field === 'priority') {
        input = document.createElement('select');
        ['P0','P1','P2','P3'].forEach(p => { const o = document.createElement('option'); o.value = p; o.textContent = p; if (p === currentText) o.selected = true; input.appendChild(o); });
    } else if (field === 'case_type') {
        input = document.createElement('select');
        ['功能测试','边界测试','异常测试','流程测试','接口测试'].forEach(t => { const o = document.createElement('option'); o.value = t; o.textContent = t; if (t === currentText) o.selected = true; input.appendChild(o); });
    } else if (field === 'steps' || field === 'expected_result') {
        input = document.createElement('textarea');
        input.value = currentText;
        input.rows = 3;
    } else {
        input = document.createElement('input');
        input.type = 'text';
        input.value = currentText;
    }
    input.className = 'inline-edit-input';
    td.innerHTML = '';
    td.appendChild(input);
    input.focus();
    if (input.select) input.select();

    const saveEdit = async () => {
        const newVal = input.value.trim();
        if (newVal === currentText) { cancelInlineEdit(); return; }
        try {
            await api(`/api/testcases/${tcId}`, { method: 'PUT', body: JSON.stringify({ [field]: newVal }) });
            td.innerHTML = field === 'priority' ? `<span class="priority-badge ${newVal}">${newVal}</span>` : field === 'case_type' ? `<span class="type-badge">${escHtml(newVal)}</span>` : escHtml(newVal);
            td.classList.add('edit-saved');
            setTimeout(() => td.classList.remove('edit-saved'), 1000);
            showToast('已保存', 'success');
        } catch (e) {
            showToast(`保存失败: ${e.message}`, 'error');
            td.innerHTML = _editingCell.original;
        }
        _editingCell = null;
    };

    const cancelInlineEdit = () => {
        if (_editingCell) { td.innerHTML = _editingCell.original; _editingCell = null; }
    };

    input.addEventListener('blur', () => setTimeout(saveEdit, 150));
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); input.blur(); }
        if (e.key === 'Escape') { e.preventDefault(); cancelInlineEdit(); }
    });
}

// ========== Version History Panel (v3.3) ==========
let _historyTcId = null;

async function openHistoryPanel(tcId) {
    _historyTcId = tcId;
    const panel = document.getElementById('historyPanel');
    const content = document.getElementById('historyContent');
    if (!panel || !content) return;
    panel.classList.add('open');
    content.innerHTML = '<div class="loading-text">加载历史记录...</div>';
    try {
        const data = await apiJson(`/api/testcases/${tcId}/history`);
        const versions = data.history || data.versions || [];
        if (!versions.length) {
            content.innerHTML = `<div class="empty-state" style="padding:40px 16px">
                <div class="empty-icon">📜</div>
                <div class="empty-title">暂无历史版本</div>
            </div>`;
            return;
        }
        content.innerHTML = versions.map((v, idx) => {
            const changes = v.changes || v.changed_fields || {};
            const changeHtml = Object.entries(changes).map(([k, val]) =>
                `<div class="history-change"><span class="history-field">${escHtml(k)}</span><div class="history-diff"><del>${escHtml(val.old || '')}</del><br><ins>${escHtml(val.new || val)}</ins></div></div>`
            ).join('');
            return `<div class="history-version${idx === 0 ? ' latest' : ''}">
                <div class="history-version-header">
                    <span class="history-timestamp">${escHtml(v.timestamp || v.created_at || '')}</span>
                    ${idx === 0 ? '<span class="history-badge-latest">当前</span>' : `<button class="btn btn-outline btn-sm" onclick="restoreHistory(${v.id || v.version_id})">♻️ 恢复</button>`}
                </div>
                ${changeHtml || `<div class="history-change"><span class="history-field">完整快照</span></div>`}
            </div>`;
        }).join('');
    } catch (e) {
        content.innerHTML = `<div class="empty-state" style="padding:40px 16px"><p>加载失败: ${escHtml(e.message)}</p></div>`;
    }
}

function closeHistoryPanel() {
    document.getElementById('historyPanel')?.classList.remove('open');
    _historyTcId = null;
}

async function restoreHistory(versionId) {
    try {
        await api(`/api/history/${versionId}/restore`, { method: 'POST' });
        showToast('版本已恢复', 'success');
        closeHistoryPanel();
        loadTestcases();
    } catch (e) { showToast(`恢复失败: ${e.message}`, 'error'); }
}

// ========== 排序 ==========
function toggleSortOrder() {
    sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    document.getElementById('sortOrderBtn').textContent = sortOrder === 'asc' ? '↑' : '↓';
    tcPage = 1;
    loadTestcases();
}

// ========== 搜索高亮 ==========
function highlightText(text, keyword) {
    if (!keyword || !text) return escHtml(text);
    const safe = escHtml(text);
    const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return safe.replace(new RegExp('(' + escaped + ')', 'gi'), '<mark class="search-highlight">$1</mark>');
}

// ========== 剪贴板复制 ==========
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        toast('已复制到剪贴板', 'success');
    } catch (e) {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        toast('已复制到剪贴板', 'success');
    }
}

// ========== 主题 ==========
function toggleTheme() {
    const html = document.documentElement;
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    document.getElementById('themeIcon').textContent = next === 'dark' ? '🌙' : '☀️';
    localStorage.setItem('theme', next);
}
function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    document.getElementById('themeIcon').textContent = saved === 'dark' ? '🌙' : '☀️';
}

// ========== 视图切换 ==========
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
        e.preventDefault();
        const view = item.dataset.view;
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${view}`).classList.add('active');
        if (view === 'testcases') loadTestcases();
        if (view === 'settings') { loadConfig(); loadTemplateList(); }
        if (view === 'logs') loadLogs();
        if (view === 'stats') loadStats();
        if (view === 'trash') loadTrash();
        if (view === 'executor') loadExecTestcases();
        if (view === 'suites') loadSuites();
        if (view === 'dashboard') loadDashboard();
        if (view === 'reports') loadReports();
        if (view === 'env') loadEnvCheck();
        document.getElementById('sidebar').classList.remove('open');
    });
});

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
document.querySelector('.content').addEventListener('click', () => document.getElementById('sidebar').classList.remove('open'));

// ========== 快捷统计 ==========
async function loadQuickStats() {
    try {
        const data = await apiJson('/api/stats');
        document.getElementById('qsDocs').textContent = data.documents.total;
        document.getElementById('qsTcTotal').textContent = data.testcases.total;
        document.getElementById('qsP0').textContent = data.testcases.by_priority.P0 || 0;
        document.getElementById('qsP1').textContent = data.testcases.by_priority.P1 || 0;
        document.getElementById('qsP2').textContent = data.testcases.by_priority.P2 || 0;
        document.getElementById('qsP3').textContent = data.testcases.by_priority.P3 || 0;
    } catch (e) { /* silent */ }
}

// ========== 文件上传 ==========
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) handleMultipleFiles(Array.from(e.dataTransfer.files));
});
dropZone.addEventListener('click', e => { if (e.target.tagName !== 'BUTTON') fileInput.click(); });
fileInput.addEventListener('change', () => { if (fileInput.files.length > 0) handleMultipleFiles(Array.from(fileInput.files)); });

// 允许的文件类型
const ALLOWED_TYPES = ['.md','.docx','.json','.txt','.pdf','.xlsx','.csv'];
const FILE_ICONS = { '.md':'📝', '.docx':'📄', '.json':'🔧', '.txt':'📃', '.pdf':'📕', '.xlsx':'📊', '.csv':'📈' };

function getFileIcon(filename) {
    const ext = '.' + filename.split('.').pop().toLowerCase();
    return FILE_ICONS[ext] || '📁';
}

function handleMultipleFiles(files) {
    const validFiles = files.filter(f => {
        const ext = '.' + f.name.split('.').pop().toLowerCase();
        return ALLOWED_TYPES.includes(ext);
    });
    if (!validFiles.length) { toast('请选择支持的文件格式', 'error'); return; }
    _pendingUploadFiles = validFiles;
    renderFileList();
    // 开始上传
    validFiles.forEach((file, idx) => uploadFileAtIndex(idx));
}

function renderFileList() {
    // 如果已有文件列表容器则复用，否则在dropZone下方创建
    let listEl = document.getElementById('pendingFileList');
    if (!listEl) {
        listEl = document.createElement('div');
        listEl.id = 'pendingFileList';
        listEl.className = 'file-list';
        dropZone.parentElement.insertBefore(listEl, dropZone.nextSibling);
    }
    listEl.innerHTML = _pendingUploadFiles.map((f, i) =>
        `<div class="file-list-item" id="fileItem${i}">
            <span class="file-icon">${getFileIcon(f.name)}</span>
            <span class="file-name">${escHtml(f.name)}</span>
            <span class="file-size">${formatFileSize(f.size)}</span>
            <div class="file-progress"><div class="file-progress-fill" id="fileProg${i}" style="width:0%"></div></div>
            <button class="file-remove" onclick="removeFileFromList(${i})">✕</button>
        </div>`
    ).join('');
}

function removeFileFromList(idx) {
    _pendingUploadFiles.splice(idx, 1);
    renderFileList();
}

async function uploadFileAtIndex(idx) {
    const file = _pendingUploadFiles[idx];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    const fill = document.getElementById(`fileProg${idx}`);
    const progress = document.getElementById('uploadProgress');
    const progText = document.getElementById('progressText');
    progress.style.display = '';
    progText.textContent = `正在上传 ${file.name}...`;
    let pct = 10;
    if (fill) fill.style.width = '10%';
    const timer = setInterval(() => { pct = Math.min(pct + Math.random() * 15, 90); if (fill) fill.style.width = pct + '%'; }, 300);
    try {
        const data = await apiJson('/api/documents/upload', { method: 'POST', body: formData });
        clearInterval(timer);
        if (fill) fill.style.width = '100%';
        progText.textContent = '上传完成！';
        toast(`上传成功: ${data.filename}`, 'success');
        fileInput.value = '';
        docPage = 1;
        loadDocuments();
        loadQuickStats();
        setTimeout(() => { progress.style.display = 'none'; }, 2000);
    } catch (e) {
        clearInterval(timer);
        if (fill) fill.style.width = '0%';
        toast(`上传失败: ${e.message}`, 'error');
    }
}

// 单文件上传（兼容旧逻辑）
async function uploadFile(file) {
    handleMultipleFiles([file]);
}

document.getElementById('submitTextBtn').addEventListener('click', async () => {
    const title = document.getElementById('textTitle').value.trim();
    const content = document.getElementById('textContent').value.trim();
    const docType = document.getElementById('textType').value;
    if (!title) { toast('请输入文档标题', 'error'); return; }
    if (!content || content.length < 10) { toast('请输入文档内容（至少10个字符）', 'error'); return; }
    try {
        toast('正在提交...', 'info');
        await apiJson('/api/documents/text', { method: 'POST', body: JSON.stringify({ title, content, doc_type: docType }) });
        toast('提交成功', 'success');
        document.getElementById('textTitle').value = '';
        document.getElementById('textContent').value = '';
        docPage = 1;
        loadDocuments();
        loadQuickStats();
    } catch (e) { toast(`提交失败: ${e.message}`, 'error'); }
});

// ========== 文档列表 ==========
async function loadDocuments() {
    showDocSkeleton();
    const search = document.getElementById('docSearch')?.value || '';
    try {
        const data = await apiJson(`/api/documents?${new URLSearchParams({ page: docPage, page_size: 12, search })}`);
        allDocuments = data.documents;
        renderDocuments(data.documents);
        renderDocPagination(data);
        updateDocFilter(data.documents);
    } catch (e) {
        document.getElementById('documentsList').innerHTML = `<div class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-title">暂无文档</div>
            <div class="empty-desc">上传需求文档或粘贴内容，AI 将自动生成测试用例</div>
        </div>`;
    }
}

function renderDocuments(docs) {
    const c = document.getElementById('documentsList');
    if (!docs.length) {
        c.innerHTML = `<div class="empty-state">
            <div class="empty-icon">📭</div>
            <div class="empty-title">暂无文档</div>
            <div class="empty-desc">上传需求文档或粘贴内容，AI 将自动生成测试用例</div>
        </div>`;
        return;
    }
    c.innerHTML = docs.map(doc => {
        const sz = doc.file_size ? formatFileSize(doc.file_size) : '';
        return `<div class="doc-card">
            <div class="doc-card-header"><h4 title="${escHtml(doc.filename)}">${escHtml(doc.filename)}</h4><span class="doc-badge ${doc.doc_type}">${doc.doc_type}</span></div>
            <div class="doc-preview">${escHtml(doc.content_preview || '')}</div>
            <div class="doc-meta"><span>${doc.created_at || ''}</span>${sz ? `<span>${sz}</span>` : ''}</div>
            <div class="doc-actions">
                <button class="btn btn-gradient btn-sm" onclick="openGenerateModal(${doc.id}, '${escAttr(doc.filename)}')">🤖 AI 生成</button>
                <button class="btn btn-outline btn-sm" onclick="previewDocument(${doc.id})">👁</button>
                <button class="btn btn-outline btn-sm" onclick="deleteDocument(${doc.id})">🗑</button>
            </div>
        </div>`;
    }).join('');
}

function renderDocPagination(data) {
    const c = document.getElementById('docPagination');
    if (!data || data.total_pages <= 1) { c.innerHTML = ''; return; }
    let h = `<button class="page-btn" onclick="goDocPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`;
    const s = Math.max(1, data.page - 2), e = Math.min(data.total_pages, data.page + 2);
    if (s > 1) h += `<button class="page-btn" onclick="goDocPage(1)">1</button>`;
    if (s > 2) h += `<span class="page-info">...</span>`;
    for (let i = s; i <= e; i++) h += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="goDocPage(${i})">${i}</button>`;
    if (e < data.total_pages - 1) h += `<span class="page-info">...</span>`;
    if (e < data.total_pages) h += `<button class="page-btn" onclick="goDocPage(${data.total_pages})">${data.total_pages}</button>`;
    h += `<button class="page-btn" onclick="goDocPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''}>›</button>`;
    h += `<span class="page-info">${data.total} 个文档</span>`;
    c.innerHTML = h;
}
function goDocPage(p) { docPage = p; loadDocuments(); }
function debounceDocSearch() { clearTimeout(docSearchTimer); docSearchTimer = setTimeout(() => { docPage = 1; loadDocuments(); }, 400); }
function updateDocFilter(docs) {
    const s = document.getElementById('filterDoc'), cur = s.value;
    s.innerHTML = '<option value="">全部文档</option>';
    docs.forEach(d => { s.innerHTML += `<option value="${d.id}">${escHtml(d.filename)}</option>`; });
    s.value = cur;
}

// ========== 文档预览 ==========
async function previewDocument(docId) {
    try {
        const data = await apiJson(`/api/documents/${docId}/preview`);
        document.getElementById('previewMeta').innerHTML = `<strong>${escHtml(data.filename)}</strong> · ${data.doc_type} · ${formatFileSize(data.content_length)}`;
        document.getElementById('previewContent').textContent = data.content;
        document.getElementById('previewModal').classList.add('show');
    } catch (e) { toast(`预览失败: ${e.message}`, 'error'); }
}
function closePreviewModal() { document.getElementById('previewModal').classList.remove('show'); }

// ========== 文档删除 ==========
async function deleteDocument(docId) {
    if (!confirm('确定要删除该文档及其所有测试用例吗？')) return;
    try { await api(`/api/documents/${docId}`, { method: 'DELETE' }); toast('删除成功', 'success'); loadDocuments(); loadQuickStats(); }
    catch (e) { toast(`删除失败: ${e.message}`, 'error'); }
}

// ========== AI 生成 ==========
let _promptTemplates = [];

async function loadPromptTemplates() {
    try {
        const data = await apiJson('/api/prompt-templates');
        _promptTemplates = data.templates || [];
        // 更新生成弹窗的模板选择器
        const sel = document.getElementById('genPromptTemplate');
        if (sel) {
            const cur = sel.value;
            sel.innerHTML = '<option value="">系统默认</option>';
            _promptTemplates.forEach(t => {
                sel.innerHTML += `<option value="${t.id}">${escHtml(t.name)}${t.is_default ? ' ⭐' : ''}</option>`;
            });
            sel.value = cur;
        }
    } catch (e) { /* silent */ }
}

function onPromptTemplateChange() {
    // 模板选择变化时隐藏预览
    document.getElementById('promptPreview').style.display = 'none';
}

function previewPromptTemplate() {
    const sel = document.getElementById('genPromptTemplate');
    const preview = document.getElementById('promptPreview');
    if (!sel.value) {
        preview.textContent = '系统默认 Prompt：你是一位资深的软件测试工程师...（完整的结构化测试用例生成指令）';
        preview.style.display = preview.style.display === 'none' ? '' : 'none';
        return;
    }
    const tpl = _promptTemplates.find(t => t.id === parseInt(sel.value));
    if (tpl) {
        preview.textContent = tpl.content;
        preview.style.display = preview.style.display === 'none' ? '' : 'none';
    }
}

function toggleCustomPrompt() {
    const ta = document.getElementById('genCustomPrompt');
    const arrow = document.getElementById('customPromptArrow');
    if (ta.style.display === 'none') {
        ta.style.display = '';
        arrow.textContent = '▾';
    } else {
        ta.style.display = 'none';
        arrow.textContent = '▸';
    }
}

// ========== Auto-Save Draft ==========
function saveDraft() {
    const template = document.getElementById('genPromptTemplate')?.value || '';
    const customPrompt = document.getElementById('genCustomPrompt')?.value || '';
    const testTypes = [];
    document.querySelectorAll('input[name="testType"]:checked').forEach(cb => testTypes.push(cb.value));
    const draft = { template, customPrompt, testTypes };
    try {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
        // Show brief indicator
        const indicator = document.getElementById('draftIndicator');
        if (indicator) { indicator.classList.add('show'); setTimeout(() => indicator.classList.remove('show'), 1500); }
    } catch (e) { /* quota exceeded - silent */ }
}

function restoreDraft() {
    try {
        const raw = localStorage.getItem(DRAFT_KEY);
        if (!raw) return;
        const draft = JSON.parse(raw);
        if (draft.template !== undefined) {
            const sel = document.getElementById('genPromptTemplate');
            // Delay setting value since templates load async
            setTimeout(() => { if (sel) sel.value = draft.template; }, 300);
        }
        if (draft.customPrompt) {
            document.getElementById('genCustomPrompt').value = draft.customPrompt;
            document.getElementById('genCustomPrompt').style.display = '';
            document.getElementById('customPromptArrow').textContent = '▾';
        } else {
            document.getElementById('genCustomPrompt').value = '';
            document.getElementById('genCustomPrompt').style.display = 'none';
            document.getElementById('customPromptArrow').textContent = '▸';
        }
        if (draft.testTypes && draft.testTypes.length) {
            document.querySelectorAll('input[name="testType"]').forEach(cb => {
                cb.checked = draft.testTypes.includes(cb.value);
            });
        }
    } catch (e) { /* corrupted draft - ignore */ }
}

function clearDraft() {
    try { localStorage.removeItem(DRAFT_KEY); } catch (e) {}
}

function _debouncedSaveDraft() {
    clearTimeout(_draftSaveTimer);
    _draftSaveTimer = setTimeout(saveDraft, 500);
}

function setupDraftAutoSave() {
    const templateSel = document.getElementById('genPromptTemplate');
    const promptTA = document.getElementById('genCustomPrompt');
    if (templateSel) templateSel.addEventListener('change', _debouncedSaveDraft);
    if (promptTA) promptTA.addEventListener('input', _debouncedSaveDraft);
    document.querySelectorAll('input[name="testType"]').forEach(cb => {
        cb.addEventListener('change', _debouncedSaveDraft);
    });
}

function clearDraftAutoSave() {
    const templateSel = document.getElementById('genPromptTemplate');
    const promptTA = document.getElementById('genCustomPrompt');
    if (templateSel) templateSel.removeEventListener('change', _debouncedSaveDraft);
    if (promptTA) promptTA.removeEventListener('input', _debouncedSaveDraft);
    document.querySelectorAll('input[name="testType"]').forEach(cb => {
        cb.removeEventListener('change', _debouncedSaveDraft);
    });
    clearTimeout(_draftSaveTimer);
}

// ========== Filter Chips ==========
function renderFilterChips() {
    const container = document.getElementById('filterChips');
    const list = document.getElementById('filterChipsList');
    const navItem = document.querySelector('.nav-item[data-view="testcases"]');
    if (!container || !list) return;

    const docVal = document.getElementById('filterDoc').value;
    const priorityVal = document.getElementById('filterPriority').value;
    const typeVal = document.getElementById('filterType').value;
    const searchVal = document.getElementById('tcSearch')?.value || '';
    let chips = '';
    let count = 0;

    if (priorityVal) {
        chips += `<span class="filter-chip chip-priority"><span class="chip-label">优先级:</span> ${priorityVal}<span class="chip-remove" onclick="removeFilter('priority')">✕</span></span>`;
        count++;
    }
    if (typeVal) {
        chips += `<span class="filter-chip chip-type"><span class="chip-label">类型:</span> ${escHtml(typeVal)}<span class="chip-remove" onclick="removeFilter('type')">✕</span></span>`;
        count++;
    }
    if (docVal) {
        const docName = allDocuments.find(d => d.id === parseInt(docVal))?.filename || docVal;
        chips += `<span class="filter-chip chip-document"><span class="chip-label">文档:</span> ${escHtml(docName)}<span class="chip-remove" onclick="removeFilter('doc')">✕</span></span>`;
        count++;
    }
    if (searchVal) {
        chips += `<span class="filter-chip chip-search"><span class="chip-label">搜索:</span> ${escHtml(searchVal)}<span class="chip-remove" onclick="removeFilter('search')">✕</span></span>`;
        count++;
    }

    list.innerHTML = chips;
    container.classList.toggle('has-chips', count > 0);

    // Update sidebar badge
    if (navItem) {
        navItem.classList.toggle('has-filter', count > 0);
        let badge = navItem.querySelector('.filter-count-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'filter-count-badge';
            navItem.appendChild(badge);
        }
        badge.textContent = count;
        badge.style.display = count > 0 ? '' : 'none';
    }
}

function removeFilter(type) {
    if (type === 'priority') document.getElementById('filterPriority').value = '';
    if (type === 'type') document.getElementById('filterType').value = '';
    if (type === 'doc') document.getElementById('filterDoc').value = '';
    if (type === 'search') { document.getElementById('tcSearch').value = ''; }
    tcPage = 1;
    loadTestcases();
}

function clearAllFilters() {
    document.getElementById('filterPriority').value = '';
    document.getElementById('filterType').value = '';
    document.getElementById('filterDoc').value = '';
    document.getElementById('tcSearch').value = '';
    tcPage = 1;
    loadTestcases();
}

// ========== Skeleton Loading ==========
function showTestcaseSkeleton() {
    const c = document.getElementById('testcasesContainer');
    let h = '<div class="skeleton-table-container"><div class="skeleton-toolbar"></div>';
    for (let i = 0; i < 8; i++) {
        const w1 = 40 + Math.random() * 30;
        const w2 = 50 + Math.random() * 40;
        const w3 = 60 + Math.random() * 30;
        const w4 = 30 + Math.random() * 20;
        h += `<div class="skeleton-row">
            <div class="skeleton-cell skeleton" style="width:${w1}px"></div>
            <div class="skeleton-cell skeleton" style="width:${w2}px"></div>
            <div class="skeleton-cell skeleton" style="flex:1;min-width:80px"></div>
            <div class="skeleton-cell skeleton" style="width:${w4}px"></div>
            <div class="skeleton-cell skeleton" style="width:${w3}px"></div>
        </div>`;
    }
    h += '</div>';
    c.innerHTML = h;
}

function showStatsSkeleton() {
    const c = document.getElementById('statsContent');
    let h = '';
    for (let i = 0; i < 4; i++) h += '<div class="skeleton-stat-card skeleton"></div>';
    c.innerHTML = h;
}

function showDocSkeleton() {
    const c = document.getElementById('documentsList');
    c.innerHTML = '<div class="loading-skeleton"><div class="skeleton-card"></div><div class="skeleton-card"></div><div class="skeleton-card"></div></div>';
}

// ========== Global Drag-Drop ==========
function initGlobalDragDrop() {
    const overlay = document.getElementById('globalDropOverlay');
    const filesEl = document.getElementById('globalDropFiles');

    document.addEventListener('dragenter', e => {
        e.preventDefault();
        _globalDragCounter++;
        if (e.dataTransfer.types.includes('Files')) {
            overlay.classList.add('visible');
        }
    });
    document.addEventListener('dragover', e => { e.preventDefault(); });
    document.addEventListener('dragleave', e => {
        e.preventDefault();
        _globalDragCounter--;
        if (_globalDragCounter <= 0) {
            _globalDragCounter = 0;
            overlay.classList.remove('visible');
        }
    });
    document.addEventListener('drop', e => {
        e.preventDefault();
        _globalDragCounter = 0;
        overlay.classList.remove('visible');
        if (e.dataTransfer.files.length > 0) {
            // 如果不在上传页面，先切换
            const uploadView = document.querySelector('.nav-item[data-view="upload"]');
            if (!document.getElementById('view-upload').classList.contains('active')) {
                uploadView?.click();
            }
            // 延迟后处理文件
            setTimeout(() => handleMultipleFiles(Array.from(e.dataTransfer.files)), 300);
        }
    });

    // Update overlay file names on drag
    document.addEventListener('dragover', e => {
        if (e.dataTransfer.types.includes('Files') && overlay.classList.contains('visible')) {
            const items = e.dataTransfer.items;
            if (items && items.length) {
                const names = Array.from(items).filter(i => i.kind === 'file').map(i => i.type ? i.type.split('/')[0] : '文件');
                filesEl.textContent = `准备上传 ${items.length} 个文件`;
            }
        }
    });
}

// ========== Enhanced Empty States ==========
function getEmptyStateHtml(type) {
    switch (type) {
        case 'no-testcases':
            return `<div class="empty-state">
                <div class="empty-icon">📋</div>
                <div class="empty-title">还没有测试用例</div>
                <div class="empty-desc">上传需求文档，AI 将自动生成结构化的测试用例</div>
                <button class="empty-action" onclick="document.querySelector('.nav-item[data-view=&quot;upload&quot;]').click()">📤 上传文档开始生成</button>
            </div>`;
        case 'no-results':
            return `<div class="empty-state">
                <div class="empty-icon">🔍</div>
                <div class="empty-title">没有找到匹配的用例</div>
                <div class="empty-desc">尝试调整筛选条件或清除搜索关键词</div>
            </div>`;
        case 'empty-trash':
            return `<div class="empty-state">
                <div class="empty-icon">🗑️</div>
                <div class="empty-title">回收站是空的</div>
                <div class="empty-desc">删除的测试用例将出现在这里，可随时恢复</div>
            </div>`;
        case 'no-logs':
            return `<div class="empty-state">
                <div class="empty-icon">📜</div>
                <div class="empty-title">暂无操作记录</div>
                <div class="empty-desc">上传文档、生成用例等操作将记录在此</div>
            </div>`;
        case 'no-templates':
            return `<div class="empty-state">
                <div class="empty-icon">📝</div>
                <div class="empty-title">暂无自定义模板</div>
                <div class="empty-desc">创建 Prompt 模板以生成特定类型的测试用例</div>
                <button class="empty-action" onclick="openCreateTemplateModal()">➕ 新建模板</button>
            </div>`;
        default:
            return '';
    }
}

function openGenerateModal(docId, docName) {
    currentDocId = docId;
    document.getElementById('genDocName').textContent = docName;
    document.getElementById('generateStatus').innerHTML = '';
    document.getElementById('generateStatus').className = 'status-area';
    document.getElementById('startGenerateBtn').disabled = false;
    document.getElementById('promptPreview').style.display = 'none';
    loadPromptTemplates();
    // 恢复草稿
    restoreDraft();
    // 设置自动保存
    setupDraftAutoSave();
    document.getElementById('generateModal').classList.add('show');
}
function closeGenerateModal() {
    document.getElementById('generateModal').classList.remove('show');
    currentDocId = null;
    if (window._abortController) window._abortController.abort();
    setGenerating(false);  // 解锁界面
    // 清除自动保存监听
    clearDraftAutoSave();
}

document.getElementById('startGenerateBtn').addEventListener('click', async () => {
    if (!currentDocId) return;
    const testTypes = [];
    document.querySelectorAll('input[name="testType"]:checked').forEach(cb => testTypes.push(cb.value));
    if (!testTypes.length) { toast('请至少选择一种测试用例类型', 'error'); return; }

    // 获取自定义 Prompt
    let customPrompt = document.getElementById('genCustomPrompt').value.trim();
    if (!customPrompt) {
        // 使用选中的模板
        const tplId = document.getElementById('genPromptTemplate').value;
        if (tplId) {
            const tpl = _promptTemplates.find(t => t.id === parseInt(tplId));
            if (tpl && tpl.name !== '默认模板') {
                customPrompt = tpl.content;
            }
        }
    }

    const statusEl = document.getElementById('generateStatus');
    const btn = document.getElementById('startGenerateBtn');
    btn.disabled = true;
    statusEl.className = 'status-area show loading';
    statusEl.innerHTML = '<span class="spinner"></span> AI 正在分析文档并生成测试用例...';
    setGenerating(true, { docId: currentDocId, types: testTypes });  // 锁定界面
    const abortCtrl = new AbortController();
    window._abortController = abortCtrl;

    const requestBody = {
        document_id: currentDocId,
        test_types: testTypes,
        custom_prompt: customPrompt || null
    };
    try {
        const resp = await fetch(API_BASE + '/api/testcases/generate/stream', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify(requestBody),
            signal: abortCtrl.signal
        });
        const reader = resp.body.getReader(), decoder = new TextDecoder();
        let buffer = '', caseCount = 0;
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    switch (data.type) {
                        case 'start':
                            statusEl.innerHTML = `<span class="spinner"></span> ${escHtml(data.message)}`;
                            break;
                        case 'progress':
                        case 'retry':
                            statusEl.innerHTML = `<span class="spinner"></span> ${escHtml(data.message)}`;
                            break;
                        case 'chunk_progress':
                            statusEl.innerHTML = `<span class="spinner"></span> 🤖 AI 正在生成中... (已接收 ${data.length} 字符)`;
                            break;
                        case 'testcase':
                            caseCount++;
                            statusEl.innerHTML = `<span class="spinner"></span> 📝 已生成第 <strong>${data.index}</strong> / ${data.total} 条用例: ${escHtml(data.data?.title || '')}`;
                            break;
                        case 'parse_error':
                            statusEl.innerHTML = `<span class="spinner"></span> ⚠️ 解析失败，正在重试 (尝试 ${data.attempt})...`;
                            break;
                        case 'complete':
                            statusEl.className = 'status-area show success';
                            statusEl.innerHTML = `✅ ${escHtml(data.message)}`;
                            setGenerating(false);  // 解锁界面
                            toast(`已生成 ${data.total} 条测试用例`, 'success');
                            clearDraft();
                            setTimeout(() => { closeGenerateModal(); document.querySelector('.nav-item[data-view="testcases"]').click(); }, 1500);
                            break;
                        case 'error':
                        case 'fatal':
                            throw new Error(data.message);
                    }
                } catch (pe) { if (pe.message && !pe.message.includes('JSON')) throw pe; }
            }
        }
    } catch (e) {
        if (e.name === 'AbortError') { setGenerating(false); return; }
        try {
            const data = await apiJson('/api/testcases/generate', {
                method: 'POST', body: JSON.stringify(requestBody)
            });
            statusEl.className = 'status-area show success';
            statusEl.innerHTML = `✅ 成功生成 <strong>${data.total_generated}</strong> 条测试用例！`;
            setGenerating(false);
            toast(`已生成 ${data.total_generated} 条测试用例`, 'success');
            clearDraft();
            setTimeout(() => { closeGenerateModal(); document.querySelector('.nav-item[data-view="testcases"]').click(); }, 1500);
        } catch (fe) {
            statusEl.className = 'status-area show error';
            statusEl.innerHTML = `❌ 生成失败: ${escHtml(fe.message)}`;
            setGenerating(false);
            btn.disabled = false;
        }
    }
});

// ========== 视图模式 ==========
function setViewMode(mode) {
    viewMode = mode;
    document.getElementById('tableViewBtn').classList.toggle('active', mode === 'table');
    document.getElementById('cardViewBtn').classList.toggle('active', mode === 'card');
    loadTestcases();
}

// ========== 测试用例列表 ==========
async function loadTestcases() {
    showTestcaseSkeleton();
    const p = new URLSearchParams({ page: tcPage, page_size: 50 });
    const docId = document.getElementById('filterDoc').value;
    const priority = document.getElementById('filterPriority').value;
    const caseType = document.getElementById('filterType').value;
    const search = document.getElementById('tcSearch')?.value || '';
    const sortBy = document.getElementById('sortBy')?.value || 'priority';
    if (docId) p.set('document_id', docId);
    if (priority) p.set('priority', priority);
    if (caseType) p.set('case_type', caseType);
    if (search) p.set('search', search);
    p.set('sort_by', sortBy);
    p.set('sort_order', sortOrder);
    renderFilterChips();
    try {
        const data = await apiJson(`/api/testcases?${p}`);
        if (viewMode === 'card') renderTestcaseCards(data.testcases);
        else renderTestcases(data.testcases);
        renderTcPagination(data);
        if (data.stats) {
            document.getElementById('statsCards').style.display = '';
            document.getElementById('statTotal').textContent = data.total;
            document.getElementById('statP0').textContent = data.stats.p0_count || 0;
            document.getElementById('statP1').textContent = data.stats.p1_count || 0;
            document.getElementById('statP2').textContent = data.stats.p2_count || 0;
            document.getElementById('statP3').textContent = data.stats.p3_count || 0;
            document.getElementById('tcStatsText').textContent = `共 ${data.total} 条用例`;
        }
    } catch (e) {
        document.getElementById('testcasesContainer').innerHTML = getEmptyStateHtml('no-testcases');
    }
}

function renderTestcases(cases) {
    const c = document.getElementById('testcasesContainer');
    if (!cases.length) { c.innerHTML = getEmptyStateHtml('no-testcases'); return; }
    const kw = document.getElementById('tcSearch')?.value || '';
    let h = `<table class="tc-table"><thead><tr>
        <th class="checkbox-col"><input type="checkbox" id="selectAllTc" onchange="toggleSelectAllTc(this)"></th>
        <th>编号</th><th>模块</th><th>标题</th><th>优先级</th><th>类型</th>
        <th>前置条件</th><th>测试步骤</th><th>预期结果</th><th>操作</th>
    </tr></thead><tbody>`;
    cases.forEach(tc => {
        h += `<tr data-id="${tc.id}">
            <td class="checkbox-col"><input type="checkbox" class="tc-checkbox" value="${tc.id}" onchange="updateTcSelection()"></td>
            <td style="white-space:nowrap">${highlightText(tc.case_id, kw)}</td>
            <td class="editable-cell" onclick="startInlineEdit(this,${tc.id},'module')">${highlightText(tc.module, kw)}</td>
            <td class="editable-cell" style="font-weight:500;max-width:200px" onclick="startInlineEdit(this,${tc.id},'title')">${highlightText(tc.title, kw)}</td>
            <td class="editable-cell" onclick="startInlineEdit(this,${tc.id},'priority')"><span class="priority-badge ${tc.priority}">${tc.priority}</span></td>
            <td class="editable-cell" onclick="startInlineEdit(this,${tc.id},'case_type')"><span class="type-badge">${escHtml(tc.case_type)}</span></td>
            <td class="tc-steps">${highlightText(tc.precondition, kw)}</td>
            <td class="tc-steps editable-cell" onclick="startInlineEdit(this,${tc.id},'steps')">${highlightText(tc.steps, kw)}</td>
            <td class="tc-steps editable-cell" onclick="startInlineEdit(this,${tc.id},'expected_result')">${highlightText(tc.expected_result, kw)}</td>
            <td><div class="tc-actions">
                <button class="btn btn-outline btn-sm" onclick="openEditModal(${tc.id})" title="编辑">✏️</button>
                <button class="btn btn-outline btn-sm" onclick="copyTestcase(${tc.id})" title="复制">📋</button>
                <button class="btn btn-outline btn-sm" onclick="openHistoryPanel(${tc.id})" title="历史版本">🕘</button>
                <button class="btn btn-outline btn-sm" onclick="regenerateTestcase(${tc.id})" title="重新生成">🔄</button>
                <button class="btn btn-danger btn-sm" onclick="deleteTestcase(${tc.id})">🗑</button>
            </div></td></tr>`;
    });
    h += '</tbody></table>';
    c.innerHTML = h;
}

function renderTestcaseCards(cases) {
    const c = document.getElementById('testcasesContainer');
    if (!cases.length) { c.innerHTML = getEmptyStateHtml('no-testcases'); return; }
    let h = '<div class="tc-cards-grid">';
    cases.forEach(tc => {
        h += `<div class="tc-card-item">
            <div class="tc-card-header"><span style="font-size:12px;color:var(--text-muted)">${escHtml(tc.case_id)}</span><span class="priority-badge ${tc.priority}">${tc.priority}</span></div>
            <div class="tc-card-title">${escHtml(tc.title)}</div>
            <div class="tc-card-meta"><span class="type-badge">${escHtml(tc.case_type)}</span>${tc.module ? `<span style="font-size:12px;color:var(--text-muted)">📂 ${escHtml(tc.module)}</span>` : ''}</div>
            ${tc.precondition ? `<div class="tc-card-section"><strong>前置条件</strong>${escHtml(tc.precondition)}</div>` : ''}
            <div class="tc-card-section"><strong>测试步骤</strong>${escHtml(tc.steps)}</div>
            <div class="tc-card-section"><strong>预期结果</strong>${escHtml(tc.expected_result)}</div>
            <div class="tc-card-actions">
                <button class="btn btn-outline btn-sm" onclick="openEditModal(${tc.id})">✏️</button>
                <button class="btn btn-outline btn-sm" onclick="copyTestcase(${tc.id})">📋</button>
                <button class="btn btn-outline btn-sm" onclick="openHistoryPanel(${tc.id})" title="历史版本">🕘</button>
                <button class="btn btn-outline btn-sm" onclick="regenerateTestcase(${tc.id})">🔄</button>
                <button class="btn btn-danger btn-sm" onclick="deleteTestcase(${tc.id})">🗑</button>
            </div>
        </div>`;
    });
    h += '</div>';
    c.innerHTML = h;
}

// ========== 全选 & 批量操作 ==========
function toggleSelectAllTc(cb) { document.querySelectorAll('.tc-checkbox').forEach(c => c.checked = cb.checked); updateTcSelection(); }
function updateTcSelection() {
    const n = document.querySelectorAll('.tc-checkbox:checked').length;
    document.getElementById('batchDeleteTcBtn').style.display = n > 0 ? '' : 'none';
    document.getElementById('batchDeleteTcBtn').textContent = `🗑 批量删除 (${n})`;
    document.getElementById('batchPriorityBtn').style.display = n > 0 ? '' : 'none';
    document.getElementById('batchPriorityBtn').textContent = `🏷 改优先级 (${n})`;
    document.getElementById('batchCopyBtn').style.display = n > 0 ? '' : 'none';
    document.getElementById('batchCopyBtn').textContent = `📋 批量复制 (${n})`;
}

async function batchDeleteTestcases() {
    const ids = Array.from(document.querySelectorAll('.tc-checkbox:checked')).map(cb => parseInt(cb.value));
    if (!ids.length || !confirm(`确定要删除选中的 ${ids.length} 条测试用例吗？`)) return;
    try {
        const data = await apiJson('/api/testcases/batch-delete', { method: 'POST', body: JSON.stringify({ ids }) });
        toast(`成功删除 ${data.deleted} 条测试用例（已移入回收站）`, 'success');
        loadTestcases(); loadQuickStats();
    } catch (e) { toast(`批量删除失败: ${e.message}`, 'error'); }
}

// ========== 批量复制 ==========
async function batchCopyTestcases() {
    const ids = Array.from(document.querySelectorAll('.tc-checkbox:checked')).map(cb => parseInt(cb.value));
    if (!ids.length || !confirm(`确定要复制选中的 ${ids.length} 条测试用例吗？`)) return;
    try {
        const data = await apiJson('/api/testcases/batch-copy', { method: 'POST', body: JSON.stringify({ ids }) });
        toast(`成功复制 ${data.copied} 条测试用例`, 'success');
        loadTestcases(); loadQuickStats();
    } catch (e) { toast(`批量复制失败: ${e.message}`, 'error'); }
}

// ========== 复制测试用例 ==========
async function copyTestcase(tcId) {
    try {
        const data = await apiJson(`/api/testcases/${tcId}/copy`, { method: 'POST' });
        toast('复制成功！', 'success');
        loadTestcases(); loadQuickStats();
    } catch (e) { toast(`复制失败: ${e.message}`, 'error'); }
}

async function regenerateTestcase(tcId) {
    if (!confirm('确定要重新生成这条测试用例吗？')) return;
    try { toast('正在重新生成...', 'info'); await apiJson(`/api/testcases/${tcId}/regenerate`, { method: 'POST' }); toast('重新生成成功！', 'success'); loadTestcases(); }
    catch (e) { toast(`重新生成失败: ${e.message}`, 'error'); }
}

// ========== 批量改优先级 ==========
function batchChangePriority() {
    document.getElementById('priorityCount').textContent = document.querySelectorAll('.tc-checkbox:checked').length;
    selectedPriority = null;
    document.querySelectorAll('.radio-card').forEach(c => c.classList.remove('selected'));
    document.getElementById('priorityModal').classList.add('show');
}
function selectPriority(p) {
    selectedPriority = p;
    document.querySelectorAll('.radio-card').forEach(c => c.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
}
function closePriorityModal() { document.getElementById('priorityModal').classList.remove('show'); }
async function confirmBatchPriority() {
    if (!selectedPriority) { toast('请选择目标优先级', 'error'); return; }
    const ids = Array.from(document.querySelectorAll('.tc-checkbox:checked')).map(cb => parseInt(cb.value));
    let ok = 0;
    for (const id of ids) { try { await api(`/api/testcases/${id}`, { method: 'PUT', body: JSON.stringify({ priority: selectedPriority }) }); ok++; } catch(e){} }
    toast(`已将 ${ok} 条用例优先级修改为 ${selectedPriority}`, 'success');
    closePriorityModal(); loadTestcases();
}

// ========== 导入 ==========
let _importFileContent = null;

function openImportModal() {
    const sel = document.getElementById('importDocId');
    sel.innerHTML = '<option value="">不关联文档</option>';
    allDocuments.forEach(d => { sel.innerHTML += `<option value="${d.id}">${escHtml(d.filename)}</option>`; });
    document.getElementById('importJsonText').value = '';
    _importFileContent = null;
    document.getElementById('importStatus').innerHTML = '';
    document.getElementById('importStatus').className = 'status-area';
    document.getElementById('importModal').classList.add('show');
    // 初始化拖拽上传
    setTimeout(initImportDropZone, 100);
}
function closeImportModal() { document.getElementById('importModal').classList.remove('show'); }

function switchImportMode() {
    const mode = document.querySelector('input[name="importMode"]:checked').value;
    document.getElementById('importFileArea').style.display = mode === 'file' ? '' : 'none';
    document.getElementById('importPasteArea').style.display = mode === 'paste' ? '' : 'none';
}

function initImportDropZone() {
    const dz = document.getElementById('importDropZone');
    if (!dz || dz._init) return;
    dz._init = true;
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', e => {
        e.preventDefault(); dz.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) handleImportFile(e.dataTransfer.files[0]);
    });
    dz.addEventListener('click', e => { if (e.target.tagName !== 'A') document.getElementById('importFileInput').click(); });
    document.getElementById('importFileInput').addEventListener('change', e => {
        if (e.target.files.length > 0) handleImportFile(e.target.files[0]);
    });
}

function handleImportFile(file) {
    if (!file.name.endsWith('.json')) { toast('请选择 JSON 文件', 'error'); return; }
    const reader = new FileReader();
    reader.onload = e => {
        _importFileContent = e.target.result;
        const dz = document.getElementById('importDropZone');
        dz.innerHTML = `<p style="font-size:14px">✅ 已选择: <strong>${escHtml(file.name)}</strong> (${formatFileSize(file.size)})</p>`;
        toast('文件已读取，点击导入按钮开始', 'info');
    };
    reader.readAsText(file);
}

async function doImport() {
    const mode = document.querySelector('input[name="importMode"]:checked').value;
    const docId = document.getElementById('importDocId').value;
    const statusEl = document.getElementById('importStatus');

    let text = '';
    if (mode === 'file') {
        text = _importFileContent;
        if (!text) { toast('请先选择文件', 'error'); return; }
    } else {
        text = document.getElementById('importJsonText').value.trim();
    }
    if (!text) { toast('请输入 JSON 数据', 'error'); return; }

    try {
        let parsed = JSON.parse(text);
        if (parsed.testcases && Array.isArray(parsed.testcases)) parsed = parsed.testcases;
        if (!Array.isArray(parsed)) parsed = [parsed];
        const valid = parsed.filter(tc => tc.title && (tc.steps || tc.expected_result));
        if (!valid.length) { toast('没有有效的用例（需要 title 和 steps 字段）', 'error'); return; }

        statusEl.className = 'status-area show loading';
        statusEl.innerHTML = `<span class="spinner"></span> 正在导入 ${valid.length} 条用例...`;

        const data = await apiJson('/api/testcases/import', {
            method: 'POST',
            body: JSON.stringify({ testcases: valid, document_id: docId ? parseInt(docId) : null })
        });
        statusEl.className = 'status-area show success';
        statusEl.innerHTML = `✅ ${data.message}`;
        toast(`成功导入 ${data.imported} 条用例`, 'success');
        setTimeout(() => { closeImportModal(); loadTestcases(); loadQuickStats(); }, 1500);
    } catch (e) {
        statusEl.className = 'status-area show error';
        statusEl.innerHTML = `❌ 导入失败: ${escHtml(e.message)}`;
    }
}

// ========== 清空 ==========
async function clearAllTestcases() {
    const docId = document.getElementById('filterDoc').value;
    const priority = document.getElementById('filterPriority').value;
    const caseType = document.getElementById('filterType').value;
    let desc = '全部';
    if (docId) desc = `文档ID=${docId}的`;
    if (priority) desc += ` ${priority}`;
    if (caseType) desc += ` ${caseType}`;
    if (!confirm(`⚠️ 确定要删除${desc}测试用例吗？\n\n删除后将移入回收站！`)) return;
    try {
        const p = new URLSearchParams();
        if (docId) p.set('document_id', docId);
        if (priority) p.set('priority', priority);
        if (caseType) p.set('case_type', caseType);
        const data = await apiJson(`/api/testcases?${p}`, { method: 'DELETE' });
        toast(`成功清空 ${data.deleted} 条（已移入回收站）`, 'success');
        loadTestcases(); loadQuickStats();
    } catch (e) { toast(`清空失败: ${e.message}`, 'error'); }
}

// ========== 回收站 ==========
async function loadTrash() {
    try {
        const data = await apiJson(`/api/trash?${new URLSearchParams({ page: trashPage, page_size: 50 })}`);
        renderTrash(data.testcases);
        renderTrashPagination(data);
    } catch (e) {
        document.getElementById('trashContainer').innerHTML = getEmptyStateHtml('empty-trash');
    }
}

function renderTrash(cases) {
    const c = document.getElementById('trashContainer');
    if (!cases.length) { c.innerHTML = getEmptyStateHtml('empty-trash'); return; }
    let h = `<table class="tc-table"><thead><tr>
        <th>编号</th><th>模块</th><th>标题</th><th>优先级</th><th>类型</th><th>删除时间</th><th>操作</th>
    </tr></thead><tbody>`;
    cases.forEach(tc => {
        h += `<tr>
            <td style="white-space:nowrap">${escHtml(tc.case_id)}</td>
            <td>${escHtml(tc.module)}</td>
            <td style="font-weight:500;max-width:200px">${escHtml(tc.title)}</td>
            <td><span class="priority-badge ${tc.priority}">${tc.priority}</span></td>
            <td><span class="type-badge">${escHtml(tc.case_type)}</span></td>
            <td style="font-size:12px;color:var(--text-muted)">${tc.deleted_at || ''}</td>
            <td><div class="tc-actions">
                <button class="btn btn-outline btn-sm" onclick="restoreFromTrash(${tc.id})" title="恢复">♻️</button>
                <button class="btn btn-danger btn-sm" onclick="permanentDelete(${tc.id})" title="永久删除">🗑</button>
            </div></td></tr>`;
    });
    h += '</tbody></table>';
    c.innerHTML = h;
}

function renderTrashPagination(data) {
    const c = document.getElementById('trashPagination');
    if (!data || data.total_pages <= 1) { c.innerHTML = ''; return; }
    let h = `<button class="page-btn" onclick="goTrashPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`;
    for (let i = 1; i <= data.total_pages; i++) h += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="goTrashPage(${i})">${i}</button>`;
    h += `<button class="page-btn" onclick="goTrashPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''}>›</button>`;
    h += `<span class="page-info">共 ${data.total} 条</span>`;
    c.innerHTML = h;
}
function goTrashPage(p) { trashPage = p; loadTrash(); }

async function restoreFromTrash(id) {
    try { await api(`/api/trash/${id}/restore`, { method: 'POST' }); toast('恢复成功！', 'success'); loadTrash(); loadTestcases(); loadQuickStats(); }
    catch (e) { toast(`恢复失败: ${e.message}`, 'error'); }
}

async function permanentDelete(id) {
    if (!confirm('确定要永久删除吗？此操作不可撤销！')) return;
    try { await api(`/api/trash/${id}`, { method: 'DELETE' }); toast('永久删除成功', 'success'); loadTrash(); }
    catch (e) { toast(`删除失败: ${e.message}`, 'error'); }
}

async function emptyTrash() {
    if (!confirm('确定要清空回收站吗？所有用例将被永久删除！')) return;
    if (!confirm('再次确认：真的要清空吗？')) return;
    try {
        const data = await apiJson('/api/trash', { method: 'DELETE' });
        toast(`已清空回收站（${data.deleted} 条）`, 'success');
        loadTrash();
    } catch (e) { toast(`清空失败: ${e.message}`, 'error'); }
}

async function restoreAllTrash() {
    if (!confirm('确定要恢复回收站中的所有用例吗？')) return;
    try {
        const trashData = await apiJson(`/api/trash?page_size=9999`);
        const ids = trashData.testcases.map(t => t.id);
        if (!ids.length) { toast('回收站为空', 'info'); return; }
        const data = await apiJson('/api/trash/batch-restore', {
            method: 'POST', body: JSON.stringify({ ids })
        });
        toast(`成功恢复 ${data.restored} 条用例`, 'success');
        loadTrash(); loadTestcases(); loadQuickStats();
    } catch (e) { toast(`恢复失败: ${e.message}`, 'error'); }
}

// ========== Prompt 模板管理 ==========

async function loadTemplateList() {
    try {
        const data = await apiJson('/api/prompt-templates');
        const templates = data.templates || [];
        const c = document.getElementById('templateList');
        if (!templates.length) {
            c.innerHTML = getEmptyStateHtml('no-templates');
            return;
        }
        c.innerHTML = templates.map(t => {
            const preview = (t.content || '').substring(0, 80).replace(/\n/g, ' ');
            return `<div class="template-item">
                <div class="template-item-info">
                    <div class="template-item-name">
                        ${escHtml(t.name)}
                        ${t.is_default ? '<span class="default-badge">默认</span>' : ''}
                    </div>
                    <div class="template-item-preview">${escHtml(preview)}${(t.content||'').length > 80 ? '...' : ''}</div>
                </div>
                <div class="template-item-actions">
                    <button class="btn btn-outline btn-sm" onclick="editTemplate(${t.id})">✏️</button>
                    <button class="btn btn-outline btn-sm" onclick="deleteTemplate(${t.id},'${escAttr(t.name)}')">🗑</button>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        document.getElementById('templateList').innerHTML = '<div class="loading-text">加载失败</div>';
    }
}

function openCreateTemplateModal() {
    document.getElementById('templateModalTitle').textContent = '📝 新建 Prompt 模板';
    document.getElementById('tplEditId').value = '';
    document.getElementById('tplName').value = '';
    document.getElementById('tplContent').value = '';
    document.getElementById('tplDefault').value = '0';
    document.getElementById('templateModal').classList.add('show');
}

function closeTemplateModal() {
    document.getElementById('templateModal').classList.remove('show');
}

async function editTemplate(id) {
    try {
        const data = await apiJson('/api/prompt-templates');
        const tpl = (data.templates || []).find(t => t.id === id);
        if (!tpl) { toast('模板不存在', 'error'); return; }
        document.getElementById('templateModalTitle').textContent = '✏️ 编辑 Prompt 模板';
        document.getElementById('tplEditId').value = tpl.id;
        document.getElementById('tplName').value = tpl.name;
        document.getElementById('tplContent').value = tpl.content || '';
        document.getElementById('tplDefault').value = tpl.is_default ? '1' : '0';
        document.getElementById('templateModal').classList.add('show');
    } catch (e) { toast(`加载失败: ${e.message}`, 'error'); }
}

async function saveTemplate() {
    const id = document.getElementById('tplEditId').value;
    const name = document.getElementById('tplName').value.trim();
    const content = document.getElementById('tplContent').value.trim();
    const isDefault = document.getElementById('tplDefault').value === '1';

    if (!name) { toast('请输入模板名称', 'error'); return; }
    if (!content) { toast('请输入 Prompt 内容', 'error'); return; }

    try {
        if (id) {
            await api(`/api/prompt-templates/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ name, content, is_default: isDefault })
            });
            toast('模板更新成功！', 'success');
        } else {
            await api('/api/prompt-templates', {
                method: 'POST',
                body: JSON.stringify({ name, content, is_default: isDefault })
            });
            toast('模板创建成功！', 'success');
        }
        closeTemplateModal();
        loadTemplateList();
        loadPromptTemplates();
    } catch (e) { toast(`保存失败: ${e.message}`, 'error'); }
}

async function deleteTemplate(id, name) {
    if (!confirm(`确定要删除模板「${name}」吗？`)) return;
    try {
        await api(`/api/prompt-templates/${id}`, { method: 'DELETE' });
        toast('模板已删除', 'success');
        loadTemplateList();
        loadPromptTemplates();
    } catch (e) { toast(`删除失败: ${e.message}`, 'error'); }
}

// ========== 分页 ==========
function renderTcPagination(data) {
    const c = document.getElementById('tcPagination');
    if (!data || data.total_pages <= 1) { c.innerHTML = ''; return; }
    let h = `<button class="page-btn" onclick="goTcPage(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>‹</button>`;
    const s = Math.max(1, data.page - 3), e = Math.min(data.total_pages, data.page + 3);
    if (s > 1) h += `<button class="page-btn" onclick="goTcPage(1)">1</button>`;
    if (s > 2) h += `<span class="page-info">...</span>`;
    for (let i = s; i <= e; i++) h += `<button class="page-btn ${i === data.page ? 'active' : ''}" onclick="goTcPage(${i})">${i}</button>`;
    if (e < data.total_pages - 1) h += `<span class="page-info">...</span>`;
    if (e < data.total_pages) h += `<button class="page-btn" onclick="goTcPage(${data.total_pages})">${data.total_pages}</button>`;
    h += `<button class="page-btn" onclick="goTcPage(${data.page + 1})" ${data.page >= data.total_pages ? 'disabled' : ''}>›</button>`;
    h += `<span class="page-info">共 ${data.total} 条</span>`;
    c.innerHTML = h;
}
function goTcPage(p) { tcPage = p; loadTestcases(); }
function debounceTcSearch() { clearTimeout(tcSearchTimer); tcSearchTimer = setTimeout(() => { tcPage = 1; loadTestcases(); }, 400); }
document.getElementById('filterDoc').addEventListener('change', () => { tcPage = 1; loadTestcases(); });
document.getElementById('filterPriority').addEventListener('change', () => { tcPage = 1; loadTestcases(); });
document.getElementById('filterType').addEventListener('change', () => { tcPage = 1; loadTestcases(); });

// ========== 导出 ==========
function toggleExportMenu() { document.getElementById('exportMenu').classList.toggle('show'); }
document.addEventListener('click', e => { if (!e.target.closest('.export-dropdown')) document.getElementById('exportMenu').classList.remove('show'); });
function doExport(fmt) {
    document.getElementById('exportMenu').classList.remove('show');
    const p = new URLSearchParams();
    const docId = document.getElementById('filterDoc').value;
    const priority = document.getElementById('filterPriority').value;
    const caseType = document.getElementById('filterType').value;
    const search = document.getElementById('tcSearch')?.value || '';
    if (docId) p.set('document_id', docId);
    if (priority) p.set('priority', priority);
    if (caseType) p.set('case_type', caseType);
    if (search) p.set('search', search);
    toast(`正在导出 ${fmt.toUpperCase()}...`, 'info');
    const a = document.createElement('a');
    a.href = `/api/export/${fmt}?${p}`;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => toast('导出完成！', 'success'), 1500);
}

// ========== 编辑 ==========
async function openEditModal(tcId) {
    try {
        const tc = await apiJson(`/api/testcases/${tcId}`);
        document.getElementById('editId').value = tc.id;
        document.getElementById('editCaseId').value = tc.case_id || '';
        document.getElementById('editModule').value = tc.module || '';
        document.getElementById('editTitle').value = tc.title || '';
        document.getElementById('editPriority').value = tc.priority || 'P2';
        document.getElementById('editType').value = tc.case_type || '功能测试';
        document.getElementById('editPrecondition').value = tc.precondition || '';
        document.getElementById('editSteps').value = tc.steps || '';
        document.getElementById('editExpected').value = tc.expected_result || '';
        document.getElementById('editModal').classList.add('show');
    } catch (e) { toast(`加载失败: ${e.message}`, 'error'); }
}
function closeEditModal() { document.getElementById('editModal').classList.remove('show'); }
document.getElementById('saveEditBtn').addEventListener('click', async () => {
    const id = document.getElementById('editId').value;
    try {
        await api(`/api/testcases/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                module: document.getElementById('editModule').value,
                title: document.getElementById('editTitle').value,
                priority: document.getElementById('editPriority').value,
                case_type: document.getElementById('editType').value,
                precondition: document.getElementById('editPrecondition').value,
                steps: document.getElementById('editSteps').value,
                expected_result: document.getElementById('editExpected').value,
            })
        });
        toast('保存成功！', 'success');
        closeEditModal(); loadTestcases();
    } catch (e) { toast(`保存失败: ${e.message}`, 'error'); }
});

// ========== 删除（移入回收站） ==========
async function deleteTestcase(tcId) {
    if (!confirm('确定要删除这条测试用例吗？\n\n删除后将移入回收站，可随时恢复。')) return;
    try {
        await api(`/api/testcases/${tcId}`, { method: 'DELETE' });
        toast('已移入回收站', 'success');
        loadTestcases(); loadQuickStats();
    } catch (e) { toast(`删除失败: ${e.message}`, 'error'); }
}

// ========== 数据概览 ==========
async function loadStats() {
    showStatsSkeleton();
    try {
        const data = await apiJson('/api/stats');
        const c = document.getElementById('statsContent');
        const pColors = { P0: '#EF4444', P1: '#F97316', P2: '#EAB308', P3: '#22C55E' };
        const maxP = Math.max(...Object.values(data.testcases.by_priority), 1);
        const maxT = Math.max(...Object.values(data.testcases.by_type), 1);

        // Priority distribution with bar chart
        let h = `<div class="dashboard-card glass"><h4>📊 优先级分布</h4>`;
        h += `<div class="bar-chart">`;
        for (const [p, n] of Object.entries(data.testcases.by_priority)) {
            const pct = Math.round((n / maxP) * 100);
            h += `<div class="bar-row"><span class="bar-label"><span class="priority-badge ${p}">${p}</span></span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${pColors[p]}">${n}</div></div></div>`;
        }
        h += `</div></div>`;

        // Type distribution with bar chart
        const tColors = ['#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981'];
        h += `<div class="dashboard-card glass"><h4>🏷️ 用例类型分布</h4>`;
        h += `<div class="bar-chart">`;
        let ti = 0;
        for (const [t, n] of Object.entries(data.testcases.by_type)) {
            const pct = Math.round((n / maxT) * 100);
            h += `<div class="bar-row"><span class="bar-label">${escHtml(t)}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${tColors[ti % tColors.length]}">${n}</div></div></div>`;
            ti++;
        }
        h += `</div></div>`;

        // Module distribution
        h += `<div class="dashboard-card glass"><h4>📂 模块分布 (Top 15)</h4><ul class="dashboard-list">`;
        for (const [m, n] of Object.entries(data.testcases.by_module).slice(0, 15)) h += `<li><span>${escHtml(m)}</span><span class="count-badge">${n}</span></li>`;
        h += `</ul></div>`;

        // Overview stat cards with trend indicators
        h += `<div class="dashboard-card glass"><h4>📈 总览</h4><div class="stat-mini-cards">`;
        h += `<div class="stat-mini"><div class="stat-mini-icon">📄</div><div class="stat-mini-value">${data.documents.total}</div><div class="stat-mini-label">文档总数</div><div class="stat-trend trend-up">↑</div></div>`;
        h += `<div class="stat-mini"><div class="stat-mini-icon">📋</div><div class="stat-mini-value">${data.testcases.total}</div><div class="stat-mini-label">用例总数</div><div class="stat-trend trend-up">↑</div></div>`;
        h += `<div class="stat-mini"><div class="stat-mini-icon">🏷️</div><div class="stat-mini-value">${Object.keys(data.testcases.by_type).length}</div><div class="stat-mini-label">类型数</div></div>`;
        h += `<div class="stat-mini"><div class="stat-mini-icon">📂</div><div class="stat-mini-value">${Object.keys(data.testcases.by_module).length}</div><div class="stat-mini-label">模块数</div></div>`;
        h += `</div></div>`;
        c.innerHTML = h;
    } catch (e) { document.getElementById('statsContent').innerHTML = '<div class="empty-state"><p>加载失败</p></div>'; }
}

// ========== 操作日志 ==========
const ACTION_ICONS = {
    upload: '📤', generate: '🤖', delete: '🗑', copy: '📋',
    import: '📥', restore: '♻️', config: '⚙️'
};
const ACTION_LABELS = {
    upload: '上传', generate: '生成', delete: '删除', copy: '复制',
    import: '导入', restore: '恢复', config: '配置'
};

async function loadLogs() {
    const action = document.getElementById('logActionFilter')?.value || '';
    const p = new URLSearchParams({ page: logPage, page_size: 50 });
    if (action) p.set('action', action);
    try {
        const data = await apiJson(`/api/logs?${p}`);
        renderLogs(data.logs);
        renderLogsPagination(data);
    } catch (e) {
        document.getElementById('logsContainer').innerHTML = getEmptyStateHtml('no-logs');
    }
}

function renderLogs(logs) {
    const c = document.getElementById('logsContainer');
    if (!logs.length) { c.innerHTML = getEmptyStateHtml('no-logs'); return; }
    let h = '<table class="tc-table"><thead><tr><th>ID</th><th>操作</th><th>目标类型</th><th>目标ID</th><th>详情</th><th>时间</th></tr></thead><tbody>';
    logs.forEach(log => {
        const icon = ACTION_ICONS[log.action] || '📝';
        const label = ACTION_LABELS[log.action] || log.action;
        h += '<tr><td>' + log.id + '</td><td><span class="type-badge">' + icon + ' ' + label + '</span></td><td>' + escHtml(log.target_type) + '</td><td>' + (log.target_id || '-') + '</td><td class="tc-steps">' + escHtml(log.detail) + '</td><td style="font-size:12px;color:var(--text-muted)">' + (log.created_at || '') + '</td></tr>';
    });
    h += '</tbody></table>';
    c.innerHTML = h;
}

function renderLogsPagination(data) {
    const c = document.getElementById('logsPagination');
    if (!data || data.total_pages <= 1) { c.innerHTML = ''; return; }
    let h = '<button class="page-btn" onclick="goLogPage(' + (data.page - 1) + ')" ' + (data.page <= 1 ? 'disabled' : '') + '>‹</button>';
    const s = Math.max(1, data.page - 2), e = Math.min(data.total_pages, data.page + 2);
    for (let i = s; i <= e; i++) h += '<button class="page-btn ' + (i === data.page ? 'active' : '') + '" onclick="goLogPage(' + i + ')">' + i + '</button>';
    h += '<button class="page-btn" onclick="goLogPage(' + (data.page + 1) + ')" ' + (data.page >= data.total_pages ? 'disabled' : '') + '>›</button>';
    h += '<span class="page-info">共 ' + data.total + ' 条</span>';
    c.innerHTML = h;
}
function goLogPage(p) { logPage = p; loadLogs(); }

// ========== AI 配置 ==========
async function loadConfig() {
    try {
        const data = await apiJson('/api/config');
        document.getElementById('cfgBaseUrl').value = data.ai_base_url || '';
        document.getElementById('cfgModel').value = data.ai_model || 'gpt-4o';
        // 保存完整的 API Key 到 data 属性，方便查看
        const apiInput = document.getElementById('cfgApiKey');
        apiInput.value = '';
        apiInput.dataset.fullKey = data.ai_api_key || '';
        apiKeyVisible = false;
        apiInput.type = 'password';

        document.getElementById('apiKeyStatus').innerHTML = data.ai_api_key_set
            ? `<span style="color:var(--success)">✅ 已配置</span> <code style="font-size:11px;background:var(--bg-tertiary);padding:2px 6px;border-radius:4px">${escHtml(data.ai_api_key_masked)}</code>`
            : '<span style="color:var(--warning)">⚠️ 未配置</span>';
        if (data.ai_temperature !== undefined) document.getElementById('cfgTemp').value = data.ai_temperature;
        if (data.ai_max_tokens !== undefined) document.getElementById('cfgMaxTokens').value = data.ai_max_tokens;
        document.getElementById('tempVal').textContent = document.getElementById('cfgTemp').value;
    } catch (e) { toast(`加载配置失败: ${e.message}`, 'error'); }
}

function toggleApiKeyVisibility() {
    const input = document.getElementById('cfgApiKey');
    apiKeyVisible = !apiKeyVisible;
    if (apiKeyVisible) {
        // 如果输入框为空，显示已保存的完整 key
        if (!input.value && input.dataset.fullKey) {
            input.value = input.dataset.fullKey;
        }
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

document.getElementById('saveConfigBtn').addEventListener('click', async () => {
    const baseUrl = document.getElementById('cfgBaseUrl').value.trim();
    const apiKey = document.getElementById('cfgApiKey').value.trim();
    const model = document.getElementById('cfgModel').value.trim();
    if (!baseUrl) { toast('请输入 API Base URL', 'error'); return; }
    if (!apiKey) { toast('请输入 API Key', 'error'); return; }
    if (!model) { toast('请输入模型名称', 'error'); return; }
    try {
        await api('/api/config', {
            method: 'PUT',
            body: JSON.stringify({
                ai_base_url: baseUrl, ai_api_key: apiKey, ai_model: model,
                ai_temperature: parseFloat(document.getElementById('cfgTemp').value),
                ai_max_tokens: parseInt(document.getElementById('cfgMaxTokens').value)
            })
        });
        toast('配置保存成功！', 'success');
        loadConfig();
    } catch (e) { toast(`保存失败: ${e.message}`, 'error'); }
});

async function testAIConnection() {
    toast('正在测试 AI 连接...', 'info');
    try {
        const config = await apiJson('/api/config');
        if (!config.ai_api_key_set) { toast('请先配置 API Key', 'warning'); return; }
        toast(`连接配置正常！模型: ${config.ai_model}`, 'success');
    } catch (e) { toast(`连接测试失败: ${e.message}`, 'error'); }
}

// ========== 快捷键 (v3.3) ==========
function closeHelpModal() { document.getElementById('helpModal').classList.remove('show'); }
document.addEventListener('keydown', e => {
    // Command palette takes priority
    if (_cmdPaletteOpen) return; // handled by cmdPaletteInput keydown

    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
        closeHistoryPanel();
    }
    const tag = document.activeElement.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
    if (!isInput) {
        if (e.key === '?') { e.preventDefault(); document.getElementById('helpModal').classList.add('show'); }
        if (e.key >= '1' && e.key <= '9') { e.preventDefault(); const v = ['upload', 'testcases', 'suites', 'executor', 'dashboard', 'reports', 'stats', 'trash', 'settings']; document.querySelector(`.nav-item[data-view="${v[e.key - 1]}"]`)?.click(); }
    }
    if (e.ctrlKey && e.key === 'k') { e.preventDefault(); openCommandPalette(); }
    if (e.ctrlKey && e.key === 'u') { e.preventDefault(); document.querySelector('.nav-item[data-view="upload"]')?.click(); }
    if (e.ctrlKey && e.key === 'g') { e.preventDefault(); if (allDocuments.length) openGenerateModal(allDocuments[0].id, allDocuments[0].filename); else showToast('请先上传文档','warning'); }
    if (e.ctrlKey && e.key === 'e') { e.preventDefault(); doExport('excel'); }
    if (e.ctrlKey && e.shiftKey && e.key === 'F') { e.preventDefault(); document.querySelector('.nav-item[data-view="testcases"]')?.click(); setTimeout(() => document.getElementById('tcSearch')?.focus(), 100); }
    if (e.key === 's' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); toggleSortOrder(); }
});

// ========== 工具函数 ==========
function escHtml(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function escAttr(s) { return s.replace(/'/g, "\\'").replace(/"/g, '\\"'); }
function formatFileSize(b) { if (!b || b === 0) return ''; if (b < 1024) return b + ' B'; if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB'; return (b/(1024*1024)).toFixed(1) + ' MB'; }

// ========== 初始化 ==========
initTheme();
if (checkAuth()) {
    loadDocuments();
    loadQuickStats();
    initGlobalDragDrop();
}

// 登录/注册回车提交
document.getElementById('authPassword').addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
document.getElementById('regPasswordConfirm').addEventListener('keydown', e => { if (e.key === 'Enter') doRegister(); });

// ========== 生成保护：离开页面警告 ==========
window.addEventListener('beforeunload', (e) => {
    if (_isGenerating) {
        e.preventDefault();
        e.returnValue = '测试用例正在生成中，确定要离开吗？';
        return e.returnValue;
    }
});

// ========== v3.5: Playwright 自动化测试执行器 ==========
let _execSelectedIds = new Set();
let _execRunning = false;

async function loadExecTestcases() {
    const container = document.getElementById('execTestcasesList');
    if (!container) return;
    
    const docFilter = document.getElementById('execFilterDoc')?.value || '';
    const priorityFilter = document.getElementById('execFilterPriority')?.value || '';
    
    try {
        let url = '/api/testcases?page_size=100';
        if (docFilter) url += `&document_id=${docFilter}`;
        if (priorityFilter) url += `&priority=${priorityFilter}`;
        
        const data = await apiJson(url);
        const tcs = data.testcases || [];
        
        if (!tcs.length) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><p>暂无测试用例，请先上传文档并生成</p></div>`;
            return;
        }
        
        container.innerHTML = tcs.map(tc => `
            <div class="exec-tc-row" onclick="toggleExecTc(${tc.id}, this)">
                <input type="checkbox" id="exec-tc-${tc.id}" ${_execSelectedIds.has(tc.id) ? 'checked' : ''} onclick="event.stopPropagation(); toggleExecTc(${tc.id}, this.closest('.exec-tc-row'))">
                <span class="priority-badge ${tc.priority || 'P2'}" style="flex-shrink:0">${tc.priority || 'P2'}</span>
                <div class="exec-tc-info">
                    <div class="tc-title">${escapeHtml(tc.title)}</div>
                    <div class="tc-meta">${escapeHtml(tc.case_id || '')} · ${escapeHtml(tc.case_type || '')} · ${escapeHtml(tc.module || '未分类')}</div>
                </div>
            </div>
        `).join('');
        
        updateExecSelectedCount();
        
        // 同步文档筛选下拉
        syncExecDocFilter();
        
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>加载失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

function toggleExecTc(id, row) {
    const cb = document.getElementById(`exec-tc-${id}`);
    if (_execSelectedIds.has(id)) {
        _execSelectedIds.delete(id);
        if (cb) cb.checked = false;
        if (row) row.style.background = '';
    } else {
        _execSelectedIds.add(id);
        if (cb) cb.checked = true;
        if (row) row.style.background = 'var(--bg-hover)';
    }
    updateExecSelectedCount();
}

function execSelectAll() {
    document.querySelectorAll('.exec-tc-row input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
        const id = parseInt(cb.id.replace('exec-tc-', ''));
        _execSelectedIds.add(id);
        cb.closest('.exec-tc-row').style.background = 'var(--bg-hover)';
    });
    updateExecSelectedCount();
}

function execDeselectAll() {
    _execSelectedIds.clear();
    document.querySelectorAll('.exec-tc-row input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
        cb.closest('.exec-tc-row').style.background = '';
    });
    updateExecSelectedCount();
}

function updateExecSelectedCount() {
    const el = document.getElementById('execSelectedCount');
    if (el) el.textContent = `已选 ${_execSelectedIds.size} 个`;
}

async function syncExecDocFilter() {
    const select = document.getElementById('execFilterDoc');
    if (!select || select.options.length > 1) return;
    try {
        const docs = await apiJson('/api/documents?page_size=100');
        (docs.documents || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.id;
            opt.textContent = d.filename;
            select.appendChild(opt);
        });
    } catch(e) {}
}

async function startExecution() {
    if (_execSelectedIds.size === 0) {
        showToast('请先选择测试用例', 'warning');
        return;
    }
    if (_execRunning) {
        showToast('正在执行中，请等待完成', 'warning');
        return;
    }
    
    const baseUrl = document.getElementById('execBaseUrl')?.value || 'http://localhost:3000';
    const timeout = parseInt(document.getElementById('execTimeout')?.value || '30000');
    const ids = Array.from(_execSelectedIds);
    
    _execRunning = true;
    document.getElementById('startExecBtn').disabled = true;
    document.getElementById('startExecBtn').innerHTML = '<span>⏳ 执行中...</span>';
    
    const progressSection = document.getElementById('execProgressSection');
    progressSection.style.display = 'block';
    const resultsContainer = document.getElementById('execResultsContainer');
    resultsContainer.innerHTML = '';
    
    const progressFill = document.getElementById('execProgressFill');
    const progressText = document.getElementById('execProgressText');
    const statusEl = document.getElementById('execStatus');
    
    // 初始化结果卡片
    ids.forEach(id => {
        const row = document.querySelector(`#exec-tc-${id}`)?.closest('.exec-tc-row');
        const title = row?.querySelector('.tc-title')?.textContent || `ID: ${id}`;
        resultsContainer.innerHTML += `
            <div class="exec-result-card pending" id="exec-result-${id}">
                <div class="exec-result-header">
                    <h4><span class="exec-status-badge pending">⏳ 等待中</span> ${escapeHtml(title)}</h4>
                </div>
                <div class="exec-result-message">等待执行...</div>
            </div>`;
    });
    
    // SSE 流式执行
    try {
        const resp = await fetch(API_BASE + '/api/executor/run/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify({ testcase_ids: ids, base_url: baseUrl, timeout: timeout })
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ detail: '请求失败' }));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const data = JSON.parse(line.slice(6));
                    
                    switch (data.type) {
                        case 'start':
                            statusEl.textContent = data.message;
                            break;
                            
                        case 'running': {
                            statusEl.textContent = `正在执行 ${data.index}/${data.total}: ${data.case_id}`;
                            const card = document.getElementById(`exec-result-${ids[data.index - 1]}`);
                            if (card) {
                                card.className = 'exec-result-card running';
                                card.querySelector('.exec-result-header h4').innerHTML = `<span class="exec-status-badge running">🔄 执行中</span> ${escapeHtml(data.title || data.case_id)}`;
                                card.querySelector('.exec-result-message').textContent = '正在生成代码并执行...';
                            }
                            break;
                        }
                            
                        case 'result': {
                            const tcId = ids[data.index - 1];
                            const card = document.getElementById(`exec-result-${tcId}`);
                            if (card) {
                                const passed = data.passed;
                                card.className = `exec-result-card ${passed ? 'passed' : 'failed'}`;
                                const statusBadge = passed
                                    ? '<span class="exec-status-badge pass">✅ 通过</span>'
                                    : '<span class="exec-status-badge fail">❌ 失败</span>';
                                
                                let screenshotsHtml = '';
                                if (data.screenshots && data.screenshots.length) {
                                    screenshotsHtml = `<div class="exec-screenshot-thumbs">${data.screenshots.map(s => 
                                        `<img class="exec-screenshot-thumb" src="/api/executor/screenshots/${data.exec_id || 0}/${s}" onclick="openScreenshotModal(${data.exec_id || 0}, '${s}')" alt="${s}">`
                                    ).join('')}</div>`;
                                }
                                
                                card.innerHTML = `
                                    <div class="exec-result-header">
                                        <h4>${statusBadge} ${escapeHtml(data.case_id || '')}</h4>
                                        <span style="font-size:12px;color:var(--text-secondary)">${data.duration_ms ? (data.duration_ms/1000).toFixed(1) + 's' : ''}</span>
                                    </div>
                                    <div class="exec-result-meta">
                                        <span>📊 步骤: ${data.steps_completed || 0}/${data.steps_total || 0}</span>
                                        <span>⏱ ${data.duration_ms || 0}ms</span>
                                    </div>
                                    <div class="exec-result-message">${escapeHtml(data.message || (passed ? '所有步骤通过' : '执行失败'))}</div>
                                    ${screenshotsHtml}
                                `;
                            }
                            
                            // 更新进度
                            progressFill.style.width = `${(data.index / data.total * 100).toFixed(0)}%`;
                            progressText.textContent = `${data.index}/${data.total}`;
                            break;
                        }
                            
                        case 'complete':
                            statusEl.textContent = data.message;
                            progressFill.style.width = '100%';
                            showToast(data.message, data.failed === 0 ? 'success' : 'warning', 5000);
                            break;
                    }
                } catch (e) {}
            }
        }
    } catch (e) {
        statusEl.textContent = `执行失败: ${e.message}`;
        showToast(`执行失败: ${e.message}`, 'error');
    }
    
    _execRunning = false;
    document.getElementById('startExecBtn').disabled = false;
    document.getElementById('startExecBtn').innerHTML = '<span>🚀 开始执行</span>';
}

async function previewExecCode() {
    if (_execSelectedIds.size === 0) {
        showToast('请先选择测试用例', 'warning');
        return;
    }
    
    const firstId = Array.from(_execSelectedIds)[0];
    const baseUrl = document.getElementById('execBaseUrl')?.value || 'http://localhost:3000';
    const timeout = parseInt(document.getElementById('execTimeout')?.value || '30000');
    
    try {
        showToast('正在生成代码预览...', 'info');
        const data = await apiJson(`/api/executor/preview/${firstId}?base_url=${encodeURIComponent(baseUrl)}&timeout=${timeout}`);
        document.getElementById('codePreviewContent').textContent = data.code || '无代码';
        document.getElementById('codePreviewModal').classList.add('show');
    } catch (e) {
        showToast(`代码生成失败: ${e.message}`, 'error');
    }
}

function closeCodePreviewModal() {
    document.getElementById('codePreviewModal').classList.remove('show');
}

function closeScreenshotModal() {
    document.getElementById('screenshotModal').classList.remove('show');
}

function openScreenshotModal(execId, filename) {
    const modal = document.getElementById('screenshotModal');
    const gallery = document.getElementById('screenshotGallery');
    document.getElementById('screenshotTitle').textContent = `📸 ${filename}`;
    gallery.innerHTML = `<div style="grid-column:1/-1;text-align:center">
        <img src="/api/executor/screenshots/${execId}/${filename}" style="max-width:100%;max-height:80vh;border-radius:8px;border:1px solid var(--border-color)" alt="${filename}">
    </div>`;
    modal.classList.add('show');
}

async function loadExecHistory() {
    const section = document.getElementById('execHistorySection');
    section.style.display = 'block';
    const container = document.getElementById('execHistoryList');
    
    try {
        const data = await apiJson('/api/executor/history?page_size=50');
        const execs = data.executions || [];
        
        if (!execs.length) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">📜</div><p>暂无执行记录</p></div>';
            return;
        }
        
        container.innerHTML = `<table class="data-table"><thead><tr>
            <th>状态</th><th>用例ID</th><th>标题</th><th>步骤</th><th>耗时</th><th>执行时间</th><th>操作</th>
        </tr></thead><tbody>${execs.map(ex => `<tr>
            <td><span class="exec-status-badge ${ex.passed ? 'pass' : 'fail'}">${ex.passed ? '✅' : '❌'}</span></td>
            <td><code>${escapeHtml(ex.case_id)}</code></td>
            <td>${escapeHtml(ex.title || '')}</td>
            <td>${ex.steps_completed}/${ex.steps_total}</td>
            <td>${ex.duration_ms ? (ex.duration_ms/1000).toFixed(1) + 's' : '-'}</td>
            <td style="font-size:12px">${escapeHtml(ex.executed_at || '')}</td>
            <td>
                <button class="btn btn-outline btn-sm" onclick="viewExecDetail(${ex.id})">详情</button>
                <button class="btn btn-danger btn-sm" onclick="deleteExecRecord(${ex.id})">删除</button>
            </td>
        </tr>`).join('')}</tbody></table>`;
        
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>加载失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

async function viewExecDetail(execId) {
    try {
        const data = await apiJson(`/api/executor/history/${execId}`);
        const modal = document.getElementById('screenshotModal');
        const gallery = document.getElementById('screenshotGallery');
        document.getElementById('screenshotTitle').textContent = `📸 ${data.case_id} - ${data.title || ''}`;
        
        let html = `
            <div style="grid-column:1/-1">
                <div class="exec-result-meta" style="margin-bottom:12px">
                    <span><strong>结果:</strong> <span class="exec-status-badge ${data.passed ? 'pass' : 'fail'}">${data.passed ? '通过' : '失败'}</span></span>
                    <span><strong>步骤:</strong> ${data.steps_completed}/${data.steps_total}</span>
                    <span><strong>耗时:</strong> ${data.duration_ms ? (data.duration_ms/1000).toFixed(1) + 's' : '-'}</span>
                    <span><strong>时间:</strong> ${escapeHtml(data.executed_at || '')}</span>
                </div>
                ${data.message ? `<div class="exec-result-message">${escapeHtml(data.message)}</div>` : ''}
            </div>`;
        
        const screenshots = data.screenshots || [];
        if (screenshots.length) {
            html += screenshots.map(s => `
                <div>
                    <img src="/api/executor/screenshots/${execId}/${s}" style="width:100%;border-radius:8px;border:1px solid var(--border-color)" alt="${s}">
                    <div style="text-align:center;font-size:11px;color:var(--text-secondary);margin-top:4px">${s}</div>
                </div>
            `).join('');
        } else {
            html += '<div style="grid-column:1/-1;text-align:center;color:var(--text-secondary);padding:20px">无截图</div>';
        }
        
        // 代码展示
        if (data.code) {
            html += `<div style="grid-column:1/-1;margin-top:12px">
                <details><summary style="cursor:pointer;color:var(--accent);margin-bottom:8px">📝 查看生成的代码</summary>
                <pre style="background:var(--bg-tertiary);padding:16px;border-radius:8px;overflow-x:auto;font-size:12px;max-height:400px;font-family:'Fira Code',monospace">${escapeHtml(data.code)}</pre>
                </details>
            </div>`;
        }
        
        gallery.innerHTML = html;
        modal.classList.add('show');
    } catch (e) {
        showToast(`加载详情失败: ${e.message}`, 'error');
    }
}

async function deleteExecRecord(execId) {
    if (!confirm('确定删除这条执行记录？')) return;
    try {
        await api(`/api/executor/history/${execId}`, { method: 'DELETE' });
        showToast('删除成功');
        loadExecHistory();
    } catch (e) {
        showToast(`删除失败: ${e.message}`, 'error');
    }
}

async function clearExecHistory() {
    if (!confirm('确定清空所有执行历史？此操作不可恢复。')) return;
    try {
        await api('/api/executor/history', { method: 'DELETE' });
        showToast('执行历史已清空');
        loadExecHistory();
    } catch (e) {
        showToast(`清空失败: ${e.message}`, 'error');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ========== v4.0: 测试套件管理 ==========
async function loadSuites() {
    const container = document.getElementById('suitesContainer');
    if (!container) return;
    try {
        const data = await apiJson('/api/suites');
        const suites = data.suites || [];
        if (!suites.length) {
            container.innerHTML = `<div class="empty-state"><div class="empty-icon">📦</div><div class="empty-title">还没有测试套件</div><div class="empty-desc">创建套件将测试用例组合，一键执行完整测试流程</div><button class="empty-action" onclick="openCreateSuiteModal()">➕ 创建第一个套件</button></div>`;
            return;
        }
        container.innerHTML = suites.map(s => `
            <div class="document-card glass" onclick="openSuiteDetail(${s.id})" style="cursor:pointer">
                <div class="doc-header">
                    <span class="doc-icon">📦</span>
                    <div class="doc-info">
                        <h4>${escapeHtml(s.name)}</h4>
                        <p class="doc-meta">${escapeHtml(s.description || '无描述')}</p>
                    </div>
                </div>
                <div class="doc-stats">
                    <span>📋 ${s.member_count || 0} 个用例</span>
                    <span>🌐 ${escapeHtml(s.base_url || '')}</span>
                    <span>⏱ ${s.timeout || 30000}ms</span>
                </div>
                <div class="doc-actions">
                    <button class="btn btn-gradient btn-sm" onclick="event.stopPropagation(); runSuite(${s.id})">🚀 执行</button>
                    <button class="btn btn-outline btn-sm" onclick="event.stopPropagation(); editSuite(${s.id})">✏️ 编辑</button>
                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteSuite(${s.id})">🗑</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>加载失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

function openCreateSuiteModal() {
    document.getElementById('suiteEditId').value = '';
    document.getElementById('suiteName').value = '';
    document.getElementById('suiteDesc').value = '';
    document.getElementById('suiteBaseUrl').value = 'http://localhost:3000';
    document.getElementById('suiteTimeout').value = '30000';
    document.getElementById('suiteModalTitle').textContent = '📦 新建测试套件';
    document.getElementById('suiteModal').classList.add('show');
}

function closeSuiteModal() {
    document.getElementById('suiteModal').classList.remove('show');
}

async function saveSuite() {
    const id = document.getElementById('suiteEditId').value;
    const name = document.getElementById('suiteName').value.trim();
    if (!name) { showToast('请输入套件名称', 'warning'); return; }
    const body = {
        name,
        description: document.getElementById('suiteDesc').value,
        base_url: document.getElementById('suiteBaseUrl').value,
        timeout: parseInt(document.getElementById('suiteTimeout').value),
    };
    try {
        if (id) {
            await api(`/api/suites/${id}`, { method: 'PUT', body: JSON.stringify(body) });
            showToast('套件更新成功');
        } else {
            await apiJson('/api/suites', { method: 'POST', body: JSON.stringify(body) });
            showToast('套件创建成功');
        }
        closeSuiteModal();
        loadSuites();
    } catch (e) {
        showToast(`操作失败: ${e.message}`, 'error');
    }
}

async function editSuite(suiteId) {
    try {
        const data = await apiJson(`/api/suites/${suiteId}`);
        document.getElementById('suiteEditId').value = suiteId;
        document.getElementById('suiteName').value = data.name || '';
        document.getElementById('suiteDesc').value = data.description || '';
        document.getElementById('suiteBaseUrl').value = data.base_url || 'http://localhost:3000';
        document.getElementById('suiteTimeout').value = String(data.timeout || 30000);
        document.getElementById('suiteModalTitle').textContent = '✏️ 编辑套件';
        document.getElementById('suiteModal').classList.add('show');
    } catch (e) {
        showToast(`加载失败: ${e.message}`, 'error');
    }
}

async function deleteSuite(suiteId) {
    if (!confirm('确定删除此套件？')) return;
    try {
        await api(`/api/suites/${suiteId}`, { method: 'DELETE' });
        showToast('删除成功');
        loadSuites();
    } catch (e) {
        showToast(`删除失败: ${e.message}`, 'error');
    }
}

async function openSuiteDetail(suiteId) {
    try {
        const data = await apiJson(`/api/suites/${suiteId}`);
        document.getElementById('suiteDetailTitle').textContent = `📦 ${escapeHtml(data.name)}`;
        document.getElementById('suiteDetailModal').dataset.suiteId = suiteId;
        const members = data.members || [];
        let html = `<div style="margin-bottom:16px"><p style="color:var(--text-secondary)">${escapeHtml(data.description || '无描述')}</p>
            <div style="display:flex;gap:16px;margin-top:8px;font-size:13px;color:var(--text-secondary)">
                <span>🌐 ${escapeHtml(data.base_url)}</span><span>⏱ ${data.timeout}ms</span><span>📋 ${members.length} 个用例</span>
            </div></div>`;
        if (members.length) {
            html += '<div style="max-height:400px;overflow-y:auto"><table class="data-table"><thead><tr><th>编号</th><th>标题</th><th>优先级</th><th>类型</th><th>操作</th></tr></thead><tbody>' +
                members.map(m => `<tr>
                    <td><code>${escapeHtml(m.case_id)}</code></td>
                    <td>${escapeHtml(m.title)}</td>
                    <td><span class="priority-badge ${m.priority || 'P2'}">${m.priority || 'P2'}</span></td>
                    <td>${escapeHtml(m.case_type || '')}</td>
                    <td><button class="btn btn-danger btn-sm" onclick="removeSuiteMember(${suiteId}, ${m.id})">移除</button></td>
                </tr>`).join('') + '</tbody></table></div>';
        } else {
            html += '<div class="empty-state" style="padding:20px"><div class="empty-icon">📋</div><p>套件中暂无用例，请在「自动化测试」页面选择用例后添加到套件</p></div>';
        }
        document.getElementById('suiteDetailContent').innerHTML = html;
        document.getElementById('suiteDetailModal').classList.add('show');
    } catch (e) {
        showToast(`加载失败: ${e.message}`, 'error');
    }
}

function closeSuiteDetailModal() {
    document.getElementById('suiteDetailModal').classList.remove('show');
}

async function removeSuiteMember(suiteId, tcId) {
    try {
        await api(`/api/suites/${suiteId}/members/${tcId}`, { method: 'DELETE' });
        showToast('已移除');
        openSuiteDetail(suiteId);
    } catch (e) {
        showToast(`移除失败: ${e.message}`, 'error');
    }
}

async function runSuite(suiteId) {
    if (!confirm('确定执行此测试套件？')) return;
    try {
        const suite = await apiJson(`/api/suites/${suiteId}`);
        if (!suite.members || !suite.members.length) {
            showToast('套件中没有测试用例', 'warning');
            return;
        }
        // 切换到执行器视图，用套件的配置执行
        const ids = suite.members.map(m => m.id);
        _execSelectedIds = new Set(ids);
        document.querySelector('.nav-item[data-view="executor"]').click();
        setTimeout(() => {
            document.getElementById('execBaseUrl').value = suite.base_url || 'http://localhost:3000';
            document.getElementById('execTimeout').value = String(suite.timeout || 30000);
            startExecution();
        }, 300);
    } catch (e) {
        showToast(`加载套件失败: ${e.message}`, 'error');
    }
}

function runSuiteFromDetail() {
    const suiteId = parseInt(document.getElementById('suiteDetailModal').dataset.suiteId);
    if (suiteId) { closeSuiteDetailModal(); runSuite(suiteId); }
}

// ========== v4.0: 执行仪表盘 ==========
async function loadDashboard() {
    const container = document.getElementById('dashboardContent');
    if (!container) return;
    try {
        const data = await apiJson('/api/executor/stats');
        const passRate = data.pass_rate || 0;
        const total = data.total_executions || 0;
        const passed = data.total_passed || 0;
        const failed = total - passed;
        const daily = data.daily || [];
        const recent = data.recent || [];

        // Donut chart SVG
        const r = 54, c = 2 * Math.PI * r;
        const passLen = (passRate / 100) * c;
        const failLen = c - passLen;
        const donutColor = passRate >= 80 ? 'var(--success)' : passRate >= 50 ? 'var(--warning)' : 'var(--danger)';
        const donut = `<svg viewBox="0 0 128 128" class="dash-donut">
            <circle cx="64" cy="64" r="${r}" fill="none" stroke="var(--bg-tertiary)" stroke-width="12"/>
            <circle cx="64" cy="64" r="${r}" fill="none" stroke="${donutColor}" stroke-width="12"
                stroke-dasharray="${passLen} ${failLen}" stroke-dashoffset="${c/4}" stroke-linecap="round"
                style="transition:stroke-dasharray 1s ease"/>
            <text x="64" y="58" text-anchor="middle" class="dash-donut-value">${passRate}%</text>
            <text x="64" y="76" text-anchor="middle" class="dash-donut-label">通过率</text>
        </svg>`;

        // Daily trend bars
        const maxTotal = Math.max(...daily.map(d => d.total || 0), 1);
        const dailyBars = daily.map(d => {
            const passH = (d.passed / maxTotal * 100);
            const failH = ((d.total - d.passed) / maxTotal * 100);
            const dateLabel = (d.date || '').slice(5); // MM-DD
            return `<div class="dash-bar-col">
                <div class="dash-bar-stack">
                    <div class="dash-bar-seg pass" style="height:${passH}%" title="通过 ${d.passed}"></div>
                    <div class="dash-bar-seg fail" style="height:${failH}%" title="失败 ${d.total - d.passed}"></div>
                </div>
                <div class="dash-bar-count">${d.passed}/${d.total}</div>
                <div class="dash-bar-date">${dateLabel}</div>
            </div>`;
        }).join('');

        container.innerHTML = `
            <div class="dash-top-row">
                <div class="dash-donut-card glass">
                    <h4>📊 总体通过率</h4>
                    <div class="dash-donut-wrap">${donut}</div>
                    <div class="dash-donut-legend">
                        <span class="dash-legend-item"><span class="dash-legend-dot pass"></span>通过 ${passed}</span>
                        <span class="dash-legend-item"><span class="dash-legend-dot fail"></span>失败 ${failed}</span>
                        <span class="dash-legend-item"><span class="dash-legend-dot total"></span>共 ${total}</span>
                    </div>
                </div>
                <div class="dash-trend-card glass">
                    <h4>📈 每日执行趋势（近7天）</h4>
                    <div class="dash-bars-wrap">${dailyBars || '<div class="dash-empty">暂无执行数据，执行测试套件后将显示趋势</div>'}</div>
                    <div class="dash-bar-legend">
                        <span class="dash-legend-item"><span class="dash-legend-dot pass"></span>通过</span>
                        <span class="dash-legend-item"><span class="dash-legend-dot fail"></span>失败</span>
                    </div>
                </div>
            </div>
            <div class="dash-recent-card glass">
                <div class="dash-recent-header">
                    <h4>🕐 最近执行</h4>
                    <button class="btn btn-outline btn-sm" onclick="document.querySelector('.nav-item[data-view=&quot;executor&quot;]').click()">🚀 去执行</button>
                </div>
                ${recent.length ? `<table class="data-table"><thead><tr>
                    <th>状态</th><th>用例编号</th><th>标题</th><th>耗时</th><th>执行时间</th>
                </tr></thead><tbody>${recent.map(r => `<tr>
                    <td><span class="exec-status-badge ${r.passed ? 'pass' : 'fail'}">${r.passed ? '✅ 通过' : '❌ 失败'}</span></td>
                    <td><code>${escapeHtml(r.case_id)}</code></td>
                    <td>${escapeHtml(r.title || '')}</td>
                    <td>${r.duration_ms ? (r.duration_ms/1000).toFixed(1)+'s' : '-'}</td>
                    <td style="font-size:12px;color:var(--text-secondary)">${escapeHtml(r.executed_at || '')}</td>
                </tr>`).join('')}</tbody></table>` : '<div class="dash-empty">暂无执行记录</div>'}
            </div>`;
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">📊</div><p>加载失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

// ========== v4.0: 测试报告 ==========
let reportPage = 1;
async function loadReports(page) {
    if (page) reportPage = page;
    const container = document.getElementById('reportsContainer');
    if (!container) return;
    try {
        const data = await apiJson(`/api/reports?page=${reportPage}&page_size=20`);
        const reports = data.reports || [];
        if (!reports.length) {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">📄</div><p>暂无测试报告，执行测试套件后会自动生成</p></div>';
            return;
        }
        container.innerHTML = `<table class="data-table"><thead><tr>
            <th>#</th><th>套件</th><th>通过率</th><th>结果</th><th>耗时</th><th>时间</th><th>操作</th>
        </tr></thead><tbody>${reports.map(r => {
            const rate = r.total ? Math.round(r.passed / r.total * 100) : 0;
            return `<tr>
                <td>${r.id}</td>
                <td>${escapeHtml(r.suite_name)}</td>
                <td><span style="color:${rate >= 80 ? 'var(--success)' : rate >= 50 ? 'var(--warning)' : 'var(--danger)'};font-weight:600">${rate}%</span></td>
                <td>${r.passed}/${r.total}</td>
                <td>${r.duration_ms ? (r.duration_ms/1000).toFixed(1)+'s' : '-'}</td>
                <td style="font-size:12px">${escapeHtml(r.created_at || '')}</td>
                <td>
                    <a href="/api/reports/${r.id}/html" target="_blank" class="btn btn-outline btn-sm">📄 查看</a>
                    <button class="btn btn-danger btn-sm" onclick="deleteReport(${r.id})">🗑</button>
                </td>
            </tr>`;
        }).join('')}</tbody></table>`;
        renderPagination('reportsPagination', data.total, reportPage, 20, loadReports);
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>加载失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

async function deleteReport(reportId) {
    if (!confirm('确定删除此报告？')) return;
    try {
        await api(`/api/reports/${reportId}`, { method: 'DELETE' });
        showToast('删除成功');
        loadReports();
    } catch (e) {
        showToast(`删除失败: ${e.message}`, 'error');
    }
}

// ========== v4.0: 环境检测 ==========
async function loadEnvCheck() {
    const container = document.getElementById('envContent');
    if (!container) return;
    try {
        const data = await apiJson('/api/env/check');
        container.innerHTML = `
            <div class="settings-card glass" style="grid-column:1/-1">
                <h4>🐍 Python 环境</h4>
                <div style="margin-top:8px;font-size:13px">
                    <p><strong>路径:</strong> <code>${escapeHtml(data.python?.executable || '')}</code></p>
                    <p><strong>版本:</strong> ${escapeHtml(data.python?.version?.split(' ')[0] || '')}</p>
                </div>
            </div>
            <div class="settings-card glass">
                <h4>🎭 Playwright</h4>
                <div style="margin-top:8px;font-size:13px">
                    <p><strong>安装:</strong> <span class="exec-status-badge ${data.playwright?.installed ? 'pass' : 'fail'}">${data.playwright?.installed ? '✅ 已安装' : '❌ 未安装'}</span></p>
                    ${data.playwright?.version ? `<p><strong>版本:</strong> ${escapeHtml(data.playwright.version)}</p>` : ''}
                    <p><strong>浏览器:</strong> ${data.playwright?.browsers?.length ? data.playwright.browsers.map(b => `<span style="background:var(--bg-tertiary);padding:2px 8px;border-radius:4px;margin:2px">${escapeHtml(b)}</span>`).join(' ') : '❌ 未安装'}</p>
                    ${data.playwright?.error ? `<p style="color:var(--danger);margin-top:8px">${escapeHtml(data.playwright.error)}</p>` : ''}
                    <div style="margin-top:12px;display:flex;gap:8px">
                        ${!data.playwright?.installed ? '<button class="btn btn-gradient btn-sm" onclick="installDep(\'playwright\')">📥 安装 Playwright</button>' : ''}
                        ${data.playwright?.installed && !data.playwright?.browsers?.length ? '<button class="btn btn-gradient btn-sm" onclick="installDep(\'chromium\')">🌐 安装 Chromium</button>' : ''}
                    </div>
                </div>
            </div>
            <div class="settings-card glass">
                <h4>📑 PyMuPDF (PDF 解析)</h4>
                <div style="margin-top:8px;font-size:13px">
                    <p><strong>安装:</strong> <span class="exec-status-badge ${data.pymupdf?.installed ? 'pass' : 'fail'}">${data.pymupdf?.installed ? '✅ 已安装' : '❌ 未安装'}</span></p>
                    ${data.pymupdf?.version ? `<p><strong>版本:</strong> ${escapeHtml(data.pymupdf.version)}</p>` : ''}
                    <div style="margin-top:12px">
                        ${!data.pymupdf?.installed ? '<button class="btn btn-gradient btn-sm" onclick="installDep(\'pymupdf\')">📥 安装 PyMuPDF</button>' : ''}
                    </div>
                </div>
            </div>
            <div class="settings-card glass">
                <h4>🔐 Cryptography (API Key 加密)</h4>
                <div style="margin-top:8px;font-size:13px">
                    <p><strong>安装:</strong> <span class="exec-status-badge ${data.cryptography?.installed ? 'pass' : 'fail'}">${data.cryptography?.installed ? '✅ 已安装' : '❌ 未安装'}</span></p>
                    ${data.cryptography?.version ? `<p><strong>版本:</strong> ${escapeHtml(data.cryptography.version)}</p>` : ''}
                </div>
            </div>`;
    } catch (e) {
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><p>检测失败: ${escapeHtml(e.message)}</p></div>`;
    }
}

async function installDep(target) {
    showToast(`正在安装 ${target}...`, 'info', 10000);
    try {
        const result = await apiJson('/api/env/install', { method: 'POST', body: JSON.stringify({ target }) });
        if (result.success) {
            showToast(result.message, 'success');
            loadEnvCheck();
        } else {
            showToast(result.message, 'error');
        }
    } catch (e) {
        showToast(`安装失败: ${e.message}`, 'error');
    }
}

// ========== 生成状态管理（防误操作） ==========
function setGenerating(active, info = {}) {
    _isGenerating = active;
    const sidebar = document.getElementById('sidebar');
    const navItems = document.querySelectorAll('.nav-item');

    if (active) {
        // 锁定侧边栏，只允许留在当前页
        navItems.forEach(item => {
            item.dataset.prevOnclick = item.getAttribute('onclick') || '';
            item.style.pointerEvents = 'none';
            item.style.opacity = '0.5';
        });
        // 给"生成"弹窗的关闭按钮也禁用
        document.getElementById('closeGenerateBtn')?.setAttribute('disabled', 'true');
        // 添加生成中的视觉标记
        sidebar?.classList.add('generating');
        // 持久化生成状态
        try {
            localStorage.setItem(GEN_STATE_KEY, JSON.stringify({
                active: true, startTime: Date.now(), ...info
            }));
        } catch(e) {}
    } else {
        navItems.forEach(item => {
            item.style.pointerEvents = '';
            item.style.opacity = '';
        });
        document.getElementById('closeGenerateBtn')?.removeAttribute('disabled');
        sidebar?.classList.remove('generating');
        try { localStorage.removeItem(GEN_STATE_KEY); } catch(e) {}
    }
}

function restoreGenState() {
    try {
        const state = JSON.parse(localStorage.getItem(GEN_STATE_KEY) || 'null');
        if (state && state.active) {
            // 如果上次生成中意外关闭了页面，提示用户
            const elapsed = Math.round((Date.now() - state.startTime) / 1000);
            showToast(`上次生成在 ${elapsed} 秒前中断，后端可能仍在运行`, 'warning', 5000);
            localStorage.removeItem(GEN_STATE_KEY);
        }
    } catch(e) {}
}
restoreGenState();
