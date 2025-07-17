// Main JavaScript file for Stocker Platform
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initializeApp();
});

function initializeApp() {
    // Initialize navigation
    initializeNavigation();
    
    // Initialize forms
    initializeForms();
    
    // Initialize real-time updates
    initializeRealTimeUpdates();
    
    // Initialize trade functionality
    initializeTradeFeatures();
    
    // Initialize admin features
    initializeAdminFeatures();
}

// Navigation functionality
function initializeNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.section');
    
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            
            // Remove active class from all nav items and sections
            navItems.forEach(nav => nav.classList.remove('active'));
            sections.forEach(section => section.classList.remove('active'));
            
            // Add active class to clicked item and target section
            this.classList.add('active');
            const targetSection = document.getElementById(target);
            if (targetSection) {
                targetSection.classList.add('active');
            }
        });
    });
}

// Form handling
function initializeForms() {
    // Password visibility toggle
    const passwordToggles = document.querySelectorAll('.password-toggle');
    passwordToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const passwordInput = this.previousElementSibling;
            const type = passwordInput.type === 'password' ? 'text' : 'password';
            passwordInput.type = type;
            this.textContent = type === 'password' ? '👁️' : '🙈';
        });
    });
    
    // Username availability check
    const usernameInput = document.getElementById('username');
    const roleSelect = document.getElementById('role');
    const usernameFeedback = document.getElementById('username-feedback');
    
    if (usernameInput && roleSelect && usernameFeedback) {
        let checkTimeout;
        
        function checkUsernameAvailability() {
            const username = usernameInput.value.trim();
            const role = roleSelect.value;
            
            if (username.length >= 3 && role) {
                fetch(`/check_username?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.exists) {
                            usernameFeedback.textContent = 'Username already taken for this role';
                            usernameFeedback.className = 'username-feedback username-taken';
                        } else {
                            usernameFeedback.textContent = 'Username available';
                            usernameFeedback.className = 'username-feedback username-available';
                        }
                    })
                    .catch(error => {
                        console.error('Error checking username:', error);
                        usernameFeedback.textContent = '';
                    });
            } else {
                usernameFeedback.textContent = '';
            }
        }
        
        usernameInput.addEventListener('input', function() {
            clearTimeout(checkTimeout);
            checkTimeout = setTimeout(checkUsernameAvailability, 500);
        });
        
        roleSelect.addEventListener('change', checkUsernameAvailability);
    }
    
    // Password strength validation
    const passwordInput = document.getElementById('password');
    const passwordStrength = document.getElementById('password-strength');
    
    if (passwordInput && passwordStrength) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            let messages = [];
            
            if (password.length >= 8) strength++;
            else messages.push('At least 8 characters');
            
            if (/\d/.test(password)) strength++;
            else messages.push('At least 1 number');
            
            if (/[!@#$%^&*]/.test(password)) strength++;
            else messages.push('At least 1 special character');
            
            if (strength === 3) {
                passwordStrength.textContent = 'Strong password';
                passwordStrength.className = 'password-strength strong';
            } else if (strength >= 2) {
                passwordStrength.textContent = 'Medium password';
                passwordStrength.className = 'password-strength medium';
            } else {
                passwordStrength.textContent = messages.join(', ');
                passwordStrength.className = 'password-strength weak';
            }
        });
    }
}

// Real-time updates
function initializeRealTimeUpdates() {
    // Update stock prices every 10 seconds
    if (document.querySelector('.stocks-grid') || document.querySelector('.portfolio-table')) {
        setInterval(updateStockPrices, 10000);
        showUpdateIndicator();
    }
}

function updateStockPrices() {
    fetch('/get_stock_prices')
        .then(response => response.json())
        .then(stocks => {
            // Update dashboard stock cards
            Object.keys(stocks).forEach(symbol => {
                const stockCard = document.querySelector(`[data-symbol="${symbol}"]`);
                if (stockCard) {
                    const priceElement = stockCard.querySelector('.stock-price');
                    if (priceElement) {
                        const oldPrice = parseFloat(priceElement.textContent.replace('$', ''));
                        const newPrice = stocks[symbol].price;
                        
                        priceElement.textContent = `$${newPrice.toFixed(2)}`;
                        
                        // Add flash effect for price changes
                        if (oldPrice !== newPrice) {
                            priceElement.classList.add('price-updated');
                            setTimeout(() => {
                                priceElement.classList.remove('price-updated');
                            }, 500);
                        }
                    }
                }
            });
            
            // Update portfolio values
            updatePortfolioValues(stocks);
            
            // Update trade form if open
            updateTradeForm(stocks);
        })
        .catch(error => {
            console.error('Error updating stock prices:', error);
        });
}

function updatePortfolioValues(stocks) {
    const portfolioRows = document.querySelectorAll('.portfolio-row');
    portfolioRows.forEach(row => {
        const symbol = row.dataset.symbol;
        const quantity = parseInt(row.dataset.quantity);
        
        if (stocks[symbol]) {
            const currentPrice = stocks[symbol].price;
            const totalValue = currentPrice * quantity;
            
            const currentPriceElement = row.querySelector('.current-price');
            const totalValueElement = row.querySelector('.total-value');
            
            if (currentPriceElement) {
                currentPriceElement.textContent = `$${currentPrice.toFixed(2)}`;
            }
            
            if (totalValueElement) {
                totalValueElement.textContent = `$${totalValue.toFixed(2)}`;
            }
        }
    });
}

function showUpdateIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'auto-update-indicator';
    indicator.textContent = 'Live Updates Active';
    document.body.appendChild(indicator);
    
    // Show indicator every 10 seconds for 2 seconds
    setInterval(() => {
        indicator.classList.add('show');
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }, 10000);
}

// Trade functionality
function initializeTradeFeatures() {
    // Trade form handling
    const stockSelect = document.getElementById('stock_symbol');
    const quantityInput = document.getElementById('quantity');
    const actionRadios = document.querySelectorAll('input[name="action"]');
    
    if (stockSelect && quantityInput) {
        function updateTradeCalculation() {
            const symbol = stockSelect.value;
            const quantity = parseInt(quantityInput.value) || 0;
            
            if (symbol && quantity > 0) {
                fetch('/get_stock_prices')
                    .then(response => response.json())
                    .then(stocks => {
                        if (stocks[symbol]) {
                            const price = stocks[symbol].price;
                            const total = price * quantity;
                            
                            // Update summary elements
                            updateElement('summary-symbol', symbol);
                            updateElement('summary-name', stocks[symbol].name);
                            updateElement('summary-quantity', quantity);
                            updateElement('current-price', `$${price.toFixed(2)}`);
                            updateElement('total-amount', `$${total.toFixed(2)}`);
                        }
                    })
                    .catch(error => {
                        console.error('Error calculating trade:', error);
                    });
            } else {
                // Clear summary if no valid selection
                updateElement('summary-symbol', '-');
                updateElement('summary-name', '-');
                updateElement('summary-quantity', '-');
                updateElement('current-price', '$0.00');
                updateElement('total-amount', '$0.00');
            }
        }
        
        stockSelect.addEventListener('change', updateTradeCalculation);
        quantityInput.addEventListener('input', updateTradeCalculation);
        
        // Add event listeners to action radios
        actionRadios.forEach(radio => {
            radio.addEventListener('change', updateTradeCalculation);
        });
        
        // Initial calculation
        updateTradeCalculation();
    }
    
    // Quantity adjustment buttons
    const quantityControls = document.querySelectorAll('.quantity-control');
    quantityControls.forEach(control => {
        control.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const currentValue = parseInt(input.value) || 0;
            const action = this.dataset.action;
            
            if (action === 'increase') {
                input.value = currentValue + 1;
            } else if (action === 'decrease' && currentValue > 1) {
                input.value = currentValue - 1;
            }
            
            // Trigger calculation update
            input.dispatchEvent(new Event('input'));
        });
    });
    
    // Pre-fill trade form from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const symbol = urlParams.get('symbol');
    const action = urlParams.get('action');
    
    if (symbol && stockSelect) {
        stockSelect.value = symbol;
    }
    
    if (action) {
        const actionRadio = document.querySelector(`input[name="action"][value="${action}"]`);
        if (actionRadio) {
            actionRadio.checked = true;
        }
    }
    
    // Trigger initial calculation if pre-filled
    if (symbol || action) {
        setTimeout(() => {
            const event = new Event('change');
            if (stockSelect) stockSelect.dispatchEvent(event);
        }, 100);
    }
}

function updateTradeForm(stocks) {
    const stockSelect = document.getElementById('stock_symbol');
    const quantityInput = document.getElementById('quantity');
    
    if (stockSelect && quantityInput && stockSelect.value && quantityInput.value) {
        const symbol = stockSelect.value;
        const quantity = parseInt(quantityInput.value) || 0;
        
        if (stocks[symbol]) {
            const price = stocks[symbol].price;
            const total = price * quantity;
            
            updateElement('current-price', `$${price.toFixed(2)}`);
            updateElement('total-amount', `$${total.toFixed(2)}`);
        }
    }
}

// Admin features
function initializeAdminFeatures() {
    // Admin dashboard statistics updates
    if (document.querySelector('.admin-dashboard')) {
        setInterval(updateAdminStats, 30000); // Update every 30 seconds
    }
    
    // User management features
    const userManagementButtons = document.querySelectorAll('.user-action-btn');
    userManagementButtons.forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const action = this.dataset.action;
            
            if (confirm(`Are you sure you want to ${action} this user?`)) {
                handleUserAction(userId, action);
            }
        });
    });
}

function updateAdminStats() {
    // This would be implemented to fetch updated statistics
    console.log('Updating admin statistics...');
}

function handleUserAction(userId, action) {
    // Handle admin actions like user management
    console.log(`Handling ${action} for user ${userId}`);
}

// Utility functions
function updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = content;
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    
    const main = document.querySelector('main');
    if (main) {
        main.insertBefore(notification, main.firstChild);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Session management
function checkSession() {
    fetch('/check_session')
        .then(response => response.json())
        .then(data => {
            if (!data.valid && window.location.pathname !== '/' && 
                window.location.pathname !== '/login' && 
                window.location.pathname !== '/signup') {
                window.location.href = '/login';
            }
        })
        .catch(error => {
            console.error('Session check failed:', error);
        });
}

// Check session every 5 minutes
setInterval(checkSession, 300000);

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showNotification('An error occurred. Please try again.', 'error');
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+Shift+L for logout
    if (e.ctrlKey && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        window.location.href = '/logout';
    }
    
    // Ctrl+Shift+D for dashboard
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        window.location.href = '/dashboard';
    }
    
    // Ctrl+Shift+T for trade
    if (e.ctrlKey && e.shiftKey && e.key === 'T') {
        e.preventDefault();
        window.location.href = '/trade';
    }
});

// Smooth scrolling for anchor links
document.addEventListener('click', function(e) {
    if (e.target.matches('a[href^="#"]')) {
        e.preventDefault();
        const targetId = e.target.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth'
            });
        }
    }
});

// Initialize tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.dataset.tooltip;
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
}

function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Initialize tooltips on page load
document.addEventListener('DOMContentLoaded', initializeTooltips);

// Performance monitoring
function logPerformance() {
    if (performance.timing) {
        const timing = performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;
        console.log(`Page load time: ${loadTime}ms`);
    }
}

// Call performance logging after page load
window.addEventListener('load', logPerformance);