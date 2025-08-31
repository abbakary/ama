document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar
    const toggleSidebar = document.getElementById('toggle-sidebar');
    const sidebarWrapper = document.getElementById('sidebar-wrapper');
    const mainContent = document.getElementById('main-content');
    
    // Toggle sidebar on button click
    if (toggleSidebar) {
        toggleSidebar.addEventListener('click', function() {
            sidebarWrapper.classList.toggle('collapsed');
        });
    }

    // Toggle submenu
    const hasArrow = document.querySelectorAll('.has-arrow');
    
    hasArrow.forEach(item => {
        item.addEventListener('click', function(e) {
            if (window.innerWidth > 992) {
                e.preventDefault();
                const parent = this.parentElement;
                const submenu = this.nextElementSibling;
                
                // Close other open submenus
                document.querySelectorAll('.sidebar-submenu').forEach(sub => {
                    if (sub !== submenu) {
                        sub.classList.remove('active');
                    }
                });
                
                // Toggle current submenu
                if (submenu) {
                    submenu.classList.toggle('active');
                }
            }
        });
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 992 && !sidebarWrapper.contains(e.target) && !e.target.closest('.toggle-sidebar')) {
            sidebarWrapper.classList.remove('show');
        }
    });

    // Show sidebar on mobile
    const mobileToggle = document.querySelector('.mobile-toggle');
    if (mobileToggle) {
        mobileToggle.addEventListener('click', function() {
            sidebarWrapper.classList.toggle('show');
        });
    }

    // Handle window resize
    function handleResize() {
        if (window.innerWidth <= 992) {
            sidebarWrapper.classList.remove('collapsed');
        }
    }

    // Initial check
    handleResize();
    
    // Add resize event listener
    window.addEventListener('resize', handleResize);

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => {
                    if (alert.parentNode) {
                        alert.remove();
                    }
                }, 150);
            }
        }, 5000);
    });

    // Add loading state to buttons on form submit
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.textContent = 'Processing...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.classList.remove('loading');
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 10000);
            }
        });
    });
});

// Function to refresh recent orders (for dashboard)
function refreshRecentOrders() {
    const container = document.getElementById('recent-orders');
    if (!container) return;

    fetch('/api/orders/recent/')
        .then(response => response.json())
        .then(data => {
            if (data.orders && data.orders.length > 0) {
                const html = data.orders.map(order => `
                    <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                            <small class="fw-bold">${order.order_number}</small><br>
                            <small class="text-muted">${order.customer}</small>
                        </div>
                        <span class="badge bg-${getStatusColor(order.status)}">${order.status}</span>
                    </div>
                `).join('');
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p class="text-muted small">No recent orders</p>';
            }
        })
        .catch(error => {
            console.error('Error fetching recent orders:', error);
            container.innerHTML = '<p class="text-muted small">Error loading orders</p>';
        });
}

// Helper function to get status color
function getStatusColor(status) {
    const colors = {
        'created': 'secondary',
        'assigned': 'info',
        'in_progress': 'warning',
        'completed': 'success',
        'cancelled': 'danger'
    };
    return colors[status] || 'secondary';
}

// Initialize tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Call tooltip initialization when DOM is loaded
document.addEventListener('DOMContentLoaded', initTooltips);

// Function to show loading spinner
function showLoading(element) {
    element.classList.add('loading');
    element.style.pointerEvents = 'none';
}

// Function to hide loading spinner
function hideLoading(element) {
    element.classList.remove('loading');
    element.style.pointerEvents = 'auto';
}

// Function to show notification
function showNotification(message, type = 'info') {
    const alertContainer = document.querySelector('.alert-container') || document.body;
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    if (alertContainer === document.body) {
        alert.style.position = 'fixed';
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.style.minWidth = '300px';
    }
    
    alertContainer.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove('show');
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 150);
        }
    }, 5000);
}

// AJAX form submission helper
function submitForm(form, successCallback) {
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    showLoading(submitBtn);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading(submitBtn);
        if (data.success) {
            showNotification(data.message || 'Operation completed successfully', 'success');
            if (successCallback) successCallback(data);
        } else {
            showNotification(data.message || 'An error occurred', 'danger');
        }
    })
    .catch(error => {
        hideLoading(submitBtn);
        showNotification('Network error occurred', 'danger');
        console.error('Error:', error);
    });
}
