/* ================================
   DashStack Admin JavaScript
   Modern Admin Dashboard Functions
   ================================ */

// Global admin object
const DashStackAdmin = {
    // Configuration
    config: {
        sidebarBreakpoint: 992,
        animationDuration: 300
    },

    // Initialize the admin dashboard
    init() {
        this.setupSidebar();
        this.setupSearch();
        this.setupNotifications();
        this.setupTooltips();
        this.setupAnimations();
        this.setupTheme();
        
        console.log('DashStack Admin Dashboard Initialized ✨');
    },

    // Sidebar functionality
    setupSidebar() {
        const sidebar = document.getElementById('sidebar');
        const sidebarBackdrop = document.getElementById('sidebarBackdrop');
        
        // Mobile sidebar toggle
        window.toggleSidebar = () => {
            if (window.innerWidth < this.config.sidebarBreakpoint) {
                sidebar.classList.toggle('show');
                sidebarBackdrop.classList.toggle('show');
                document.body.classList.toggle('sidebar-open');
            }
        };

        // Close sidebar
        window.closeSidebar = () => {
            sidebar.classList.remove('show');
            sidebarBackdrop.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        };

        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth >= this.config.sidebarBreakpoint) {
                window.closeSidebar();
            }
        });

        // Auto-close sidebar on route change (mobile)
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < this.config.sidebarBreakpoint) {
                    setTimeout(() => this.closeSidebar(), 100);
                }
            });
        });

        // Smooth active state transitions
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('mouseenter', function() {
                if (!this.classList.contains('active')) {
                    this.style.transform = 'translateX(4px)';
                }
            });

            link.addEventListener('mouseleave', function() {
                if (!this.classList.contains('active')) {
                    this.style.transform = 'translateX(0)';
                }
            });
        });
    },

    // Global search functionality
    setupSearch() {
        const searchInput = document.getElementById('globalSearch');
        if (!searchInput) return;

        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();
            
            if (query.length > 2) {
                searchTimeout = setTimeout(() => {
                    this.performSearch(query);
                }, 300);
            }
        });

        // Search keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for quick search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }

            // Escape to clear search
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.value = '';
                searchInput.blur();
            }
        });
    },

    // Perform search functionality
    performSearch(query) {
        // Mock search results - replace with actual search API
        console.log('Searching for:', query);
        
        // Example: search navigation items
        const navItems = document.querySelectorAll('.nav-link');
        navItems.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(query.toLowerCase())) {
                item.classList.add('search-highlight');
                setTimeout(() => item.classList.remove('search-highlight'), 2000);
            }
        });
    },

    // Notification system
    setupNotifications() {
        // Auto-hide alerts
        document.querySelectorAll('.alert').forEach(alert => {
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-10px)';
                    setTimeout(() => alert.remove(), this.config.animationDuration);
                }
            }, 5000);
        });

        // Notification badge animation
        const notificationBadge = document.querySelector('.notification-badge');
        if (notificationBadge) {
            setInterval(() => {
                notificationBadge.style.animation = 'pulse 1s ease-in-out';
                setTimeout(() => {
                    notificationBadge.style.animation = '';
                }, 1000);
            }, 10000);
        }

        // Mark notifications as read
        document.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', function() {
                this.style.opacity = '0.7';
                this.classList.add('read');
            });
        });
    },

    // Setup tooltips
    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(
            document.querySelectorAll('[data-bs-toggle="tooltip"], [title]')
        );
        
        tooltipTriggerList.forEach(tooltipTriggerEl => {
            if (tooltipTriggerEl.title && !tooltipTriggerEl.getAttribute('data-bs-toggle')) {
                tooltipTriggerEl.setAttribute('data-bs-toggle', 'tooltip');
            }
        });

        // Auto-enable tooltips for action buttons
        document.querySelectorAll('.btn[title], .action-buttons .btn').forEach(btn => {
            if (!btn.getAttribute('data-bs-toggle')) {
                btn.setAttribute('data-bs-toggle', 'tooltip');
                btn.setAttribute('data-bs-placement', 'top');
            }
        });
    },

    // Animation setup
    setupAnimations() {
        // Intersection Observer for fade-in animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe cards and sections
        document.querySelectorAll('.stats-card, .chart-card, .activity-card, .table-card').forEach(el => {
            observer.observe(el);
        });

        // Stagger animation for stats cards
        document.querySelectorAll('.stats-card').forEach((card, index) => {
            card.style.animationDelay = `${index * 100}ms`;
        });

        // Hover effects for interactive elements
        document.querySelectorAll('.stats-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px) scale(1.02)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    },

    // Theme management
    setupTheme() {
        // Auto-detect system theme preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
        }

        // Listen for theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const theme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });

        // Apply saved theme
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
    },

    // Utility functions
    utils: {
        // Format numbers with separators
        formatNumber(num) {
            return new Intl.NumberFormat('vi-VN').format(num);
        },

        // Format currency
        formatCurrency(amount) {
            return new Intl.NumberFormat('vi-VN', {
                style: 'currency',
                currency: 'VND'
            }).format(amount);
        },

        // Format date
        formatDate(date) {
            return new Intl.DateTimeFormat('vi-VN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            }).format(new Date(date));
        },

        // Show loading state
        showLoading(element) {
            element.classList.add('loading');
            element.style.pointerEvents = 'none';
        },

        // Hide loading state
        hideLoading(element) {
            element.classList.remove('loading');
            element.style.pointerEvents = 'auto';
        },

        // Show toast notification
        showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
            toast.style.zIndex = '9999';
            toast.innerHTML = `
                ${message}
                <button type="button" class="btn-close ms-2" onclick="this.parentElement.remove()"></button>
            `;
            
            document.body.appendChild(toast);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 300);
                }
            }, 5000);
        },

        // Confirm dialog
        confirm(message, callback) {
            if (window.confirm(message)) {
                callback();
            }
        },

        // Copy to clipboard
        async copyToClipboard(text) {
            try {
                await navigator.clipboard.writeText(text);
                this.showToast('Đã sao chép vào clipboard', 'success');
            } catch (err) {
                this.showToast('Không thể sao chép', 'error');
            }
        }
    },

    // Data management functions
    data: {
        // Generic AJAX request handler
        async request(url, options = {}) {
            const defaults = {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'  // Include session cookies
            };

            try {
                const response = await fetch(url, { ...defaults, ...options });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error('Request failed:', error);
                DashStackAdmin.utils.showToast('Đã xảy ra lỗi khi tải dữ liệu', 'danger');
                throw error;
            }
        },

        // Load dashboard stats
        async loadDashboardStats() {
            try {
                const stats = await this.request('/admin/api/stats');
                this.updateStatsCards(stats);
            } catch (error) {
                console.error('Failed to load dashboard stats:', error);
            }
        },

        // Update stats cards with new data
        updateStatsCards(stats) {
            Object.keys(stats).forEach(key => {
                const element = document.querySelector(`[data-stat="${key}"]`);
                if (element) {
                    element.textContent = DashStackAdmin.utils.formatNumber(stats[key]);
                    element.classList.add('updated');
                    setTimeout(() => element.classList.remove('updated'), 1000);
                }
            });
        }
    }
};

// Table management
class DataTable {
    constructor(tableSelector, options = {}) {
        this.table = document.querySelector(tableSelector);
        this.options = {
            sortable: true,
            searchable: true,
            pagination: true,
            pageSize: 10,
            ...options
        };
        
        if (this.table) {
            this.init();
        }
    }

    init() {
        if (this.options.sortable) this.setupSorting();
        if (this.options.searchable) this.setupSearch();
        if (this.options.pagination) this.setupPagination();
        
        // Setup row actions
        this.setupRowActions();
    }

    setupSorting() {
        this.table.querySelectorAll('th[data-sortable]').forEach(th => {
            th.style.cursor = 'pointer';
            th.addEventListener('click', () => {
                this.sortTable(th.dataset.sortable, th.dataset.sortDir !== 'desc');
            });
        });
    }

    setupSearch() {
        const searchInput = this.table.parentElement.querySelector('.table-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTable(e.target.value);
            });
        }
    }

    setupRowActions() {
        this.table.addEventListener('click', (e) => {
            const action = e.target.closest('[data-action]');
            if (action) {
                e.preventDefault();
                this.handleRowAction(action.dataset.action, action);
            }
        });
    }

    handleRowAction(action, element) {
        const row = element.closest('tr');
        const id = row.dataset.id;

        switch (action) {
            case 'edit':
                this.editRow(id, row);
                break;
            case 'delete':
                this.deleteRow(id, row);
                break;
            case 'view':
                this.viewRow(id, row);
                break;
            default:
                console.log(`Unknown action: ${action}`);
        }
    }

    editRow(id, row) {
        DashStackAdmin.utils.showToast('Chức năng chỉnh sửa đang được phát triển', 'info');
    }

    deleteRow(id, row) {
        DashStackAdmin.utils.confirm('Bạn có chắc chắn muốn xóa?', () => {
            row.style.opacity = '0';
            setTimeout(() => row.remove(), 300);
            DashStackAdmin.utils.showToast('Đã xóa thành công', 'success');
        });
    }

    viewRow(id, row) {
        DashStackAdmin.utils.showToast('Chức năng xem chi tiết đang được phát triển', 'info');
    }

    sortTable(column, ascending = true) {
        // Implementation for table sorting
        console.log(`Sorting by ${column}, ascending: ${ascending}`);
    }

    filterTable(query) {
        const rows = this.table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const visible = text.includes(query.toLowerCase());
            row.style.display = visible ? '' : 'none';
        });
    }
}

// Form management
class AdminForm {
    constructor(formSelector) {
        this.form = document.querySelector(formSelector);
        if (this.form && this.form.getAttribute('data-ajax') !== 'false') {
            this.init();
        }
    }

    init() {
        this.setupValidation();
        this.setupSubmission();
        this.setupFileUploads();
    }

    setupValidation() {
        this.form.addEventListener('submit', (e) => {
            if (!this.validateForm()) {
                e.preventDefault();
                DashStackAdmin.utils.showToast('Vui lòng kiểm tra lại thông tin', 'warning');
            }
        });

        // Real-time validation
        this.form.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', () => this.validateField(field));
        });
    }

    validateForm() {
        let isValid = true;
        const fields = this.form.querySelectorAll('[required]');
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;

        // Required validation
        if (field.hasAttribute('required') && !value) {
            this.showFieldError(field, 'Trường này không được để trống');
            isValid = false;
        }
        // Email validation
        else if (field.type === 'email' && value && !/\S+@\S+\.\S+/.test(value)) {
            this.showFieldError(field, 'Email không hợp lệ');
            isValid = false;
        }
        // Remove error if valid
        else {
            this.clearFieldError(field);
        }

        return isValid;
    }

    showFieldError(field, message) {
        this.clearFieldError(field);
        field.classList.add('is-invalid');
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentElement.appendChild(errorDiv);
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const errorMsg = field.parentElement.querySelector('.invalid-feedback');
        if (errorMsg) errorMsg.remove();
    }

    setupSubmission() {
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = this.form.querySelector('[type="submit"]');
            const originalText = submitBtn.textContent;
            
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang xử lý...';
            
            try {
                const formData = new FormData(this.form);
                const response = await DashStackAdmin.data.request(this.form.action, {
                    method: this.form.method || 'POST',
                    body: formData
                });
                
                DashStackAdmin.utils.showToast('Lưu thành công!', 'success');
                
                // Reset form if successful
                if (response.success) {
                    this.form.reset();
                }
            } catch (error) {
                DashStackAdmin.utils.showToast('Đã xảy ra lỗi khi lưu', 'danger');
            } finally {
                // Restore button state
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }

    setupFileUploads() {
        this.form.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', (e) => {
                this.handleFileUpload(e.target);
            });
        });
    }

    handleFileUpload(input) {
        const files = Array.from(input.files);
        const maxSize = 5 * 1024 * 1024; // 5MB
        
        files.forEach(file => {
            if (file.size > maxSize) {
                DashStackAdmin.utils.showToast('File quá lớn (tối đa 5MB)', 'warning');
                input.value = '';
                return;
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize main admin functionality
    DashStackAdmin.init();
    
    // Initialize data tables
    new DataTable('.table');
    
    // Initialize forms
    new AdminForm('form');
    
    // Load dashboard data if on dashboard page
    if (window.location.pathname.includes('dashboard')) {
        DashStackAdmin.data.loadDashboardStats();
    }
});

// Export for global use
window.DashStackAdmin = DashStackAdmin;
window.DataTable = DataTable;
window.AdminForm = AdminForm;