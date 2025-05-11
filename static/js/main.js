// 获取CSRF令牌
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 自动关闭警告消息
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 文件上传预览
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || '未选择文件';
            const fileLabel = input.nextElementSibling;
            if (fileLabel && fileLabel.classList.contains('form-file-label')) {
                fileLabel.textContent = fileName;
            }
        });
    });

    // 表格排序功能
    const sortableTables = document.querySelectorAll('.sortable');
    sortableTables.forEach(function(table) {
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(function(header) {
            header.addEventListener('click', function() {
                const sortKey = this.dataset.sort;
                const sortDirection = this.classList.contains('sort-asc') ? 'desc' : 'asc';

                // 清除所有排序状态
                headers.forEach(h => {
                    h.classList.remove('sort-asc', 'sort-desc');
                    h.querySelector('.sort-icon')?.remove();
                });

                // 设置当前排序状态
                this.classList.add(`sort-${sortDirection}`);
                const icon = document.createElement('span');
                icon.className = `sort-icon bi bi-arrow-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`;
                this.appendChild(icon);

                // 执行排序
                sortTable(table, sortKey, sortDirection);
            });
        });
    });

    // 确认操作
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // 版本号格式验证
    const versionInputs = document.querySelectorAll('input[data-validate="version"]');
    versionInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            const value = this.value.trim();
            const isValid = /^\d{3}\.\d{3}\.\d{3}$/.test(value);

            if (value && !isValid) {
                this.classList.add('is-invalid');

                // 添加错误提示
                let feedback = this.nextElementSibling;
                if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                    feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    this.parentNode.appendChild(feedback);
                }
                feedback.textContent = '请使用格式: xxx.yyy.zzz（例如: 001.000.001）';
            } else {
                this.classList.remove('is-invalid');
            }
        });
    });

    // IMEI格式验证
    const imeiInputs = document.querySelectorAll('input[data-validate="imei"]');
    imeiInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            const value = this.value.trim();
            const isValid = /^\d{15}$/.test(value);

            if (value && !isValid) {
                this.classList.add('is-invalid');

                // 添加错误提示
                let feedback = this.nextElementSibling;
                if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                    feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    this.parentNode.appendChild(feedback);
                }
                feedback.textContent = 'IMEI应为15位数字';
            } else {
                this.classList.remove('is-invalid');
            }
        });
    });
});

// 表格排序函数
function sortTable(table, key, direction) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // 排序行
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td[data-sort-value="${key}"]`)?.dataset.sortValue ||
                      a.querySelector(`td:nth-child(${parseInt(key) + 1})`)?.textContent.trim();
        const bValue = b.querySelector(`td[data-sort-value="${key}"]`)?.dataset.sortValue ||
                      b.querySelector(`td:nth-child(${parseInt(key) + 1})`)?.textContent.trim();

        // 数字排序
        if (!isNaN(aValue) && !isNaN(bValue)) {
            return direction === 'asc' ? aValue - bValue : bValue - aValue;
        }

        // 日期排序
        const aDate = new Date(aValue);
        const bDate = new Date(bValue);
        if (!isNaN(aDate) && !isNaN(bDate)) {
            return direction === 'asc' ? aDate - bDate : bDate - aDate;
        }

        // 字符串排序
        return direction === 'asc' ?
            aValue.localeCompare(bValue, 'zh-CN') :
            bValue.localeCompare(aValue, 'zh-CN');
    });

    // 重新添加排序后的行
    rows.forEach(row => tbody.appendChild(row));
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 版本比较函数
function compareVersions(v1, v2) {
    const parts1 = v1.split('.').map(Number);
    const parts2 = v2.split('.').map(Number);

    for (let i = 0; i < parts1.length; i++) {
        if (parts1[i] > parts2[i]) return 1;
        if (parts1[i] < parts2[i]) return -1;
    }

    return 0;
}

// 图表处理函数
function setupChartResponsiveness(chartInstance, chartId) {
    if (!chartInstance || !chartId) return;

    // 获取图表容器
    const canvas = document.getElementById(chartId);
    if (!canvas) return;

    // 立即调整大小
    function resizeChart() {
        if (chartInstance) {
            // 确保图表不会超出容器
            const parentHeight = canvas.parentElement.clientHeight;

            // 设置最大尺寸
            canvas.style.maxWidth = '100%';
            canvas.style.maxHeight = parentHeight + 'px';

            // 重新渲染图表
            chartInstance.resize();
        }
    }

    // 初始调整
    resizeChart();

    // 设置观察器监听容器大小变化
    if (window.ResizeObserver) {
        const resizeObserver = new ResizeObserver(() => {
            resizeChart();
        });

        // 观察canvas的父元素
        if (canvas.parentElement) {
            resizeObserver.observe(canvas.parentElement);
        }
    }

    // 添加窗口大小变化监听
    window.addEventListener('resize', resizeChart);
}
