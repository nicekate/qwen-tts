/**
 * Qwen-TTS 语音合成服务前端脚本
 * 实现用户交互、API调用、音频播放等功能
 */

class QwenTTSApp {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.loadHistory();
        this.setupSliders();
    }

    initializeElements() {
        // 表单元素
        this.form = document.getElementById('ttsForm');
        this.textArea = document.getElementById('text');
        this.charCount = document.getElementById('charCount');
        this.synthesizeBtn = document.getElementById('synthesizeBtn');
        this.btnText = this.synthesizeBtn.querySelector('.btn-text');
        this.loadingSpinner = this.synthesizeBtn.querySelector('.loading-spinner');
        
        // 高级设置
        this.advancedToggle = document.getElementById('advancedToggle');
        this.advancedSettings = document.getElementById('advancedSettings');
        
        // 滑块元素
        this.speedSlider = document.getElementById('speed');
        this.pitchSlider = document.getElementById('pitch');
        this.volumeSlider = document.getElementById('volume');
        this.speedValue = document.getElementById('speedValue');
        this.pitchValue = document.getElementById('pitchValue');
        this.volumeValue = document.getElementById('volumeValue');
        
        // 结果和历史
        this.resultCard = document.getElementById('resultCard');
        this.resultContent = document.getElementById('resultContent');
        this.historyList = document.getElementById('historyList');
        this.clearHistoryBtn = document.getElementById('clearHistory');
        
        // 通知
        this.notification = document.getElementById('notification');
    }

    bindEvents() {
        // 表单提交
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // 文本计数
        this.textArea.addEventListener('input', () => this.updateCharCount());
        
        // 高级设置切换
        this.advancedToggle.addEventListener('click', () => this.toggleAdvancedSettings());
        
        // 清空历史
        this.clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    setupSliders() {
        // 设置滑块事件监听
        this.speedSlider.addEventListener('input', () => {
            this.speedValue.textContent = this.speedSlider.value + 'x';
        });
        
        this.pitchSlider.addEventListener('input', () => {
            this.pitchValue.textContent = this.pitchSlider.value + 'x';
        });
        
        this.volumeSlider.addEventListener('input', () => {
            this.volumeValue.textContent = this.volumeSlider.value + 'x';
        });
    }

    updateCharCount() {
        const count = this.textArea.value.length;
        this.charCount.textContent = count;
        
        // 字符数警告
        if (count > 800) {
            this.charCount.style.color = 'var(--warning-color)';
        } else if (count > 950) {
            this.charCount.style.color = 'var(--error-color)';
        } else {
            this.charCount.style.color = 'var(--text-secondary)';
        }
    }

    toggleAdvancedSettings() {
        const isOpen = this.advancedSettings.classList.contains('show');
        
        if (isOpen) {
            this.advancedSettings.classList.remove('show');
            this.advancedToggle.classList.remove('active');
        } else {
            this.advancedSettings.classList.add('show');
            this.advancedToggle.classList.add('active');
        }
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const data = {
            text: formData.get('text').trim(),
            voice: formData.get('voice'),
            speed: parseFloat(formData.get('speed')),
            pitch: parseFloat(formData.get('pitch')),
            volume: parseFloat(formData.get('volume'))
        };

        // 验证输入
        if (!data.text) {
            this.showNotification('请输入要合成的文本', 'error');
            return;
        }

        if (data.text.length > 1000) {
            this.showNotification('文本长度不能超过1000字符', 'error');
            return;
        }

        try {
            this.setLoading(true);
            const result = await this.synthesizeSpeech(data);
            
            if (result.success) {
                this.displayResult(result, data);
                this.addToHistory(data, result);
                this.showNotification('语音合成成功！', 'success');
            } else {
                throw new Error(result.message || '合成失败');
            }
        } catch (error) {
            console.error('合成错误:', error);
            this.showNotification(`合成失败: ${error.message}`, 'error');
        } finally {
            this.setLoading(false);
        }
    }

    async synthesizeSpeech(data) {
        const response = await fetch('/api/synthesize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    }

    displayResult(result, requestData) {
        const voiceInfo = result.voice_info;
        const duration = result.duration ? result.duration.toFixed(2) : 'N/A';
        
        this.resultContent.innerHTML = `
            <div class="audio-player">
                <div class="audio-controls">
                    <audio controls class="audio-element" preload="metadata">
                        <source src="${result.audio_url}" type="audio/wav">
                        您的浏览器不支持音频播放。
                    </audio>
                    <a href="/api/download/${result.audio_url.split('/').pop()}" 
                       class="download-btn" download>
                        <i class="fas fa-download"></i>
                        下载音频
                    </a>
                </div>
            </div>
            
            <div class="result-info">
                <div class="info-item">
                    <div class="info-label">音色</div>
                    <div class="info-value">${voiceInfo.name}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">方言</div>
                    <div class="info-value">${voiceInfo.dialect}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">处理时间</div>
                    <div class="info-value">${duration}秒</div>
                </div>
                <div class="info-item">
                    <div class="info-label">文本长度</div>
                    <div class="info-value">${requestData.text.length}字符</div>
                </div>
            </div>
        `;
        
        this.resultCard.style.display = 'block';
        this.resultCard.scrollIntoView({ behavior: 'smooth' });
    }

    addToHistory(requestData, result) {
        const history = this.getHistory();
        const item = {
            id: Date.now(),
            text: requestData.text,
            voice: requestData.voice,
            audioUrl: result.audio_url,
            timestamp: new Date().toLocaleString('zh-CN'),
            voiceInfo: result.voice_info
        };
        
        history.unshift(item);
        
        // 限制历史记录数量
        if (history.length > 20) {
            history.splice(20);
        }
        
        localStorage.setItem('tts_history', JSON.stringify(history));
        this.renderHistory();
    }

    getHistory() {
        try {
            return JSON.parse(localStorage.getItem('tts_history') || '[]');
        } catch {
            return [];
        }
    }

    loadHistory() {
        this.renderHistory();
    }

    renderHistory() {
        const history = this.getHistory();
        
        if (history.length === 0) {
            this.historyList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-clock"></i>
                    <p>暂无历史记录</p>
                </div>
            `;
            return;
        }
        
        this.historyList.innerHTML = history.map(item => `
            <div class="history-item">
                <div class="history-header">
                    <div class="history-text">${this.truncateText(item.text, 100)}</div>
                    <div class="history-voice">${item.voice}</div>
                </div>
                <div class="history-time">${item.timestamp}</div>
                <div class="history-actions">
                    <button class="history-play-btn" onclick="app.playHistoryItem('${item.audioUrl}')">
                        <i class="fas fa-play"></i>
                        播放
                    </button>
                    <a href="/api/download/${item.audioUrl.split('/').pop()}" 
                       class="download-btn btn-small" download>
                        <i class="fas fa-download"></i>
                        下载
                    </a>
                </div>
            </div>
        `).join('');
    }

    playHistoryItem(audioUrl) {
        // 创建临时音频元素播放
        const audio = new Audio(audioUrl);
        audio.play().catch(error => {
            console.error('播放失败:', error);
            this.showNotification('音频播放失败', 'error');
        });
    }

    clearHistory() {
        if (confirm('确定要清空所有历史记录吗？')) {
            localStorage.removeItem('tts_history');
            this.renderHistory();
            this.showNotification('历史记录已清空', 'success');
        }
    }

    setLoading(loading) {
        if (loading) {
            this.synthesizeBtn.classList.add('loading');
            this.synthesizeBtn.disabled = true;
            this.btnText.textContent = '合成中...';
        } else {
            this.synthesizeBtn.classList.remove('loading');
            this.synthesizeBtn.disabled = false;
            this.btnText.textContent = '开始合成';
        }
    }

    showNotification(message, type = 'success') {
        this.notification.textContent = message;
        this.notification.className = `notification ${type}`;
        this.notification.classList.add('show');
        
        setTimeout(() => {
            this.notification.classList.remove('show');
        }, 3000);
    }

    truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    handleKeyboard(e) {
        // Ctrl/Cmd + Enter 快速合成
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!this.synthesizeBtn.disabled) {
                this.form.dispatchEvent(new Event('submit'));
            }
        }
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new QwenTTSApp();
});
