/**
 * Qwen-TTS 语音合成服务前端脚本
 * 实现用户交互、API调用、音频播放等功能
 */

class QwenTTSApp {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.loadHistory();
        this.currentTaskId = null;
        this.progressInterval = null;
    }

    initializeElements() {
        // 标签页元素
        this.tabButtons = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');

        // 单个合成表单元素
        this.form = document.getElementById('ttsForm');
        this.textArea = document.getElementById('text');
        this.charCount = document.getElementById('charCount');
        this.synthesizeBtn = document.getElementById('synthesizeBtn');
        this.btnText = this.synthesizeBtn.querySelector('.btn-text');
        this.loadingSpinner = this.synthesizeBtn.querySelector('.loading-spinner');

        // 批量处理元素
        this.batchForm = document.getElementById('batchForm');
        this.fileUploadArea = document.getElementById('fileUploadArea');
        this.fileInput = document.getElementById('batchFile');
        this.fileInfo = document.getElementById('fileInfo');
        this.batchSubmitBtn = document.getElementById('batchSubmitBtn');
        this.batchProgressCard = document.getElementById('batchProgressCard');
        this.batchResultsCard = document.getElementById('batchResultsCard');
        this.downloadAllBtn = document.getElementById('downloadAllBtn');

        // 进度元素
        this.progressText = document.getElementById('progressText');
        this.progressPercentage = document.getElementById('progressPercentage');
        this.progressFill = document.getElementById('progressFill');
        this.totalSegments = document.getElementById('totalSegments');
        this.completedSegments = document.getElementById('completedSegments');
        this.failedSegments = document.getElementById('failedSegments');
        this.batchResultsList = document.getElementById('batchResultsList');

        // 结果和历史
        this.resultCard = document.getElementById('resultCard');
        this.resultContent = document.getElementById('resultContent');
        this.historyList = document.getElementById('historyList');
        this.clearHistoryBtn = document.getElementById('clearHistory');
        this.historySection = document.querySelector('.history-section');

        // 通知
        this.notification = document.getElementById('notification');
    }

    bindEvents() {
        // 表单提交
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // 文本计数
        this.textArea.addEventListener('input', () => this.updateCharCount());

        // 标签页切换
        this.tabButtons.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        // 批量处理表单提交
        if (this.batchForm) {
            this.batchForm.addEventListener('submit', (e) => this.handleBatchSubmit(e));
        }

        // 文件上传相关事件
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        if (this.fileUploadArea) {
            this.fileUploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
            this.fileUploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
            this.fileUploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        }

        // 批量下载按钮
        if (this.downloadAllBtn) {
            this.downloadAllBtn.addEventListener('click', () => this.handleDownloadAll());
        }

        // 清空历史
        this.clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        
        // 键盘快捷键
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
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



    async handleSubmit(e) {
        e.preventDefault();
        
        const formData = new FormData(this.form);
        const data = {
            text: formData.get('text').trim(),
            voice: formData.get('voice')
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
        // 检查当前是否在批量处理模式
        const currentTab = document.querySelector('.tab-btn.active')?.dataset.tab;
        if (currentTab === 'batch') {
            // 在批量处理模式下，不显示单个合成结果
            return;
        }

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

    // 标签页切换
    switchTab(tabName) {
        // 更新按钮状态
        this.tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // 更新内容显示
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        // 根据标签页隐藏/显示相关区域
        if (tabName === 'batch') {
            // 切换到批量处理时，隐藏单个合成的结果区域和历史记录
            if (this.resultCard) {
                this.resultCard.style.display = 'none';
            }
            if (this.historySection) {
                this.historySection.style.display = 'none';
            }
        } else if (tabName === 'single') {
            // 切换到单个合成时，隐藏批量处理的结果区域，显示历史记录
            if (this.batchProgressCard) {
                this.batchProgressCard.style.display = 'none';
            }
            if (this.batchResultsCard) {
                this.batchResultsCard.style.display = 'none';
            }
            if (this.historySection) {
                this.historySection.style.display = 'block';
            }
        }
    }

    // 文件选择处理
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.displayFileInfo(file);
        }
    }

    // 拖拽处理
    handleDragOver(e) {
        e.preventDefault();
        this.fileUploadArea.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.fileUploadArea.classList.remove('dragover');
    }

    handleFileDrop(e) {
        e.preventDefault();
        this.fileUploadArea.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.name.toLowerCase().endsWith('.txt') || file.name.toLowerCase().endsWith('.md')) {
                this.fileInput.files = files;
                this.displayFileInfo(file);
            } else {
                this.showNotification('只支持 .txt 和 .md 文件', 'error');
            }
        }
    }

    // 显示文件信息
    displayFileInfo(file) {
        const fileName = this.fileInfo.querySelector('.file-name');
        const fileSize = this.fileInfo.querySelector('.file-size');

        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);

        this.fileInfo.style.display = 'flex';
        this.fileUploadArea.querySelector('.file-upload-content').style.display = 'none';
    }

    // 格式化文件大小
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 批量处理表单提交
    async handleBatchSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.batchForm);

        if (!this.fileInput.files[0]) {
            this.showNotification('请选择要上传的文件', 'error');
            return;
        }

        try {
            this.setBatchLoading(true);

            const response = await fetch('/api/batch/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.currentTaskId = result.task_id;
                this.showBatchProgress(result.total_segments);
                this.startProgressPolling();
                this.showNotification('文件上传成功，开始批量处理', 'success');
            } else {
                throw new Error(result.message || '批量处理失败');
            }

        } catch (error) {
            console.error('批量处理错误:', error);
            this.showNotification(`批量处理失败: ${error.message}`, 'error');
        } finally {
            this.setBatchLoading(false);
        }
    }

    // 设置批量处理加载状态
    setBatchLoading(loading) {
        if (loading) {
            this.batchSubmitBtn.classList.add('loading');
            this.batchSubmitBtn.disabled = true;
            this.batchSubmitBtn.querySelector('.btn-text').textContent = '处理中...';
        } else {
            this.batchSubmitBtn.classList.remove('loading');
            this.batchSubmitBtn.disabled = false;
            this.batchSubmitBtn.querySelector('.btn-text').textContent = '开始批量处理';
        }
    }

    // 显示批量处理进度
    showBatchProgress(totalSegments) {
        // 确保隐藏单个合成的结果区域和历史记录
        if (this.resultCard) {
            this.resultCard.style.display = 'none';
        }
        if (this.historySection) {
            this.historySection.style.display = 'none';
        }

        this.batchProgressCard.style.display = 'block';
        this.totalSegments.textContent = totalSegments;
        this.completedSegments.textContent = '0';
        this.failedSegments.textContent = '0';
        this.progressFill.style.width = '0%';
        this.progressPercentage.textContent = '0%';
        this.progressText.textContent = '开始处理...';

        // 平滑滚动到进度区域，而不是跳转到顶部
        setTimeout(() => {
            this.batchProgressCard.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest'
            });
        }, 100);
    }

    // 开始进度轮询
    startProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/batch/status/${this.currentTaskId}`);
                if (response.ok) {
                    const task = await response.json();
                    this.updateProgress(task);

                    if (task.status === 'completed' || task.status === 'failed') {
                        clearInterval(this.progressInterval);
                        this.showBatchResults(task);
                    }
                }
            } catch (error) {
                console.error('获取进度失败:', error);
            }
        }, 2000); // 每2秒更新一次
    }

    // 更新进度显示
    updateProgress(task) {
        this.completedSegments.textContent = task.completed_segments;
        this.failedSegments.textContent = task.failed_segments;
        this.progressFill.style.width = `${task.progress_percentage}%`;
        this.progressPercentage.textContent = `${Math.round(task.progress_percentage)}%`;

        if (task.status === 'processing') {
            this.progressText.textContent = '正在处理...';
        } else if (task.status === 'completed') {
            this.progressText.textContent = '处理完成';
        } else if (task.status === 'failed') {
            this.progressText.textContent = '处理失败';
        }
    }

    // 显示批量处理结果
    showBatchResults(task) {
        // 确保隐藏单个合成的结果区域和历史记录
        if (this.resultCard) {
            this.resultCard.style.display = 'none';
        }
        if (this.historySection) {
            this.historySection.style.display = 'none';
        }

        this.batchResultsCard.style.display = 'block';

        const resultsHtml = task.results.map(result => `
            <div class="batch-result-item ${result.status}">
                <div class="result-header">
                    <div class="result-text">${result.text}</div>
                    <div class="result-status ${result.status}">
                        ${result.status === 'success' ? '成功' : '失败'}
                    </div>
                </div>
                ${result.status === 'success' ? `
                    <div class="result-actions">
                        <button class="history-play-btn" onclick="app.playAudio('${result.audio_url}')">
                            <i class="fas fa-play"></i>
                            播放
                        </button>
                        <a href="/api/download/${result.filename}" class="download-btn btn-small" download>
                            <i class="fas fa-download"></i>
                            下载
                        </a>
                    </div>
                ` : `
                    <div class="error-message">${result.error}</div>
                `}
            </div>
        `).join('');

        this.batchResultsList.innerHTML = resultsHtml;

        // 平滑滚动到结果区域
        setTimeout(() => {
            this.batchResultsCard.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest'
            });
        }, 100);

        // 显示完成通知
        const successCount = task.completed_segments;
        const failedCount = task.failed_segments;
        this.showNotification(
            `批量处理完成！成功: ${successCount}, 失败: ${failedCount}`,
            failedCount === 0 ? 'success' : 'warning'
        );
    }

    // 播放音频
    playAudio(audioUrl) {
        const audio = new Audio(audioUrl);
        audio.play().catch(error => {
            console.error('播放失败:', error);
            this.showNotification('音频播放失败', 'error');
        });
    }

    // 批量下载所有音频文件
    async handleDownloadAll() {
        if (!this.currentTaskId) {
            this.showNotification('没有可下载的文件', 'error');
            return;
        }

        try {
            // 获取任务状态和结果
            const response = await fetch(`/api/batch/status/${this.currentTaskId}`);
            if (!response.ok) {
                throw new Error('获取任务状态失败');
            }

            const task = await response.json();
            const successResults = task.results.filter(result => result.status === 'success');

            if (successResults.length === 0) {
                this.showNotification('没有成功的音频文件可下载', 'warning');
                return;
            }

            // 显示下载选项
            const choice = await this.showDownloadChoice(successResults.length);

            if (choice === 'zip') {
                // ZIP打包下载
                await this.downloadAsZip();
            } else if (choice === 'individual') {
                // 逐个下载
                await this.downloadIndividually(successResults);
            }

        } catch (error) {
            console.error('批量下载失败:', error);
            this.showNotification(`批量下载失败: ${error.message}`, 'error');
        }
    }

    // 显示下载选项对话框
    async showDownloadChoice(fileCount) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'download-modal';
            modal.innerHTML = `
                <div class="download-modal-content">
                    <h3>选择下载方式</h3>
                    <p>共有 ${fileCount} 个音频文件可下载</p>
                    <div class="download-options">
                        <button class="btn-primary" data-choice="zip">
                            <i class="fas fa-file-archive"></i>
                            打包下载 (ZIP)
                        </button>
                        <button class="btn-secondary" data-choice="individual">
                            <i class="fas fa-download"></i>
                            逐个下载
                        </button>
                        <button class="btn-cancel" data-choice="cancel">
                            <i class="fas fa-times"></i>
                            取消
                        </button>
                    </div>
                </div>
            `;

            // 添加样式
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            const content = modal.querySelector('.download-modal-content');
            content.style.cssText = `
                background: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                max-width: 400px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            `;

            const options = modal.querySelector('.download-options');
            options.style.cssText = `
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-top: 20px;
            `;

            // 绑定事件
            modal.addEventListener('click', (e) => {
                if (e.target.hasAttribute('data-choice')) {
                    const choice = e.target.getAttribute('data-choice');
                    document.body.removeChild(modal);
                    resolve(choice);
                }
            });

            document.body.appendChild(modal);
        });
    }

    // ZIP打包下载
    async downloadAsZip() {
        try {
            this.showNotification('正在生成ZIP文件...', 'success');

            // 创建下载链接
            const link = document.createElement('a');
            link.href = `/api/batch/download/${this.currentTaskId}`;
            link.style.display = 'none';

            // 添加到页面并触发下载
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            this.showNotification('ZIP文件下载已开始', 'success');

        } catch (error) {
            console.error('ZIP下载失败:', error);
            this.showNotification(`ZIP下载失败: ${error.message}`, 'error');
        }
    }

    // 逐个下载文件
    async downloadIndividually(successResults) {
        try {
            this.showNotification(`开始下载 ${successResults.length} 个音频文件...`, 'success');

            let downloadCount = 0;
            for (const result of successResults) {
                try {
                    // 创建下载链接
                    const link = document.createElement('a');
                    link.href = `/api/download/${result.filename}`;
                    link.download = result.filename;
                    link.style.display = 'none';

                    // 添加到页面并触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);

                    downloadCount++;

                    // 添加延迟避免浏览器阻止多个下载
                    if (downloadCount < successResults.length) {
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                } catch (error) {
                    console.error(`下载文件 ${result.filename} 失败:`, error);
                }
            }

            this.showNotification(`批量下载完成！已下载 ${downloadCount} 个文件`, 'success');

        } catch (error) {
            console.error('逐个下载失败:', error);
            this.showNotification(`下载失败: ${error.message}`, 'error');
        }
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new QwenTTSApp();
});
