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
    async wygRevise(solutionId, message) {
        return this.request('POST', '/api/wyg/revise', { solution_id: solutionId, message });
    },
    async wygChat(solutionId, message) {
        return this.request('POST', '/api/wyg/chat', { solution_id: solutionId, message });
    },
    async getSolution(solutionId) {
        return this.request('GET', `/api/wyg/solutions/${solutionId}`);
    },

    // 猜词游戏
    async gameStart() {
        return this.request('POST', '/api/game/start');
    },
    async gameGuess(gameId, guess) {
        return this.request('POST', '/api/game/guess', { game_id: gameId, guess });
    },
    async gameGiveup(gameId) {
        return this.request('POST', '/api/game/giveup', { game_id: gameId, guess: '' });
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
    pendingChoices: {},  // 收集的选择题答案 { questionIndex: selectedText }
    proposeCompleted: false,  // propose 阶段是否已完成
    gameId: null,  // 猜词游戏会话ID
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
    const titles = { record: '记录', wyg: '/WYG', solutions: '方案', timeline: '时间线', game: '猜词游戏' };
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
        list.innerHTML = '<div class="empty-state"><p>还没有记录，开始记录你的想法吧</p></div>';
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

    // 添加思考提示
    const thinkingId = addThinkingMessage('BA 需求分析师正在思考');

    // 调用 explore API
    try {
        const result = await api.wygExplore(requirement);
        removeThinkingMessage(thinkingId);
        state.currentSolutionId = result.solution_id;
        addChatMessage('assistant', result.ba_output, 'BA');
    } catch (err) {
        removeThinkingMessage(thinkingId);
        let errMsg = err.message;
        if (errMsg === 'Failed to fetch') {
            errMsg = '无法连接后端服务。请确认：\n1. 后端已启动（运行 main.py）\n2. 在设置中检查后端地址是否正确';
        }
        addChatMessage('assistant', '❌ 探索失败: ' + errMsg, 'system');
    }
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || !state.currentSolutionId) return;

    input.value = '';

    // 如果 propose 已完成，走 revise 流程而非 BA chat
    if (state.proposeCompleted) {
        addChatMessage('user', message);

        // 移除追问输入框（如果存在）
        const reviseArea = document.getElementById('revise-area');
        if (reviseArea) reviseArea.remove();

        const thinkingId = addThinkingMessage('正在修改方案');
        try {
            const result = await api.wygRevise(state.currentSolutionId, message);
            removeThinkingMessage(thinkingId);

            addAgentOrchestration();
            if (result.summary_output) {
                addResultCard(result.summary_output, result.rr_verdict);
            }

            showReviseInput();
        } catch (err) {
            removeThinkingMessage(thinkingId);
            let errMsg = err.message;
            if (errMsg === 'Failed to fetch') {
                errMsg = '无法连接后端服务。请确认后端已启动';
            }
            addChatMessage('assistant', '❌ 修改失败: ' + errMsg, 'system');
            showReviseInput();
        }
        return;
    }

    // explore 阶段：走 BA chat
    addChatMessage('user', message);

    const thinkingId = addThinkingMessage('BA 需求分析师正在思考');

    try {
        const result = await api.wygChat(state.currentSolutionId, message);
        removeThinkingMessage(thinkingId);

        // 判断 BA 是否认为需求已澄清
        const baReply = result.content || '';
        const isClarified = baReply.includes('需求已澄清') || baReply.includes('需求澄清');

        if (isClarified) {
            addChatMessage('assistant', '需求已明确，正在生成方案...', 'system');
            autoPropose();
        } else {
            addChatMessage('assistant', result.content, result.agent);
        }
    } catch (err) {
        removeThinkingMessage(thinkingId);
        let errMsg = err.message;
        if (errMsg === 'Failed to fetch') {
            errMsg = '无法连接后端服务。请确认后端已启动';
        }
        addChatMessage('assistant', '❌ 发送失败: ' + errMsg, 'system');
    }
}

async function confirmExplore() {
    // 用户主动确认需求已澄清，直接进入 propose
    await autoPropose();
}

function showReviseInput() {
    // 如果已存在追问输入框，不重复添加
    if (document.getElementById('revise-area')) return;

    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.id = 'revise-area';
    div.className = 'revise-area';
    div.innerHTML = `
        <div class="revise-label">想调整方案？告诉我你的想法</div>
        <div class="revise-input-row">
            <textarea id="revise-input" placeholder="比如：预算再低一点、想去海边、多安排点自由活动..." rows="2"></textarea>
            <button class="revise-btn" onclick="submitRevise()">重新生成</button>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

async function submitRevise() {
    const input = document.getElementById('revise-input');
    const message = input.value.trim();
    if (!message || !state.currentSolutionId) return;

    // 移除追问输入框
    const reviseArea = document.getElementById('revise-area');
    if (reviseArea) reviseArea.remove();

    // 显示用户消息
    addChatMessage('user', message);

    const thinkingId = addThinkingMessage('正在修改方案');
    try {
        const result = await api.wygRevise(state.currentSolutionId, message);
        removeThinkingMessage(thinkingId);

        // 显示 Agent 编排 + 结果卡片
        addAgentOrchestration();
        if (result.summary_output) {
            addResultCard(result.summary_output, result.rr_verdict);
        }

        // 再次显示追问输入框
        showReviseInput();
    } catch (err) {
        removeThinkingMessage(thinkingId);
        let errMsg = err.message;
        if (errMsg === 'Failed to fetch') {
            errMsg = '无法连接后端服务。请确认后端已启动';
        }
        addChatMessage('assistant', '❌ 修改失败: ' + errMsg, 'system');
        showReviseInput();
    }
}

// ============================================
// 聊天消息渲染
// ============================================

function addChatMessage(role, content, agent = null) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;

    let html = '';
    if (agent && role === 'assistant') {
        html += `<div class="agent-badge">${agent}</div>`;
    }

    // 解析选择题：问题1：xxx A) ... B) ... C) ...
    if (role === 'assistant' && content.match(/^[A-C][)\．].+/m)) {
        const parsed = parseChoices(content);
        html += escapeHtml(parsed.text);

        if (parsed.questions.length > 0) {
            // 分问题渲染
            parsed.questions.forEach((q, qi) => {
                const msgId = 'msg-' + Date.now() + '-' + qi;
                if (q.text) {
                    html += `<div class="choice-question">${escapeHtml(q.text)}</div>`;
                }
                html += '<div class="choice-options" data-msg-id="' + msgId + '">';
                q.options.forEach(opt => {
                    html += `<button class="choice-btn" data-msg-id="${msgId}" onclick="selectChoice(this, '${escapeAttr(opt.text)}')">${escapeHtml(opt.label)} ${escapeHtml(opt.text)}</button>`;
                });
                html += '</div>';
            });
        } else {
            // 兼容旧格式：没有问题分组，直接是 A) B) C)
            const oldParsed = parseChoicesOld(content);
            html += escapeHtml(oldParsed.text);
            if (oldParsed.options.length > 0) {
                const msgId = 'msg-' + Date.now();
                html += '<div class="choice-options" data-msg-id="' + msgId + '">';
                oldParsed.options.forEach(opt => {
                    html += `<button class="choice-btn" data-msg-id="${msgId}" onclick="selectChoice(this, '${escapeAttr(opt.text)}')">${escapeHtml(opt.label)} ${escapeHtml(opt.text)}</button>`;
                });
                html += '</div>';
            }
        }
        // 统一确认按钮：所有选择题选完后才显示
        const batchId = 'batch-' + Date.now();
        html += `<button class="choice-submit-btn" id="${batchId}" style="display:none" onclick="submitAllChoices()">确认选择</button>`;
    } else {
        html += escapeHtml(content);
    }

    div.innerHTML = html;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addResultCard(summaryText, rrVerdict) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';

    // 解析 markdown 风格的标题和内容
    const sections = summaryText.split(/##\s*/).filter(s => s.trim());
    let cardHtml = `<div class="result-card">`;

    // 顶部状态栏
    const statusIcon = rrVerdict === 'pass' ? '✅' : '⚠️';
    const statusText = rrVerdict === 'pass' ? '方案已就绪' : '方案需调整';
    cardHtml += `<div class="result-status ${rrVerdict}">${statusIcon} ${statusText}</div>`;

    sections.forEach(section => {
        const lines = section.split('\n').filter(l => l.trim());
        if (lines.length === 0) return;
        const title = lines[0].replace(/###\s*/, '').trim();
        const content = lines.slice(1).join('\n').trim();
        if (title && content) {
            cardHtml += `<div class="result-section">`;
            cardHtml += `<div class="result-section-title">${escapeHtml(title)}</div>`;
            cardHtml += `<div class="result-section-content">${escapeHtml(content)}</div>`;
            cardHtml += `</div>`;
        }
    });

    cardHtml += `</div>`;
    div.innerHTML = cardHtml;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addSummaryCard(summaryText, rrVerdict) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';

    const verdictIcon = rrVerdict === 'pass' ? '✅' : '❌';
    const verdictText = rrVerdict === 'pass' ? '准入通过' : '准入不通过';

    // 解析 markdown 风格的标题和内容
    const sections = summaryText.split(/##\s*/).filter(s => s.trim());
    let cardHtml = `<div class="summary-card">`;
    cardHtml += `<div class="summary-header">${verdictIcon} 决策摘要 <span class="summary-verdict ${rrVerdict}">${verdictText}</span></div>`;

    sections.forEach(section => {
        const lines = section.split('\n').filter(l => l.trim());
        if (lines.length === 0) return;
        const title = lines[0].replace(/###\s*/, '').trim();
        const content = lines.slice(1).join('\n').trim();
        if (title && content) {
            cardHtml += `<div class="summary-section">`;
            cardHtml += `<div class="summary-section-title">${escapeHtml(title)}</div>`;
            cardHtml += `<div class="summary-section-content">${escapeHtml(content)}</div>`;
            cardHtml += `</div>`;
        }
    });

    cardHtml += `</div>`;
    div.innerHTML = cardHtml;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addDetailToggle(title, content) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'chat-msg assistant';

    const toggleId = 'detail-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5);
    div.innerHTML = `
        <div class="detail-toggle" onclick="toggleDetail('${toggleId}')">
            <span class="detail-toggle-arrow" id="arrow-${toggleId}">▶</span>
            <span class="detail-toggle-title">${escapeHtml(title)}</span>
        </div>
        <div class="detail-content" id="${toggleId}" style="display:none">${escapeHtml(content)}</div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function toggleDetail(id) {
    const el = document.getElementById(id);
    const arrow = document.getElementById('arrow-' + id);
    if (el.style.display === 'none') {
        el.style.display = 'block';
        arrow.textContent = '▼';
    } else {
        el.style.display = 'none';
        arrow.textContent = '▶';
    }
}

// ============================================
// 选择题解析
// ============================================

function parseChoices(text) {
    // 按问题分组解析：问题1：xxx A) ... B) ... C) ...  空行  问题2：xxx A) ... B) ... C) ...
    const lines = text.split('\n');
    const result = { questions: [], text: '' };

    let currentQuestion = null;
    let textLines = [];
    let inOptions = false;

    for (const line of lines) {
        const trimmed = line.trim();

        // 检测问题行：问题1：xxx 或 问题N：xxx 或 Q1：xxx
        const questionMatch = trimmed.match(/^问题\s*\d+[：:]\s*(.+)/) || trimmed.match(/^Q\d+[：:]\s*(.+)/);
        if (questionMatch) {
            // 保存上一个问题
            if (currentQuestion && currentQuestion.options.length > 0) {
                currentQuestion = _dedupOptions(currentQuestion);
                result.questions.push(currentQuestion);
            }
            currentQuestion = { text: questionMatch[1].trim(), options: [] };
            inOptions = true;
            continue;
        }

        // 检测选项行：A) xxx B) xxx C) xxx
        const optionMatch = trimmed.match(/^([A-C])[)\．.）]\s*(.+)/);
        if (optionMatch && (currentQuestion || !inOptions)) {
            if (!currentQuestion) {
                currentQuestion = { text: '', options: [] };
            }
            inOptions = true;
            currentQuestion.options.push({ label: optionMatch[1], text: optionMatch[2].trim() });
            continue;
        }

        // 空行 = 问题分隔
        if (trimmed === '') {
            if (currentQuestion && currentQuestion.options.length > 0) {
                currentQuestion = _dedupOptions(currentQuestion);
                result.questions.push(currentQuestion);
                currentQuestion = null;
            }
            inOptions = false;
            continue;
        }

        // 非问题非选项的文字
        if (!inOptions) {
            textLines.push(line);
        }
    }

    // 保存最后一个问题
    if (currentQuestion && currentQuestion.options.length > 0) {
        currentQuestion = _dedupOptions(currentQuestion);
        result.questions.push(currentQuestion);
    }

    result.text = textLines.join('\n');
    return result;
}

function _dedupOptions(question) {
    /** 前端选项去重：规则匹配（不硬编码近义词） */
    if (!question || question.options.length <= 1) return question;

    const deduped = [];
    const seen = [];

    for (const opt of question.options) {
        const clean = opt.text.replace(/[的了吗呢吧啊呀很非常比较更加最]/g, '').trim();
        let isDup = false;

        for (const s of seen) {
            // 1. 精确匹配
            if (clean === s) { isDup = true; break; }
            // 2. 包含关系
            if (clean.includes(s) || s.includes(clean)) { isDup = true; break; }
            // 3. 字符重叠度 > 0.6
            const setA = new Set(clean), setB = new Set(s);
            const inter = [...setA].filter(c => setB.has(c)).length;
            const overlap = inter / Math.min(setA.size, setB.size);
            if (overlap > 0.6) { isDup = true; break; }
            // 4. 共享核心词检测：公共子串在开头 → 核心词相同 → 相似
            const shorter = clean.length <= s.length ? clean : s;
            const longer = clean.length <= s.length ? s : clean;
            if (shorter.length >= 2 && shorter !== longer) {
                let maxCommon = 0, commonStr = '';
                for (let wLen = shorter.length; wLen >= 2; wLen--) {
                    let found = false;
                    for (let start = 0; start <= shorter.length - wLen; start++) {
                        const sub = shorter.substring(start, start + wLen);
                        if (longer.includes(sub)) {
                            maxCommon = wLen; commonStr = sub; found = true; break;
                        }
                    }
                    if (found) break;
                }
                if (maxCommon >= 2 && shorter.startsWith(commonStr) && longer.startsWith(commonStr)) {
                    isDup = true; break;
                }
            }
        }
        if (!isDup) {
            seen.push(clean);
            deduped.push(opt);
        }
    }

    // 不足 3 个时补充
    const fills = ['其他', '都不选', '看情况'];
    const labels = ['A', 'B', 'C'];
    while (deduped.length < 3) {
        deduped.push({ label: labels[deduped.length] || 'C', text: fills[deduped.length] || fills[2] });
    }

    // 重新分配标签
    deduped.forEach((opt, i) => { opt.label = labels[i] || String.fromCharCode(65 + i); });

    return { text: question.text, options: deduped.slice(0, 3) };
}

function parseChoicesOld(text) {
    // 旧格式兼容：直接 A) xxx B) xxx C) xxx
    const lines = text.split('\n');
    const textLines = [];
    const options = [];
    let inOptions = false;

    for (const line of lines) {
        const match = line.match(/^([A-C])[)\．.）]\s*(.+)/);
        if (match) {
            inOptions = true;
            options.push({ label: match[1], text: match[2].trim() });
        } else if (inOptions) {
            if (line.trim() && options.length > 0) {
                options[options.length - 1].text += ' ' + line.trim();
            }
        } else {
            textLines.push(line);
        }
    }

    // 用 _dedupOptions 去重
    const q = _dedupOptions({ text: '', options });
    return { text: textLines.join('\n'), options: q.options };
}

// ============================================
// 选择题交互
// ============================================

function selectChoice(btn, text) {
    const msgId = btn.dataset.msgId;

    // 同一组选择题内，取消其他选中，选中当前
    const container = btn.parentElement;
    container.querySelectorAll('.choice-btn').forEach(b => {
        b.classList.remove('selected');
    });
    btn.classList.add('selected');

    // 记录选择
    state.pendingChoices[msgId] = text;

    // 检查是否所有选择题组都已选择
    checkAllChoicesSelected();
}

function checkAllChoicesSelected() {
    // 只检查未被禁用的选择题组（跳过已提交的旧选择题）
    const activeGroups = document.querySelectorAll('.choice-options:not(.submitted)');
    let allSelected = true;

    activeGroups.forEach(group => {
        const hasSelected = group.querySelector('.choice-btn.selected');
        if (!hasSelected) {
            allSelected = false;
        }
    });

    // 所有活跃组都选完后，显示统一确认按钮
    const submitBtns = document.querySelectorAll('.choice-submit-btn:not(.submitted)');
    submitBtns.forEach(btn => {
        btn.style.display = (allSelected && activeGroups.length > 0) ? 'inline-block' : 'none';
    });
}

function submitAllChoices() {
    if (!state.currentSolutionId) return;

    // 收集所有活跃（未提交）选择题的问题和答案
    const allAnswers = [];
    document.querySelectorAll('.choice-options:not(.submitted)').forEach(group => {
        const selected = group.querySelector('.choice-btn.selected');
        // 找到对应的问题文本
        const prevQuestion = group.previousElementSibling;
        const questionText = prevQuestion && prevQuestion.classList.contains('choice-question')
            ? prevQuestion.textContent.trim() : '';
        if (selected) {
            const answerText = selected.textContent.trim();
            if (questionText) {
                allAnswers.push(questionText + ' → ' + answerText);
            } else {
                allAnswers.push(answerText);
            }
        }
    });

    if (allAnswers.length === 0) return;

    // 标记已提交的选择题组（不再参与后续检查）
    document.querySelectorAll('.choice-options:not(.submitted)').forEach(group => {
        group.classList.add('submitted');
        group.querySelectorAll('.choice-btn').forEach(b => b.disabled = true);
    });
    document.querySelectorAll('.choice-submit-btn:not(.submitted)').forEach(btn => {
        btn.classList.add('submitted');
        btn.style.display = 'none';
    });

    // 清空待选
    state.pendingChoices = {};

    // 添加用户消息到对话区（显示简洁答案）
    const displayText = allAnswers.map(a => {
        const parts = a.split(' → ');
        return parts.length > 1 ? parts[1] : parts[0];
    }).join('、');
    addChatMessage('user', displayText);

    // 发送完整上下文给 BA（包含问题+答案，便于 BA 理解）
    const fullContext = allAnswers.join('\n');

    const thinkingId = addThinkingMessage('正在分析你的选择');

    api.wygChat(state.currentSolutionId, fullContext).then(result => {
        removeThinkingMessage(thinkingId);

        // 判断 BA 是否认为需求已澄清
        const baReply = result.content || '';
        const isClarified = baReply.includes('需求已澄清') || baReply.includes('需求澄清');

        if (isClarified) {
            // 需求已澄清，自动进入 propose 阶段
            addChatMessage('assistant', '需求已明确，正在生成方案...', 'system');
            autoPropose();
        } else {
            // BA 还有新问题，继续展示
            addChatMessage('assistant', result.content, result.agent);
            // 不再显示"生成方案"按钮，用户选完下一轮选择题后会自动判断
        }
    }).catch(err => {
        removeThinkingMessage(thinkingId);
        let errMsg = err.message;
        if (errMsg === 'Failed to fetch') {
            errMsg = '无法连接后端服务。请确认后端已启动';
        }
        addChatMessage('assistant', '❌ 发送失败: ' + errMsg, 'system');
    });
}

async function autoPropose() {
    if (!state.currentSolutionId) return;

    const thinkingId = addThinkingMessage('7 个 Agent 正在协作生成方案');
    try {
        const result = await api.wygPropose(state.currentSolutionId);
        removeThinkingMessage(thinkingId);

        // 显示 Agent 编排信息 + 结果卡片
        addAgentOrchestration();
        if (result.summary_output) {
            addResultCard(result.summary_output, result.rr_verdict);
        }

        // 标记 propose 完成，显示追问输入框
        state.proposeCompleted = true;
        showReviseInput();

        await loadSolutions();
    } catch (err) {
        removeThinkingMessage(thinkingId);
        addChatMessage('assistant', '❌ 方案生成失败: ' + err.message, 'system');
    }
}

function addAgentOrchestration() {
    // 在对话框中输出 Agent 编排信息
    const text = '7 个 Agent 协作完成\n\n' +
        '🔹 BA 需求分析师 — 澄清了你的需求，明确了目标\n' +
        '🔹 SA 架构设计师 — 设计了推荐方案和备选方案\n' +
        '🔹 PM 项目经理 — 拆解了可执行的任务清单\n' +
        '🔹 RR 就绪评审 — 检查方案是否满足快速执行和用户友好\n' +
        '🔹 SUMMARY 摘要生成 — 把技术方案翻译成你能看懂的结果';
    addChatMessage('assistant', text, '编排');
}

// ============================================
// 思考提示
// ============================================

let thinkingCounter = 0;

function addThinkingMessage(text) {
    const container = document.getElementById('chat-messages');
    const id = 'thinking-' + (++thinkingCounter);
    const div = document.createElement('div');
    div.className = 'chat-msg assistant thinking-msg';
    div.id = id;
    div.innerHTML = `<div class="thinking-indicator"><span class="thinking-dots"></span> ${escapeHtml(text)}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeThinkingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function resetWygView() {
    document.getElementById('wyg-start').style.display = 'flex';
    document.getElementById('wyg-chat').style.display = 'none';
    document.getElementById('chat-messages').innerHTML = '';
    document.getElementById('chat-confirm').style.display = 'none';
    document.getElementById('wyg-input').value = '';
    state.currentSolutionId = null;
    state.proposeCompleted = false;
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
            html += `<div class="solution-detail-section"><h4>BA 需求探索</h4><pre>${escapeHtml(sol.ba_output)}</pre></div>`;
        }
        if (sol.sa_output) {
            html += `<div class="solution-detail-section"><h4>SA 方案设计</h4><pre>${escapeHtml(sol.sa_output)}</pre></div>`;
        }
        if (sol.pm_tasks) {
            html += `<div class="solution-detail-section"><h4>PM 任务列表</h4><pre>${escapeHtml(typeof sol.pm_tasks === 'string' ? sol.pm_tasks : JSON.stringify(sol.pm_tasks, null, 2))}</pre></div>`;
        }
        if (sol.rr_verdict) {
            html += `<div class="solution-detail-section"><h4>RR 准入评审</h4><pre>${sol.rr_verdict === 'pass' ? '✅ 通过' : '❌ 不通过'}</pre></div>`;
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
// 猜词游戏
// ============================================

async function startGame() {
    const startScreen = document.getElementById('game-start-screen');
    const playScreen = document.getElementById('game-play-screen');
    const endScreen = document.getElementById('game-end-screen');

    startScreen.style.display = 'none';
    endScreen.style.display = 'none';
    playScreen.style.display = 'flex';

    document.getElementById('game-result').innerHTML = '';
    document.getElementById('game-history-list').innerHTML = '';
    document.getElementById('game-input').value = '';
    document.getElementById('game-hint').textContent = '正在选词...';

    try {
        const result = await api.gameStart();
        state.gameId = result.game_id;
        document.getElementById('game-hint').textContent = result.hint;
        document.getElementById('game-input').focus();
    } catch (err) {
        document.getElementById('game-hint').textContent = '启动失败: ' + err.message;
    }
}

async function submitGuess() {
    const input = document.getElementById('game-input');
    const guess = input.value.trim();
    if (!guess || !state.gameId) return;

    input.value = '';
    const resultDiv = document.getElementById('game-result');
    resultDiv.innerHTML = '<div class="game-thinking">正在计算语义相关度...</div>';

    try {
        const result = await api.gameGuess(state.gameId, guess);
        resultDiv.innerHTML = '';

        if (result.is_correct) {
            // 猜中了
            showGameEnd(true, result.hint, result.history.length);
        } else {
            // 显示概率
            const prob = result.probability;
            const probColor = prob >= 80 ? 'var(--success)' : prob >= 60 ? 'var(--warning)' : prob >= 30 ? 'var(--accent)' : 'var(--danger)';
            resultDiv.innerHTML = `
                <div class="game-prob-display">
                    <div class="game-prob-label">「${escapeHtml(guess)}」的语义相关度</div>
                    <div class="game-prob-bar-container">
                        <div class="game-prob-bar" style="width:${prob}%; background:${probColor}"></div>
                    </div>
                    <div class="game-prob-number" style="color:${probColor}">${prob}%</div>
                    <div class="game-prob-hint">${escapeHtml(result.hint)}</div>
                </div>
            `;
        }

        // 渲染历史
        renderGameHistory(result.history);
    } catch (err) {
        resultDiv.innerHTML = '<div class="game-error">猜测失败: ' + escapeHtml(err.message) + '</div>';
    }
}

function renderGameHistory(history) {
    const list = document.getElementById('game-history-list');
    if (!history || history.length === 0) {
        list.innerHTML = '<div class="game-history-empty">还没有猜测记录</div>';
        return;
    }

    list.innerHTML = history.map((h, i) => {
        const prob = h.probability;
        const color = prob >= 80 ? 'var(--success)' : prob >= 60 ? 'var(--warning)' : prob >= 30 ? 'var(--accent)' : 'var(--danger)';
        return `
            <div class="game-history-item">
                <span class="game-history-rank">#${i + 1}</span>
                <span class="game-history-word">${escapeHtml(h.guess)}</span>
                <div class="game-history-bar-container">
                    <div class="game-history-bar" style="width:${prob}%; background:${color}"></div>
                </div>
                <span class="game-history-prob" style="color:${color}">${prob}%</span>
            </div>
        `;
    }).join('');
}

async function giveupGame() {
    if (!state.gameId) return;
    try {
        const result = await api.gameGiveup(state.gameId);
        showGameEnd(false, `答案是「${result.answer}」`, 0);
    } catch (err) {
        showGameEnd(false, '游戏已结束', 0);
    }
}

function showGameEnd(win, message, attempts) {
    const playScreen = document.getElementById('game-play-screen');
    const endScreen = document.getElementById('game-end-screen');
    const endResult = document.getElementById('game-end-result');

    playScreen.style.display = 'none';
    endScreen.style.display = 'flex';

    if (win) {
        endResult.innerHTML = `
            <div class="game-win">🎉 猜中了！</div>
            <div class="game-end-message">${escapeHtml(message)}</div>
            <div class="game-end-stats">用了 ${attempts} 次猜中</div>
        `;
    } else {
        endResult.innerHTML = `
            <div class="game-lose">😢 没猜中</div>
            <div class="game-end-message">${escapeHtml(message)}</div>
        `;
    }

    state.gameId = null;
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

    // 猜词游戏
    document.getElementById('game-start-btn').addEventListener('click', startGame);
    document.getElementById('game-guess-btn').addEventListener('click', submitGuess);
    document.getElementById('game-giveup-btn').addEventListener('click', giveupGame);
    document.getElementById('game-restart-btn').addEventListener('click', startGame);
    document.getElementById('game-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submitGuess();
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
