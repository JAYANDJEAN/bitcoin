/**
 * 比特币系统前端JavaScript
 * 提供通用的交互功能和API调用
 */

// 全局配置
const CONFIG = {
    refreshInterval: 5000, // 5秒刷新间隔
    apiTimeout: 30000, // API超时时间
    maxLogEntries: 100, // 最大日志条目数
    animationDuration: 300 // 动画持续时间
};

// API缓存机制
class APICache {
    constructor() {
        this.cache = new Map();
        this.pendingRequests = new Map();
    }

    // 获取缓存的API响应
    get(url, maxAge = 3000) {
        const cached = this.cache.get(url);
        if (cached && (Date.now() - cached.timestamp < maxAge)) {
            return Promise.resolve(cached.data);
        }
        return null;
    }

    // 设置缓存
    set(url, data) {
        this.cache.set(url, {
            data: data,
            timestamp: Date.now()
        });
    }

    // 防止重复请求
    async getOrFetch(url, fetchFn, maxAge = 3000) {
        // 先检查缓存
        const cached = this.get(url, maxAge);
        if (cached) {
            return cached;
        }

        // 检查是否有正在进行的请求
        if (this.pendingRequests.has(url)) {
            return this.pendingRequests.get(url);
        }

        // 发起新请求
        const promise = fetchFn().then(data => {
            this.set(url, data);
            this.pendingRequests.delete(url);
            return data;
        }).catch(error => {
            this.pendingRequests.delete(url);
            throw error;
        });

        this.pendingRequests.set(url, promise);
        return promise;
    }
}

// 应用主对象
const BitcoinApp = {
    // 初始化应用
    init() {
        this.apiCache = new APICache();
        this.setupEventListeners();
        this.initializeTooltips();
        this.startPeriodicUpdates();
        this.highlightActiveNavItem();
        console.log('🚀 比特币系统前端已初始化');
    },

    // 设置事件监听器
    setupEventListeners() {
        // 页面加载完成
        document.addEventListener('DOMContentLoaded', () => {
            this.fadeInElements();
        });

        // 表单验证
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                }
            });
        });

        // 模态框事件
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('hidden.bs.modal', () => {
                this.clearModalForms(modal);
            });
        });

        // 自动隐藏警告框
        document.querySelectorAll('.alert').forEach(alert => {
            if (alert.classList.contains('alert-dismissible')) {
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 8000);
            }
        });
    },

    // 初始化工具提示
    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    // 开始周期性更新
    startPeriodicUpdates() {
        // 合并更新区块链统计信息和网络状态
        this.updateAllStats();
        setInterval(() => {
            this.updateAllStats();
        }, CONFIG.refreshInterval);
    },

    // 高亮当前导航项
    highlightActiveNavItem() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPath || (currentPath !== '/' && href !== '/' && currentPath.startsWith(href))) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    },

    // 淡入动画
    fadeInElements() {
        const elements = document.querySelectorAll('.card, .alert, .btn');
        elements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            setTimeout(() => {
                element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 100);
        });
    },

    // 表单验证
    validateForm(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showFieldError(input, '此字段为必填项');
                isValid = false;
            } else {
                this.clearFieldError(input);
            }
        });

        return isValid;
    },

    // 显示字段错误
    showFieldError(field, message) {
        field.classList.add('is-invalid');

        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    },

    // 清除字段错误
    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    },

    // 清除模态框表单
    clearModalForms(modal) {
        const forms = modal.querySelectorAll('form');
        forms.forEach(form => {
            form.reset();
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                this.clearFieldError(input);
            });
        });
    },

    // 合并更新所有统计信息
    updateAllStats() {
        const fetchStats = () => this.apiCall('/api/blockchain_stats');

        this.apiCache.getOrFetch('/api/blockchain_stats', fetchStats, 2000)
            .then(data => {
                this.updateStatsDisplay(data);
            })
            .catch(error => {
                console.error('更新统计信息失败:', error);
            });
    },

    // 更新区块链统计信息
    updateBlockchainStats() {
        // 保留此方法以维持向后兼容性
        this.updateAllStats();
    },



    // 更新统计显示
    updateStatsDisplay(data) {
        const updates = [
            { selector: '.stats-height', value: data.height || 0 },
            { selector: '.stats-difficulty', value: data.difficulty || 0 },
            { selector: '.stats-pending', value: data.pending_transactions || 0 },
            { selector: '#currentDifficulty', value: data.difficulty || 'N/A' },
            { selector: '#latestBlock', value: `#${data.height || 0}` },
            { selector: '#pendingTx', value: data.pending_transactions || 0 }
        ];

        updates.forEach(update => {
            const element = document.querySelector(update.selector);
            if (element) {
                element.textContent = update.value;
            }
        });
    },

    // API调用封装
    apiCall(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: CONFIG.apiTimeout
        };

        const finalOptions = { ...defaultOptions, ...options };

        return fetch(url, finalOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('API调用失败:', error);
                throw error;
            });
    },

    // jQuery兼容的AJAX调用封装
    ajaxCall(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            contentType: 'application/json',
            timeout: CONFIG.apiTimeout,
            success: function (response) {
                console.log('API调用成功:', response);
            },
            error: function (xhr, status, error) {
                console.error('API调用失败:', error);
                const response = xhr.responseJSON;
                const errorMsg = response ? response.error : '未知错误';
                showNotification('操作失败: ' + errorMsg, 'danger');
            }
        };

        const finalOptions = { ...defaultOptions, ...options };
        return $.ajax(url, finalOptions);
    },

    // 统一的确认对话框
    confirmAction(message, callback, title = '确认操作') {
        if (confirm(`${title}\n\n${message}`)) {
            if (callback) callback();
            return true;
        }
        return false;
    },

    // 显示通知
    showNotification(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
        `;

        alertDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${this.getIconForType(type)} me-2"></i>
                <div>${message}</div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alertDiv);

        // 自动移除
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => alertDiv.remove(), 300);
            }
        }, duration);
    },

    // 获取类型对应的图标
    getIconForType(type) {
        const icons = {
            success: 'check-circle',
            danger: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },

    // 复制到剪贴板
    copyToClipboard(text, successMessage = '已复制到剪贴板') {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text)
                .then(() => this.showNotification(successMessage, 'success'))
                .catch(() => this.fallbackCopy(text, successMessage));
        } else {
            this.fallbackCopy(text, successMessage);
        }
    },

    // 备用复制方法
    fallbackCopy(text, successMessage) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '0';
        textArea.style.left = '0';
        textArea.style.width = '1px';
        textArea.style.height = '1px';
        textArea.style.padding = '0';
        textArea.style.border = 'none';
        textArea.style.outline = 'none';
        textArea.style.boxShadow = 'none';
        textArea.style.background = 'transparent';

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
            this.showNotification(successMessage, 'success');
        } catch (err) {
            this.showNotification('复制失败，请手动复制', 'danger');
        }

        document.body.removeChild(textArea);
    },

    // 格式化时间
    formatDateTime(timestamp) {
        try {
            const date = new Date(parseFloat(timestamp) * 1000);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            return timestamp;
        }
    },

    // 格式化哈希
    formatHash(hash, length = 16) {
        if (!hash || hash.length <= length) return hash;
        return `${hash.substring(0, length)}...`;
    },

    // 格式化数字
    formatNumber(num, decimals = 4) {
        if (typeof num !== 'number') return '0.0000';
        return num.toFixed(decimals);
    },

    // 显示加载状态
    showLoading(element, text = '加载中...') {
        const originalContent = element.innerHTML;
        element.innerHTML = `
            <i class="fas fa-spinner fa-spin me-2"></i>
            ${text}
        `;
        element.disabled = true;

        return () => {
            element.innerHTML = originalContent;
            element.disabled = false;
        };
    },

    // 确认对话框
    confirm(message, title = '确认', callback) {
        const result = window.confirm(`${title}\n\n${message}`);
        if (result && callback) {
            callback();
        }
        return result;
    },

    // 动态添加CSS类
    addTempClass(element, className, duration = 2000) {
        element.classList.add(className);
        setTimeout(() => {
            element.classList.remove(className);
        }, duration);
    },

    // 滚动到元素
    scrollToElement(element, offset = 0) {
        const elementPosition = element.offsetTop - offset;
        window.scrollTo({
            top: elementPosition,
            behavior: 'smooth'
        });
    },

    // 防抖函数
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 节流函数
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// 全局工具函数
window.BitcoinApp = BitcoinApp;

// 便捷函数
window.showNotification = (message, type, duration) => {
    BitcoinApp.showNotification(message, type, duration);
};

window.copyToClipboard = (text, message) => {
    BitcoinApp.copyToClipboard(text, message);
};

window.formatDateTime = (timestamp) => {
    return BitcoinApp.formatDateTime(timestamp);
};

window.formatHash = (hash, length) => {
    return BitcoinApp.formatHash(hash, length);
};

window.formatNumber = (num, decimals) => {
    return BitcoinApp.formatNumber(num, decimals);
};

window.ajaxCall = (url, options) => {
    return BitcoinApp.ajaxCall(url, options);
};

window.confirmAction = (message, callback, title) => {
    return BitcoinApp.confirmAction(message, callback, title);
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    BitcoinApp.init();
});

// 添加自定义CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .animate-pulse {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    .animate-spin {
        animation: spin 1s linear infinite;
    }
    
    .animate-bounce {
        animation: bounce 1s infinite;
    }
    
    @keyframes bounce {
        0%, 20%, 53%, 80%, 100% {
            animation-timing-function: cubic-bezier(0.215, 0.610, 0.355, 1.000);
            transform: translate3d(0,0,0);
        }
        40%, 43% {
            animation-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
            transform: translate3d(0, -30px, 0);
        }
        70% {
            animation-timing-function: cubic-bezier(0.755, 0.050, 0.855, 0.060);
            transform: translate3d(0, -15px, 0);
        }
        90% {
            transform: translate3d(0,-4px,0);
        }
    }
`;
document.head.appendChild(style);

// 导出模块（如果需要的话）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BitcoinApp;
} 