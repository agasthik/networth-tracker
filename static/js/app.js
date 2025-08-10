// Networth Tracker Frontend JavaScript
document.addEventListener('DOMContentLoaded', function () {
    console.log('Networth Tracker loaded');
    initializeApp();
});

// Global state management
const AppState = {
    accounts: [],
    totalNetworth: 0,
    lastUpdated: null,
    isLoading: false
};

function initializeApp() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Load initial data
    loadAccountData();

    // Set up auto-refresh for stock prices every 5 minutes
    setInterval(updateStockPrices, 5 * 60 * 1000);
}

// Account Form Management
function showAccountForm(accountType, accountId = null) {
    const modal = new bootstrap.Modal(document.getElementById('accountFormModal'));
    const title = document.getElementById('accountFormTitle');
    const body = document.getElementById('accountFormBody');

    // Set modal title
    const accountTypes = {
        'CD': 'Certificate of Deposit',
        'SAVINGS': 'Savings Account',
        '401K': '401k Retirement Account',
        'TRADING': 'Trading Account',
        'I_BONDS': 'I-Bonds Account'
    };

    const isEdit = accountId !== null;
    title.textContent = `${isEdit ? 'Edit' : 'Add'} ${accountTypes[accountType]}`;

    // Load appropriate form template
    loadAccountForm(accountType, body, accountId);

    modal.show();
}

function loadAccountForm(accountType, container, accountId = null) {
    const formTemplates = {
        'CD': '/templates/accounts/cd_form.html',
        'SAVINGS': '/templates/accounts/savings_form.html',
        '401K': '/templates/accounts/401k_form.html',
        'TRADING': '/templates/accounts/trading_form.html',
        'I_BONDS': '/templates/accounts/ibonds_form.html'
    };

    // Show loading spinner
    container.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="min-height: 200px;">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;

    fetch(formTemplates[accountType])
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            container.innerHTML = html;

            // If editing, populate form with existing data
            if (accountId) {
                populateAccountForm(accountId, accountType);
            }

            // Initialize form validation
            initializeFormValidation(accountType);
        })
        .catch(error => {
            console.error('Error loading form:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error loading account form. Please try again.
                    <br><small class="text-muted">Error: ${error.message}</small>
                </div>
            `;
        });
}

function populateAccountForm(accountId, accountType) {
    const account = AppState.accounts.find(acc => acc.id === accountId);
    if (!account) return;

    // Populate common fields
    const form = document.querySelector(`#${accountType.toLowerCase()}AccountForm`);
    if (!form) return;

    // Fill in form fields based on account data
    Object.keys(account).forEach(key => {
        const input = form.querySelector(`[name="${key}"]`);
        if (input) {
            input.value = account[key];
        }
    });

    // Handle special cases for different account types
    if (accountType === 'TRADING' && account.positions) {
        // Clear existing positions
        const container = document.getElementById('stockPositionsList');
        container.innerHTML = '';

        // Add each stock position
        account.positions.forEach(position => {
            addStockPosition();
            const positionElements = container.querySelectorAll('.stock-position');
            const lastPosition = positionElements[positionElements.length - 1];

            lastPosition.querySelector('.stock-symbol').value = position.symbol;
            lastPosition.querySelector('.stock-shares').value = position.shares;
            lastPosition.querySelector('.stock-purchase-price').value = position.purchase_price;
            lastPosition.querySelector('.stock-purchase-date').value = position.purchase_date;
            if (position.current_price) {
                lastPosition.querySelector('.stock-current-price').value = position.current_price;
            }
        });

        // Recalculate summary
        if (typeof calculateTradingSummary === 'function') {
            calculateTradingSummary();
        }
    }

    if (accountType === 'I_BONDS') {
        // Trigger I-Bonds analysis calculations
        if (typeof calculateIBondsAnalysis === 'function') {
            calculateIBondsAnalysis();
        }
    }

    // Update submit button text for editing
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        const submitText = submitButton.querySelector('span');
        if (submitText) {
            submitText.textContent = `Update ${accountType.replace('_', '-')} Account`;
        }
    }
}

function submitAccountForm(event, accountType) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const accountData = Object.fromEntries(formData.entries());

    // Add account type
    accountData.type = accountType;

    // Filter out empty fields and convert string numbers to actual numbers
    const filteredData = {};
    for (const [key, value] of Object.entries(accountData)) {
        if (value !== '' && value !== null && value !== undefined) {
            // Convert numeric fields to numbers
            if (['principal_amount', 'current_value', 'interest_rate', 'current_balance',
                'cash_balance', 'purchase_amount', 'fixed_rate', 'inflation_rate'].includes(key)) {
                const numValue = parseFloat(value);
                if (!isNaN(numValue)) {
                    filteredData[key] = numValue;
                }
            } else {
                filteredData[key] = value;
            }
        }
    }

    // Handle stock positions for trading accounts
    if (accountType === 'TRADING') {
        const positions = [];
        const stockPositions = form.querySelectorAll('.stock-position');

        stockPositions.forEach(position => {
            const symbol = position.querySelector('.stock-symbol').value;
            const shares = position.querySelector('.stock-shares').value;
            const purchasePrice = position.querySelector('.stock-purchase-price').value;
            const purchaseDate = position.querySelector('.stock-purchase-date').value;
            const currentPrice = position.querySelector('.stock-current-price').value;

            if (symbol && shares && purchasePrice && purchaseDate) {
                positions.push({
                    symbol: symbol.toUpperCase(),
                    shares: parseFloat(shares),
                    purchase_price: parseFloat(purchasePrice),
                    purchase_date: purchaseDate,
                    current_price: currentPrice ? parseFloat(currentPrice) : parseFloat(purchasePrice)
                });
            }
        });

        filteredData.positions = positions;
    }

    // Validate form data
    if (!validateAccountForm(filteredData, accountType)) {
        return;
    }

    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Saving...';
    submitButton.disabled = true;

    // Determine if this is an update or create
    const accountId = filteredData.account_id;
    const isUpdate = accountId && accountId.trim() !== '';

    const url = isUpdate ? `/api/accounts/${accountId}` : '/api/accounts';
    const method = isUpdate ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(filteredData)
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            showNotification(
                `${accountType} account ${isUpdate ? 'updated' : 'created'} successfully!`,
                'success'
            );

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('accountFormModal'));
            modal.hide();

            // Refresh account data
            loadAccountData();
        })
        .catch(error => {
            console.error('Error saving account:', error);
            showNotification(
                error.message || 'Error saving account. Please try again.',
                'danger'
            );
        })
        .finally(() => {
            // Restore button state
            submitButton.innerHTML = originalText;
            submitButton.disabled = false;
        });
}

// Utility Functions
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at the top of the container
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertDiv);
        bsAlert.close();
    }, 5000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatNumber(amount) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value / 100);
}

// Real-time Networth Calculations and UI Updates
function calculateTotalNetworth() {
    let total = 0;
    const accountTotals = {
        CD: 0,
        SAVINGS: 0,
        '401K': 0,
        TRADING: 0,
        I_BONDS: 0
    };

    AppState.accounts.forEach(account => {
        let accountValue = 0;

        switch (account.account_type) {
            case 'CD':
                accountValue = account.current_value || 0;
                break;
            case 'SAVINGS':
                accountValue = account.current_balance || 0;
                break;
            case '401K':
                accountValue = account.current_balance || 0;
                break;
            case 'TRADING':
                accountValue = (account.cash_balance || 0);
                if (account.positions) {
                    account.positions.forEach(position => {
                        const currentPrice = position.current_price || position.purchase_price || 0;
                        accountValue += (position.shares || 0) * currentPrice;
                    });
                }
                break;
            case 'I_BONDS':
                accountValue = account.current_value || 0;
                break;
        }

        accountTotals[account.account_type] += accountValue;
        total += accountValue;
    });

    AppState.totalNetworth = total;
    return { total, accountTotals };
}

function updateNetworthDisplay() {
    const { total, accountTotals } = calculateTotalNetworth();

    // Update main networth display
    const networthElement = document.getElementById('networthAmount');
    if (networthElement) {
        networthElement.textContent = formatNumber(total);
        // Add currency class if not already present
        const parentElement = networthElement.closest('#totalNetworth');
        if (parentElement && !parentElement.classList.contains('currency')) {
            parentElement.classList.add('currency');
        }
    }

    // Update last updated time
    const lastUpdatedElement = document.getElementById('lastUpdated');
    if (lastUpdatedElement && AppState.lastUpdated) {
        lastUpdatedElement.textContent = AppState.lastUpdated.toLocaleString();
    }

    // Update account type totals
    Object.keys(accountTotals).forEach(type => {
        const elementId = type === '401K' ? '401kTotal' :
            type === 'I_BONDS' ? 'ibondsTotal' :
                type.toLowerCase() + 'Total';
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = formatNumber(accountTotals[type]);
            // Add currency class to parent if not already present
            const parentElement = element.closest('p');
            if (parentElement && !parentElement.classList.contains('currency')) {
                parentElement.classList.add('currency');
            }
        }
    });
}

function updateDashboardSummary() {
    const { total, accountTotals } = calculateTotalNetworth();

    // Update summary table
    const summaryTableBody = document.getElementById('summaryTableBody');
    if (summaryTableBody) {
        const accountTypeNames = {
            'CD': 'Certificates of Deposit',
            'SAVINGS': 'Savings Accounts',
            '401K': '401k Retirement',
            'TRADING': 'Trading Accounts',
            'I_BONDS': 'I-Bonds Treasury'
        };

        let summaryHTML = '';
        Object.keys(accountTotals).forEach(type => {
            const allAccounts = AppState.accounts.filter(acc => acc.account_type === type);
            const filteredAccounts = getFilteredAccounts(AppState.accounts, type);
            const count = filteredAccounts.length;
            const demoCount = allAccounts.filter(acc => acc.is_demo).length;
            const value = accountTotals[type];
            const percentage = total > 0 ? (value / total * 100) : 0;

            if (count > 0) {
                let accountInfo = `${accountTypeNames[type]}`;
                if (demoCount > 0 && !demoFilterActive) {
                    accountInfo += ` <small class="text-muted">(${demoCount} demo)</small>`;
                }

                summaryHTML += `
                    <tr>
                        <td>${accountInfo}</td>
                        <td>${count}</td>
                        <td>${formatCurrency(value)}</td>
                        <td>${percentage.toFixed(1)}%</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="showAccountTab('${type}')">
                                View Details
                            </button>
                        </td>
                    </tr>
                `;
            }
        });

        summaryTableBody.innerHTML = summaryHTML;
    }

    // Update quick stats
    const totalAccountsElement = document.getElementById('totalAccounts');
    if (totalAccountsElement) {
        const displayedAccounts = demoFilterActive ?
            AppState.accounts.filter(acc => acc.is_demo) :
            AppState.accounts;
        totalAccountsElement.textContent = displayedAccounts.length;
    }

    const totalInstitutionsElement = document.getElementById('totalInstitutions');
    if (totalInstitutionsElement) {
        const displayedAccounts = demoFilterActive ?
            AppState.accounts.filter(acc => acc.is_demo) :
            AppState.accounts;
        const institutions = new Set(displayedAccounts.map(acc => acc.institution));
        totalInstitutionsElement.textContent = institutions.size;
    }
}

function updateAccountTabs() {
    // Update each account type tab with current data
    updateCDAccountsList();
    updateSavingsAccountsList();
    update401kAccountsList();
    updateTradingAccountsList();
    updateIBondsAccountsList();
}

function showAccountTab(accountType) {
    const tabMap = {
        'CD': 'cd-tab',
        'SAVINGS': 'savings-tab',
        '401K': 'retirement401k-tab',
        'TRADING': 'trading-tab',
        'I_BONDS': 'ibonds-tab'
    };

    const tabId = tabMap[accountType];
    if (tabId) {
        const tab = document.getElementById(tabId);
        if (tab) {
            tab.click();
        } else {
            console.error('Tab element not found for account type:', accountType, 'with tab ID:', tabId);
        }
    } else {
        console.error('No tab mapping found for account type:', accountType);
    }
}

// Session Management
function showSessionInfo() {
    const modal = new bootstrap.Modal(document.getElementById('sessionInfoModal'));
    modal.show();
}

// Data Management Functions
function loadAccountData() {
    if (AppState.isLoading) return;

    AppState.isLoading = true;
    showLoadingState();

    fetch('/api/accounts')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            AppState.accounts = data.accounts || [];
            AppState.lastUpdated = new Date();

            console.log('Loaded accounts:', AppState.accounts.length);

            // Update UI with loaded data
            updateDashboardSummary();
            updateAccountTabs();
            updateNetworthDisplay();
        })
        .catch(error => {
            console.error('Error loading account data:', error);
            showNotification('Error loading account data. Please refresh the page.', 'danger');
        })
        .finally(() => {
            AppState.isLoading = false;
            hideLoadingState();

            // Load portfolio summary after loading state is cleared
            console.log('About to call loadPortfolioSummary');
            loadPortfolioSummary();
            console.log('About to call initializeCharts');
            initializeCharts();
        });
}

function refreshNetworth() {
    loadAccountData();
    showNotification('Networth data refreshed successfully!', 'success');
}

function updateStockPrices() {
    if (AppState.isLoading) return;

    AppState.isLoading = true;

    // Show loading indicator
    const button = document.querySelector('button[onclick="updateStockPrices()"]');
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Updating...';
        button.disabled = true;

        fetch('/api/stocks/prices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                showNotification('Stock prices updated successfully!', 'success');
                // Refresh account data to show updated values
                loadAccountData();
            })
            .catch(error => {
                console.error('Error updating stock prices:', error);
                showNotification('Error updating stock prices. Please try again.', 'danger');
            })
            .finally(() => {
                AppState.isLoading = false;
                button.innerHTML = originalText;
                button.disabled = false;
            });
    }
}

function exportData() {
    // Show loading state
    const button = document.querySelector('button[onclick="exportData()"]');
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exporting...';
        button.disabled = true;

        fetch('/api/export')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // Create download link
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `networth-backup-${new Date().toISOString().split('T')[0]}.enc`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                showNotification('Data exported successfully!', 'success');
            })
            .catch(error => {
                console.error('Error exporting data:', error);
                showNotification('Error exporting data. Please try again.', 'danger');
            })
            .finally(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            });
    }
}

function showImportModal() {
    const modal = new bootstrap.Modal(document.getElementById('importDataModal'));
    modal.show();
}

function importData() {
    const fileInput = document.getElementById('importFile');
    const passwordInput = document.getElementById('importPassword');
    const overwriteCheckbox = document.getElementById('overwriteExisting');
    const file = fileInput.files[0];

    if (!file) {
        showNotification('Please select a file to import.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('backup_file', file);

    // Add backup password if provided
    if (passwordInput.value.trim()) {
        formData.append('backup_password', passwordInput.value.trim());
    }

    // Add overwrite option
    formData.append('overwrite_existing', overwriteCheckbox.checked ? 'true' : 'false');

    // Show loading state
    const button = document.querySelector('button[onclick="importData()"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Importing...';
    button.disabled = true;

    fetch('/api/import', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            const importResults = data.import_results;
            let message = 'Data imported successfully!';

            if (importResults) {
                message += ` Imported ${importResults.accounts_imported} accounts`;
                if (importResults.accounts_skipped > 0) {
                    message += `, skipped ${importResults.accounts_skipped} existing accounts`;
                }
                if (importResults.stock_positions_imported > 0) {
                    message += `, ${importResults.stock_positions_imported} stock positions`;
                }
                if (importResults.historical_snapshots_imported > 0) {
                    message += `, ${importResults.historical_snapshots_imported} historical snapshots`;
                }
            }

            showNotification(message, 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('importDataModal'));
            modal.hide();

            // Clear form
            fileInput.value = '';
            passwordInput.value = '';
            overwriteCheckbox.checked = false;

            // Refresh account data
            loadAccountData();
        })
        .catch(error => {
            console.error('Error importing data:', error);
            showNotification(error.message || 'Error importing data. Please try again.', 'danger');
        })
        .finally(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

// Form Validation
function initializeFormValidation(accountType) {
    const form = document.querySelector(`#${accountType.toLowerCase()}AccountForm`);
    if (!form) return;

    // Add real-time validation to required fields
    const requiredFields = form.querySelectorAll('[required]');
    requiredFields.forEach(field => {
        field.addEventListener('blur', function () {
            validateField(this);
        });

        field.addEventListener('input', function () {
            clearFieldError(this);
        });
    });

    // Add number validation to numeric fields
    const numberFields = form.querySelectorAll('input[type="number"]');
    numberFields.forEach(field => {
        field.addEventListener('input', function () {
            validateNumberField(this);
        });
    });
}

function validateField(field) {
    const value = field.value.trim();
    const isValid = field.checkValidity();

    if (!isValid) {
        showFieldError(field, getFieldErrorMessage(field));
        return false;
    }

    clearFieldError(field);
    return true;
}

function validateNumberField(field) {
    const value = parseFloat(field.value);
    const min = parseFloat(field.getAttribute('min')) || 0;
    const max = parseFloat(field.getAttribute('max')) || Infinity;

    if (isNaN(value) || value < min || value > max) {
        showFieldError(field, `Please enter a valid number between ${min} and ${max}`);
        return false;
    }

    clearFieldError(field);
    return true;
}

function showFieldError(field, message) {
    clearFieldError(field);

    field.classList.add('is-invalid');

    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;

    field.parentNode.appendChild(errorDiv);
}

function clearFieldError(field) {
    field.classList.remove('is-invalid');

    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

function getFieldErrorMessage(field) {
    if (field.validity.valueMissing) {
        return 'This field is required.';
    }
    if (field.validity.typeMismatch) {
        return 'Please enter a valid value.';
    }
    if (field.validity.rangeUnderflow) {
        return `Value must be at least ${field.min}.`;
    }
    if (field.validity.rangeOverflow) {
        return `Value must be no more than ${field.max}.`;
    }
    return 'Please enter a valid value.';
}

function validateAccountForm(accountData, accountType) {
    let isValid = true;
    const errors = [];

    // Common validation
    if (!accountData.name || accountData.name.trim() === '') {
        errors.push('Account name is required.');
        isValid = false;
    }

    if (!accountData.institution || accountData.institution.trim() === '') {
        errors.push('Institution name is required.');
        isValid = false;
    }

    // Account type specific validation
    switch (accountType) {
        case 'CD':
            if (!accountData.principal_amount || parseFloat(accountData.principal_amount) <= 0) {
                errors.push('Principal amount must be greater than 0.');
                isValid = false;
            }
            if (!accountData.interest_rate || parseFloat(accountData.interest_rate) < 0) {
                errors.push('Interest rate must be 0 or greater.');
                isValid = false;
            }
            if (!accountData.maturity_date) {
                errors.push('Maturity date is required.');
                isValid = false;
            }
            break;

        case 'SAVINGS':
            if (!accountData.current_balance || parseFloat(accountData.current_balance) < 0) {
                errors.push('Current balance must be 0 or greater.');
                isValid = false;
            }
            break;

        case '401K':
            if (!accountData.current_balance || parseFloat(accountData.current_balance) < 0) {
                errors.push('Current balance must be 0 or greater.');
                isValid = false;
            }
            break;

        case 'TRADING':
            if (!accountData.broker_name || accountData.broker_name.trim() === '') {
                errors.push('Broker name is required.');
                isValid = false;
            }
            if (!accountData.cash_balance || parseFloat(accountData.cash_balance) < 0) {
                errors.push('Cash balance must be 0 or greater.');
                isValid = false;
            }
            break;

        case 'I_BONDS':
            if (!accountData.purchase_amount || parseFloat(accountData.purchase_amount) <= 0) {
                errors.push('Purchase amount must be greater than 0.');
                isValid = false;
            }
            if (!accountData.purchase_date) {
                errors.push('Purchase date is required.');
                isValid = false;
            }
            break;
    }

    if (!isValid) {
        showNotification(errors.join(' '), 'danger');
    }

    return isValid;
}

// Account Management
function deleteAccount(accountId) {
    const account = AppState.accounts.find(acc => acc.id === accountId);
    if (!account) return;

    if (!confirm(`Are you sure you want to delete "${account.name}"? This action cannot be undone.`)) {
        return;
    }

    fetch(`/api/accounts/${accountId}`, {
        method: 'DELETE'
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            showNotification('Account deleted successfully.', 'success');
            loadAccountData(); // Refresh the data
        })
        .catch(error => {
            console.error('Error deleting account:', error);
            showNotification(error.message || 'Error deleting account. Please try again.', 'danger');
        });
}

// Error Handling
window.addEventListener('error', function (event) {
    console.error('JavaScript error:', event.error);
    showNotification('An unexpected error occurred. Please refresh the page.', 'danger');
});

// Portfolio Summary and Charts
let portfolioChart = null;
let portfolioData = null;

function loadPortfolioSummary() {
    fetch('/api/portfolio/summary')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            portfolioData = data;
            updatePortfolioSummary(data);
            updatePortfolioChart(data);
            updateRecentActivity();
        })
        .catch(error => {
            console.error('Error loading portfolio summary:', error);
            showNotification('Error loading portfolio summary. Please refresh the page.', 'danger');
        });
}

function updatePortfolioSummary(data) {
    // Update networth change indicator
    const networthChange = document.getElementById('networthChange');
    if (networthChange && data.performance) {
        const change = data.performance.monthly_change;
        const changePercent = data.performance.monthly_change_percent;
        const isPositive = change >= 0;

        networthChange.innerHTML = `
            <i class="fas fa-arrow-${isPositive ? 'up' : 'down'} text-${isPositive ? 'success' : 'danger'}"></i>
            ${isPositive ? '+' : ''}${formatCurrency(change)} (${changePercent.toFixed(2)}%)
        `;
        networthChange.className = `me-3 text-${isPositive ? 'success' : 'danger'}`;
    }

    // Update summary table
    const summaryTableBody = document.getElementById('summaryTableBody');
    if (summaryTableBody && data.account_types) {
        const accountTypeNames = {
            'CD': 'Certificates of Deposit',
            'SAVINGS': 'Savings Accounts',
            '401K': '401k Retirement',
            'TRADING': 'Trading Accounts',
            'I_BONDS': 'I-Bonds Treasury'
        };

        let summaryHTML = '';
        Object.keys(data.account_types).forEach(type => {
            const typeData = data.account_types[type];
            if (typeData.count > 0) {
                const percentage = data.total_networth > 0 ? (typeData.value / data.total_networth * 100) : 0;

                // Calculate type-level performance
                let monthlyChange = 0;
                typeData.accounts.forEach(account => {
                    monthlyChange += account.monthly_change || 0;
                });

                summaryHTML += `
                    <tr>
                        <td>
                            <strong>${accountTypeNames[type]}</strong>
                            <br><small class="text-muted">${typeData.count} account${typeData.count > 1 ? 's' : ''}</small>
                        </td>
                        <td>${formatCurrency(typeData.value)}</td>
                        <td>${percentage.toFixed(1)}%</td>
                        <td class="${monthlyChange >= 0 ? 'text-success' : 'text-danger'}">
                            ${monthlyChange >= 0 ? '+' : ''}${formatCurrency(monthlyChange)}
                        </td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="showAccountTab('${type}')">
                                View Details
                            </button>
                        </td>
                    </tr>
                `;
            }
        });

        summaryTableBody.innerHTML = summaryHTML;
    }

    // Update quick stats
    const totalAccountsElement = document.getElementById('totalAccounts');
    if (totalAccountsElement) {
        totalAccountsElement.textContent = data.total_accounts || 0;
    }

    const totalInstitutionsElement = document.getElementById('totalInstitutions');
    if (totalInstitutionsElement) {
        totalInstitutionsElement.textContent = data.total_institutions || 0;
    }

    const monthlyGainElement = document.getElementById('monthlyGain');
    if (monthlyGainElement && data.performance) {
        const change = data.performance.monthly_change;
        monthlyGainElement.textContent = `${change >= 0 ? '+' : ''}${formatCurrency(change)}`;
        monthlyGainElement.className = change >= 0 ? 'text-success' : 'text-danger';
    }

    // For yearly gain, we'll use a simple estimate (monthly * 12)
    const yearlyGainElement = document.getElementById('yearlyGain');
    if (yearlyGainElement && data.performance) {
        const yearlyEstimate = data.performance.monthly_change * 12;
        yearlyGainElement.textContent = `${yearlyEstimate >= 0 ? '+' : ''}${formatCurrency(yearlyEstimate)}`;
        yearlyGainElement.className = yearlyEstimate >= 0 ? 'text-success' : 'text-danger';
    }
}

function updatePortfolioChart(data) {
    const canvas = document.getElementById('portfolioDonutChart');
    if (!canvas || !data.account_types) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart if it exists
    if (portfolioChart) {
        portfolioChart.destroy();
    }

    // Prepare chart data
    const labels = [];
    const values = [];
    const colors = [];
    const colorMap = {
        'CD': '#17a2b8',      // info
        'SAVINGS': '#28a745',  // success
        '401K': '#ffc107',     // warning
        'TRADING': '#dc3545',  // danger
        'I_BONDS': '#6c757d'   // secondary
    };

    const typeNames = {
        'CD': 'CDs',
        'SAVINGS': 'Savings',
        '401K': '401k',
        'TRADING': 'Trading',
        'I_BONDS': 'I-Bonds'
    };

    Object.keys(data.account_types).forEach(type => {
        const typeData = data.account_types[type];
        if (typeData.count > 0 && typeData.value > 0) {
            labels.push(typeNames[type]);
            values.push(typeData.value);
            colors.push(colorMap[type]);
        }
    });

    if (values.length === 0) {
        // Show no data message
        const chartContainer = document.getElementById('portfolioChart');
        chartContainer.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-chart-pie fa-3x mb-3"></i>
                <p>No investment data available</p>
                <small>Add accounts to see your portfolio breakdown</small>
            </div>
        `;
        return;
    }

    // Create Chart.js donut chart
    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverBorderWidth: 3,
                hoverBorderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${formatCurrency(value)} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%',
            animation: {
                animateRotate: true,
                duration: 1000
            }
        }
    });

    // Update portfolio summary list
    updatePortfolioSummaryList(data, colorMap, typeNames);
}

function updatePortfolioSummaryList(data, colorMap, typeNames) {
    const container = document.getElementById('portfolioSummaryList');
    if (!container || !data.account_types) return;

    let summaryHTML = '';
    const totalValue = data.total_networth || 0;

    Object.keys(data.account_types).forEach(type => {
        const typeData = data.account_types[type];
        if (typeData.count > 0 && typeData.value > 0) {
            const percentage = totalValue > 0 ? ((typeData.value / totalValue) * 100).toFixed(1) : 0;
            const color = colorMap[type];

            summaryHTML += `
                <div class="d-flex align-items-center mb-3">
                    <div class="me-3">
                        <div style="width: 16px; height: 16px; background-color: ${color}; border-radius: 50%;"></div>
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-medium">${typeNames[type]}</span>
                            <span class="text-muted small">${percentage}%</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">${typeData.count} account${typeData.count > 1 ? 's' : ''}</small>
                            <span class="fw-bold">${formatCurrency(typeData.value)}</span>
                        </div>
                    </div>
                </div>
            `;
        }
    });

    if (summaryHTML === '') {
        summaryHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-info-circle mb-2"></i>
                <p class="mb-0">No accounts to display</p>
            </div>
        `;
    }

    container.innerHTML = summaryHTML;
}

function updateRecentActivity() {
    const container = document.getElementById('recentActivity');
    if (!container || !portfolioData) return;

    // Create recent activity from account data
    let activities = [];

    Object.keys(portfolioData.account_types).forEach(type => {
        const typeData = portfolioData.account_types[type];
        typeData.accounts.forEach(account => {
            if (Math.abs(account.monthly_change) > 0.01) {
                activities.push({
                    account_name: account.name,
                    institution: account.institution,
                    change: account.monthly_change,
                    change_percent: account.monthly_change_percent,
                    type: type,
                    timestamp: new Date() // Placeholder - in real app would come from API
                });
            }
        });
    });

    // Sort by absolute change (largest changes first)
    activities.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));

    // Take top 5 activities
    activities = activities.slice(0, 5);

    if (activities.length === 0) {
        container.innerHTML = `
            <div class="text-center py-3">
                <small class="text-muted">No recent activity</small>
            </div>
        `;
        return;
    }

    let html = '';
    activities.forEach(activity => {
        const isPositive = activity.change >= 0;
        const typeIcons = {
            'CD': 'fas fa-certificate',
            'SAVINGS': 'fas fa-piggy-bank',
            '401K': 'fas fa-briefcase',
            'TRADING': 'fas fa-chart-bar',
            'I_BONDS': 'fas fa-university'
        };

        html += `
            <div class="list-group-item list-group-item-action border-0 px-0">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <i class="${typeIcons[activity.type]} text-muted me-2"></i>
                        <div>
                            <small class="fw-bold">${activity.account_name}</small>
                            <br><small class="text-muted">${activity.institution}</small>
                        </div>
                    </div>
                    <div class="text-end">
                        <small class="${isPositive ? 'text-success' : 'text-danger'}">
                            ${isPositive ? '+' : ''}${formatCurrency(activity.change)}
                        </small>
                        <br><small class="text-muted">${activity.change_percent.toFixed(1)}%</small>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function initializeCharts() {
    // Initialize Chart.js if not already loaded
    if (typeof Chart === 'undefined') {
        // Load Chart.js dynamically
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = function () {
            console.log('Chart.js loaded');
            if (portfolioData) {
                updatePortfolioChart(portfolioData);
            }
        };
        document.head.appendChild(script);
    } else if (portfolioData) {
        updatePortfolioChart(portfolioData);
    }
}

function showAccountDetails(accountId) {
    // Load detailed account view with performance metrics
    fetch(`/api/accounts/${accountId}/performance?period_days=30`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            displayAccountDetailsModal(accountId, data);
        })
        .catch(error => {
            console.error('Error loading account details:', error);
            showNotification('Error loading account details. Please try again.', 'danger');
        });
}

function displayAccountDetailsModal(accountId, performanceData) {
    // Find the account in our current data
    const account = AppState.accounts.find(acc => acc.id === accountId);
    if (!account) return;

    // Create modal content
    const modalHTML = `
        <div class="modal fade" id="accountDetailsModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-chart-line me-2"></i>
                            ${account.name} - Performance Details
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h4 class="text-primary">${formatCurrency(account.current_value || account.get_current_value?.() || 0)}</h4>
                                        <small class="text-muted">Current Value</small>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card bg-light">
                                    <div class="card-body text-center">
                                        <h4 class="${performanceData.gains_losses?.absolute_gain_loss >= 0 ? 'text-success' : 'text-danger'}">
                                            ${performanceData.gains_losses ?
            (performanceData.gains_losses.absolute_gain_loss >= 0 ? '+' : '') +
            formatCurrency(performanceData.gains_losses.absolute_gain_loss) :
            '$0.00'}
                                        </h4>
                                        <small class="text-muted">30-Day Change</small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        ${performanceData.performance ? `
                        <div class="row mb-4">
                            <div class="col-12">
                                <h6>Performance Metrics</h6>
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <tr>
                                            <td><strong>Percentage Change:</strong></td>
                                            <td class="${performanceData.performance.percentage_change >= 0 ? 'text-success' : 'text-danger'}">
                                                ${performanceData.performance.percentage_change.toFixed(2)}%
                                            </td>
                                        </tr>
                                        <tr>
                                            <td><strong>Trend Direction:</strong></td>
                                            <td>
                                                <span class="badge bg-${performanceData.performance.trend_direction === 'INCREASING' ? 'success' :
                performanceData.performance.trend_direction === 'DECREASING' ? 'danger' : 'secondary'}">
                                                    ${performanceData.performance.trend_direction}
                                                </span>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td><strong>Average Value:</strong></td>
                                            <td>${formatCurrency(performanceData.performance.average_value)}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Min/Max Value:</strong></td>
                                            <td>${formatCurrency(performanceData.performance.min_value)} / ${formatCurrency(performanceData.performance.max_value)}</td>
                                        </tr>
                                        <tr>
                                            <td><strong>Volatility:</strong></td>
                                            <td>${formatCurrency(performanceData.performance.volatility)}</td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                        </div>
                        ` : ''}

                        ${performanceData.trend ? `
                        <div class="row">
                            <div class="col-12">
                                <h6>Trend Analysis</h6>
                                <div class="alert alert-info">
                                    <strong>Direction:</strong> ${performanceData.trend.direction}<br>
                                    <strong>Daily Rate:</strong> ${formatCurrency(performanceData.trend.slope)} per day<br>
                                    <strong>Confidence:</strong> ${performanceData.trend.confidence} (R² = ${performanceData.trend.r_squared.toFixed(3)})
                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="showAccountForm('${account.account_type}', '${account.id}')">
                            Edit Account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    const existingModal = document.getElementById('accountDetailsModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('accountDetailsModal'));
    modal.show();

    // Clean up modal when hidden
    document.getElementById('accountDetailsModal').addEventListener('hidden.bs.modal', function () {
        this.remove();
    });
}

// Helper function to create demo indicator HTML
function getDemoIndicatorHTML(account) {
    if (account.is_demo) {
        return `
            <span class="demo-badge me-2">
                <i class="fas fa-flask me-1"></i>Demo
            </span>
        `;
    }
    return '';
}

// Helper function to get demo CSS class for account cards
function getDemoCardClass(account) {
    return account.is_demo ? 'demo-account-card' : '';
}

// Helper function to filter accounts based on demo filter state
function getFilteredAccounts(accounts, accountType) {
    let filtered = accounts.filter(acc => acc.account_type === accountType);

    if (demoFilterActive) {
        filtered = filtered.filter(acc => acc.is_demo);
    }

    return filtered;
}

// Account List Updates
function updateCDAccountsList() {
    const container = document.getElementById('cdAccountsList');
    if (!container) return;

    const cdAccounts = getFilteredAccounts(AppState.accounts, 'CD');

    if (cdAccounts.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo CD accounts found.' :
            'Add your first Certificate of Deposit account to get started.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-certificate fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No CD Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    cdAccounts.forEach(account => {
        const maturityDate = new Date(account.maturity_date);
        const daysToMaturity = Math.ceil((maturityDate - new Date()) / (1000 * 60 * 60 * 24));

        html += `
            <div class="card mb-3 ${getDemoCardClass(account)}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h6 class="card-title mb-1">
                                ${getDemoIndicatorHTML(account)}
                                ${account.name}
                            </h6>
                            <p class="text-muted mb-1">${account.institution}</p>
                            <small class="text-muted">
                                Principal: ${formatCurrency(account.principal_amount)} |
                                Rate: ${account.interest_rate}% |
                                Matures in ${daysToMaturity} days
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(account.current_value)}</h5>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('CD', '${account.id}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function updateSavingsAccountsList() {
    const container = document.getElementById('savingsAccountsList');
    if (!container) return;

    const savingsAccounts = getFilteredAccounts(AppState.accounts, 'SAVINGS');

    if (savingsAccounts.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo savings accounts found.' :
            'Add your first savings account to track your cash savings.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-piggy-bank fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Savings Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    savingsAccounts.forEach(account => {
        html += `
            <div class="card mb-3 ${getDemoCardClass(account)}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h6 class="card-title mb-1">
                                ${getDemoIndicatorHTML(account)}
                                ${account.name}
                            </h6>
                            <p class="text-muted mb-1">${account.institution}</p>
                            <small class="text-muted">Interest Rate: ${account.interest_rate}%</small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(account.current_balance)}</h5>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('SAVINGS', '${account.id}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function update401kAccountsList() {
    const container = document.getElementById('retirement401kAccountsList');
    if (!container) return;

    const accounts401k = getFilteredAccounts(AppState.accounts, '401K');

    if (accounts401k.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo 401k accounts found.' :
            'Add your retirement accounts to track your long-term savings.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-briefcase fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No 401k Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    accounts401k.forEach(account => {
        html += `
            <div class="card mb-3 ${getDemoCardClass(account)}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h6 class="card-title mb-1">
                                ${getDemoIndicatorHTML(account)}
                                ${account.name}
                            </h6>
                            <p class="text-muted mb-1">${account.institution}</p>
                            <small class="text-muted">
                                Employer Match: ${formatCurrency(account.employer_match)} |
                                Contribution Limit: ${formatCurrency(account.contribution_limit)}
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(account.current_balance)}</h5>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('401K', '${account.id}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function updateTradingAccountsList() {
    const container = document.getElementById('tradingAccountsList');
    if (!container) return;

    const tradingAccounts = getFilteredAccounts(AppState.accounts, 'TRADING');

    if (tradingAccounts.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo trading accounts found.' :
            'Add your brokerage accounts to track your stock investments.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-chart-bar fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Trading Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    tradingAccounts.forEach(account => {
        let totalStockValue = 0;
        let totalGainLoss = 0;

        if (account.positions) {
            account.positions.forEach(position => {
                const currentPrice = position.current_price || position.purchase_price || 0;
                const positionValue = (position.shares || 0) * currentPrice;
                const positionCost = (position.shares || 0) * (position.purchase_price || 0);
                totalStockValue += positionValue;
                totalGainLoss += (positionValue - positionCost);
            });
        }

        const totalValue = (account.cash_balance || 0) + totalStockValue;

        html += `
            <div class="card mb-3 ${getDemoCardClass(account)}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h6 class="card-title mb-1">
                                ${getDemoIndicatorHTML(account)}
                                ${account.name}
                            </h6>
                            <p class="text-muted mb-1">${account.broker_name}</p>
                            <small class="text-muted">
                                Cash: ${formatCurrency(account.cash_balance)} |
                                Stocks: ${formatCurrency(totalStockValue)} |
                                Positions: ${account.positions ? account.positions.length : 0}
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(totalValue)}</h5>
                            <small class="${totalGainLoss >= 0 ? 'text-success' : 'text-danger'}">
                                ${totalGainLoss >= 0 ? '+' : ''}${formatCurrency(totalGainLoss)}
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('TRADING', '${account.id}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function updateIBondsAccountsList() {
    const container = document.getElementById('ibondsAccountsList');
    if (!container) return;

    const ibondsAccounts = getFilteredAccounts(AppState.accounts, 'I_BONDS');

    if (ibondsAccounts.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo I-Bonds accounts found.' :
            'Add your Treasury I-Bonds to track inflation-protected savings.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-university fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No I-Bonds Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    ibondsAccounts.forEach(account => {
        const purchaseDate = new Date(account.purchase_date);
        const maturityDate = new Date(account.maturity_date);
        const yearsHeld = Math.floor((new Date() - purchaseDate) / (1000 * 60 * 60 * 24 * 365));

        html += `
            <div class="card mb-3 ${getDemoCardClass(account)}">
                <div class="card-body">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <h6 class="card-title mb-1">
                                ${getDemoIndicatorHTML(account)}
                                ${account.name}
                            </h6>
                            <p class="text-muted mb-1">U.S. Treasury</p>
                            <small class="text-muted">
                                Purchase: ${formatCurrency(account.purchase_amount)} |
                                Fixed Rate: ${account.fixed_rate}% |
                                Held: ${yearsHeld} years
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(account.current_value)}</h5>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('I_BONDS', '${account.id}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteAccount('${account.id}')" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Loading States
function showLoading(element) {
    element.classList.add('loading');
}

function hideLoading(element) {
    element.classList.remove('loading');
}

function showLoadingState() {
    const networthElement = document.getElementById('networthAmount');
    if (networthElement) {
        networthElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    }
}

function hideLoadingState() {
    // Loading state will be cleared when data is updated
}

// Additional Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Enhanced notification system with auto-dismiss and stacking
function showNotification(message, type = 'info', duration = 5000) {
    // Remove existing notifications of the same type to prevent stacking
    const existingAlerts = document.querySelectorAll(`.alert-${type}`);
    existingAlerts.forEach(alert => {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        bsAlert.close();
    });

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getNotificationIcon(type)} me-2"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto-dismiss after specified duration
    if (duration > 0) {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            bsAlert.close();
        }, duration);
    }
}

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Keyboard shortcuts
document.addEventListener('keydown', function (event) {
    // Ctrl/Cmd + R: Refresh data
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        refreshNetworth();
    }

    // Ctrl/Cmd + E: Export data
    if ((event.ctrlKey || event.metaKey) && event.key === 'e') {
        event.preventDefault();
        exportData();
    }

    // Ctrl/Cmd + I: Import data
    if ((event.ctrlKey || event.metaKey) && event.key === 'i') {
        event.preventDefault();
        showImportModal();
    }

    // Escape: Close modals
    if (event.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// Auto-save functionality for forms (debounced)
const debouncedAutoSave = debounce(function (formData, accountType) {
    // Only auto-save if form is valid and has an account ID (editing existing account)
    if (formData.account_id && formData.account_id.trim() !== '') {
        console.log('Auto-saving account data...', accountType);
        // Could implement auto-save here if needed
    }
}, 2000);

// Enhanced error handling with retry functionality
function handleApiError(error, retryFunction = null) {
    console.error('API Error:', error);

    let message = 'An unexpected error occurred.';
    let showRetry = false;

    if (error.message) {
        message = error.message;
    } else if (error.status === 401) {
        message = 'Your session has expired. Please log in again.';
        // Could redirect to login page
    } else if (error.status === 403) {
        message = 'You do not have permission to perform this action.';
    } else if (error.status === 404) {
        message = 'The requested resource was not found.';
    } else if (error.status >= 500) {
        message = 'Server error. Please try again later.';
        showRetry = true;
    } else if (!navigator.onLine) {
        message = 'No internet connection. Please check your connection and try again.';
        showRetry = true;
    }

    if (showRetry && retryFunction) {
        const retryButton = `<button class="btn btn-sm btn-outline-primary ms-2" onclick="${retryFunction}">Retry</button>`;
        showNotification(message + retryButton, 'danger', 0); // Don't auto-dismiss
    } else {
        showNotification(message, 'danger');
    }
}

// Performance monitoring
const performanceMonitor = {
    startTime: null,

    start(operation) {
        this.startTime = performance.now();
        console.log(`Starting ${operation}...`);
    },

    end(operation) {
        if (this.startTime) {
            const duration = performance.now() - this.startTime;
            console.log(`${operation} completed in ${duration.toFixed(2)}ms`);
            this.startTime = null;
        }
    }
};

// Initialize performance monitoring for data loading
const originalLoadAccountData = loadAccountData;
loadAccountData = function () {
    performanceMonitor.start('Account Data Load');
    const result = originalLoadAccountData.apply(this, arguments);

    // Monitor the promise if it returns one
    if (result && typeof result.finally === 'function') {
        result.finally(() => performanceMonitor.end('Account Data Load'));
    } else {
        performanceMonitor.end('Account Data Load');
    }

    return result;
};

// Connection status monitoring
window.addEventListener('online', function () {
    showNotification('Connection restored. Data will be synchronized.', 'success');
    loadAccountData();
});

window.addEventListener('offline', function () {
    showNotification('Connection lost. You can continue working offline, but stock prices won\'t update.', 'warning', 10000);
});

// Initialize connection status
if (!navigator.onLine) {
    showNotification('You are currently offline. Stock price updates are disabled.', 'info');
}

console.log('Networth Tracker JavaScript fully loaded and initialized');