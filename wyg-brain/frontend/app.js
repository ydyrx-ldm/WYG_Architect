/**
 * 外脑 WYG Brain - 前端逻辑
 */

// ============================================
// 配置
// ============================================

const STORAGE_KEYS = {
    API_URL: 'wyg_api_url',
    DEEPSEEK_KEY: 'wyg_deepseek_key',
};

function getApiUrl() {
    return localStorage.getItem(STORAGE_KEYS.API_URL) || 'http://localhost:8000';
}

function getDeepSeekKey() {
    return localStorage.getItem(STORAGE_KEYS.DEEPSEEK_KEY) || '';
}

// ============================================
// API 客户端
// ============================================

const api = {
    async request(method, path, body = null) {
        const url = `${getApiUrl()}${path}`;
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(url, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || res.statusText);
        }
        return res.json();
    },

    // 记录
    async createRecord(data) {
        return this.request('POST', '/api/records', data);
    },
    async listRecords(limit = 50, offset = 0) {
        return this.request('GET', `/api/records?limit=${limit}&offset=${offset}`);
    },

    // /WYG
    async wygExplore(requirement) {
        return this.request('POST', '/api/wyg/explore', { requirement });
    },
    async wygPropose(solutionId) {
        return this.request('POST', '/api/wyg/propose', { solution_id: solutionId, confirmed: true });
    },
    async wygChat(solutionId, message) {
        return this.request('POST', '/api/wyg/chat', { solution_id: solutionId, message });
    },
    async getSolution(solutionId) {
        return this.request('GET', `/api/wyg/solutions/${solutionId}`);
    },

    // 健康检查
    async health() {
        return this.request('GET', '/health');
    },
};

// ============================================
// 状态
// ============================================

const state = {
    currentView: 'record',
    currentSolutionId: null,
    selectedMood: null,
    records: [],
    ws: null,
};

// ============================================
// 视图切换
// ============================================

function switchView(viewName) {
    state.currentView = viewName;

    // 更新导航
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // 更新视图
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const view = document.getElementById(`view-${viewName}`);
    if (view) view.classList.add('active');

    // 更新标题
    const titles = { record: '记录', wyg: '/WYG', solutions: '方案', timeline: '时间线' };
    document.getElementById('page-title').textContent = titles[viewName] || '';

    // 关闭移动端侧边栏
    document.getElementById('sidebar').classList.remove('open');
}

// ============================================
// 记录功能
// ============================================

async function submitRecord() {
    const input = document.getElementById('record-input');
    const content = input.value.trim();
    if (!content) return;

    const tags = document.getElementById('tag-input').value
        .split(/[,，]/)
        .map(t => t.trim())
        .filter(Boolean);

    try {
        const record = await api.createRecord({
            content,
            content_type: 'text',
            mood: state.selectedMood,
            tags,
        });

        input.value = '';
        document.getElementById('tag-input').value = '';
        state.selectedMood = null;
        document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));

        await loadRecords();
    } catch (err) {
        alert('保存失败: ' + err.message);
    }
}

async function loadRecords() {
    try {
        state.records = await api.listRecords();
        renderRecords();
    } catch (err) {
        console.error('加载记录失败:', err);
    }
}

function renderRecords() {
    const list = document.getElementById('record-list');
    if (!state.records.length) {
        list.innerHTML = '<div class="empty-state"><p>📝 还没有记录，开始记录你的想法吧</p></div>';
        return;
    }

    const moodEmoji = { happy: '😊', thinking: '🤔', idea: '💡', worry: '😟', angry: '😤' };

    list.innerHTML = state.records.map(r => `
        <div class="record-card">
            <div class="record-card-header">
                ${r.mood ? `<span class="record-mood">${moodEmoji[r.mood] || ''}</span>` : ''}
                <span class="record-time">${formatTime(r.created_at)}</span>
            </div>
            <div class="record-content">${escapeHtml(r.content)}</div>
            ${r.tags && r.tags.length ? `
                <div class="record-tags">
                    ${r.tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
                </div>
            ` : ''}
            <div class="record-card-actions">
                <button onclick="startWygFromRecord(${r.id}, '${escapeAttr(r.content)}')">🎯 /WYG 分析</button>
            </div>
        </div>
    `).join('');
}

function startWygFromRecord(recordId, content) {
    switchView('wyg');
    document.getElementById('wyg-input').value = content;
}

// ============================================
// /WYG 功能
// ============================================

async function startWyg() {
    const input = document.getElementById('wyg-input');
    const requirement = input.value.trim();
    if (!requirement) return;

    // 显示对话界面
    document.getElementById('wyg-start').style.display = 'none';
    document.getElementById('wyg-chat').style.display = 'flex';

    // 添加用户消息
    addChatMessage('user', requirement);

    // 调用 explore API
    try {
        const result = await api.wygExplore(requirement);
        state.currentSolutionId = result.solution_id;
        addChatMessage('assistant', result.ba_output, 'BA');
        document.getElementById('chat-confirm').style.display = 'inline-block';
    } catch (err) {
        addChatMessage('assistant', '❌ 探索失败: ' + err.message, 'system');
    }
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || !state.currentSolutionId) return;

    input.value = '';
    addChatMessage('user', message);

    try {
        const result = await api.wygChat(state.currentSolutionId, message);
        addChatMessage('assistant', result.content, result.agent);
    } catch (err) {
        addChatMessage('assistant', '❌ 发送失败: ' + err.message, 'system');
    }
}

async function confirmExplore() {
    if (!state.currentSolutionId) return;

    document.getElementById('chat-confirm').style.display = 'none';
    addChatMessage('assistant', '⏳ 正在进入 propose 阶段（SA 方案设计 + PM 任务拆解 + RR 准入评审）...', 'system');

    try {
        const result = await api.wygPropose(state.currentSolutionId);

        addChatMessage('assistant', result.sa_output, 'SA');
        addChatMessage('assistant', result.pm_output, 'PM');

        const verdict = result.rr_verdict === 'pass' ? '✅ 准入通过' : '❌ 准入不通过';
        addChatMessage('assistant', `${verdict}\n\n${result.rr_output}`, 'RR');

        // 刷新方案列表
        await loadSolutions();
    } catch (err) {
        addChatMessage('assistant', '❌ Propose 失败: ' + err.message, 'system');
    }
}

function addChatMessage(role, content, agent = null) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;

    let html = '';
    if (agent && role === 'assistant') {
        html += `<div class="agent-badge">${agent}</div>`;
    }
    html += escapeHtml(content);

    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function resetWygView() {
    document.getElementById('wyg-start').style.display = 'flex';
    document.getElementById('wyg-chat').style.display = 'none';
    document.getElementById('chat-messages').innerHTML = '';
    document.getElementById('chat-confirm').style.display = 'none';
    document.getElementById('wyg-input').value = '';
    state.currentSolutionId = null;
}

// ============================================
// 方案功能
// ============================================

async function loadSolutions() {
    // 暂时从记录中提取方案信息
    // TODO: 后端增加方案列表 API
}

function showSolutionDetail(solutionId) {
    api.getSolution(solutionId).then(sol => {
        const modal = document.getElementById('solution-modal');
        const title = document.getElementById('solution-modal-title');
        const body = document.getElementById('solution-modal-body');

        title.textContent = `方案 #${sol.id} - ${sol.phase}`;

        let html = '';
        if (sol.ba_output) {
            html += `<div class="solution-detail-section"><h4>📋 BA 需求探索</h4><pre>${escapeHtml(sol.ba_output)}</pre></div>`;
        }
        if (sol.sa_output) {
            html += `<div class="solution-detail-section"><h4>🏗️ SA 方案设计</h4><pre>${escapeHtml(sol.sa_output)}</pre></div>`;
        }
        if (sol.pm_tasks) {
            html += `<div class="solution-detail-section"><h4>📋 PM 任务列表</h4><pre>${escapeHtml(typeof sol.pm_tasks === 'string' ? sol.pm_tasks : JSON.stringify(sol.pm_tasks, null, 2))}</pre></div>`;
        }
        if (sol.rr_verdict) {
            html += `<div class="solution-detail-section"><h4>🚦 RR 准入评审</h4><pre>${sol.rr_verdict === 'pass' ? '✅ 通过' : '❌ 不通过'}</pre></div>`;
        }

        body.innerHTML = html;
        modal.style.display = 'flex';
    }).catch(err => {
        alert('加载方案失败: ' + err.message);
    });
}

// ============================================
// WebSocket
// ============================================

function connectWebSocket() {
    const apiUrl = getApiUrl();
    const wsUrl = apiUrl.replace(/^http/, 'ws') + '/ws/default';

    try {
        state.ws = new WebSocket(wsUrl);

        state.ws.onopen = () => {
            updateWsStatus(true);
        };

        state.ws.onclose = () => {
            updateWsStatus(false);
            // 5秒后重连
            setTimeout(connectWebSocket, 5000);
        };

        state.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        };

        state.ws.onerror = () => {
            updateWsStatus(false);
        };
    } catch (err) {
        console.error('WebSocket 连接失败:', err);
        updateWsStatus(false);
    }
}

function updateWsStatus(online) {
    const dot = document.querySelector('#ws-status .status-dot');
    const text = document.querySelector('#ws-status span:last-child');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
    text.textContent = online ? '已连接' : '未连接';
}

function handleWsMessage(msg) {
    switch (msg.type) {
        case 'record_updated':
            loadRecords();
            break;
        case 'agent_stream':
            // 实时流式输出
            break;
    }
}

// ============================================
// 设置
// ============================================

function openSettings() {
    document.getElementById('setting-api-url').value = getApiUrl();
    document.getElementById('setting-deepseek-key').value = getDeepSeekKey();
    document.getElementById('api-modal').style.display = 'flex';
}

function saveSettings() {
    const apiUrl = document.getElementById('setting-api-url').value.trim();
    const deepseekKey = document.getElementById('setting-deepseek-key').value.trim();

    localStorage.setItem(STORAGE_KEYS.API_URL, apiUrl);
    localStorage.setItem(STORAGE_KEYS.DEEPSEEK_KEY, deepseekKey);

    document.getElementById('api-modal').style.display = 'none';

    // 重新连接
    if (state.ws) state.ws.close();
    connectWebSocket();
    loadRecords();
}

// ============================================
// 工具函数
// ============================================

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
    return str.replace(/'/g, "\\'").replace(/\n/g, ' ').substring(0, 100);
}

function formatTime(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;

    return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ============================================
// 事件绑定
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // 导航
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => switchView(btn.dataset.view));
    });

    // 侧边栏
    document.getElementById('sidebar-toggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });
    document.getElementById('sidebar-close').addEventListener('click', () => {
        document.getElementById('sidebar').classList.remove('open');
    });

    // 心情选择
    document.querySelectorAll('.mood-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            state.selectedMood = btn.dataset.mood;
        });
    });

    // 记录提交
    document.getElementById('record-submit').addEventListener('click', submitRecord);
    document.getElementById('record-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitRecord();
    });

    // /WYG
    document.getElementById('wyg-submit').addEventListener('click', startWyg);
    document.getElementById('chat-send').addEventListener('click', sendChat);
    document.getElementById('chat-confirm').addEventListener('click', confirmExplore);
    document.getElementById('chat-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendChat();
    });

    // 设置
    document.getElementById('api-key-btn').addEventListener('click', openSettings);
    document.getElementById('settings-save').addEventListener('click', saveSettings);
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').style.display = 'none';
        });
    });

    // 点击遮罩关闭弹窗
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.style.display = 'none';
        });
    });

    // 初始化
    loadRecords();
    connectWebSocket();
});
