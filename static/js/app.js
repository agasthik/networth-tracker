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

// Demo filter state
let demoFilterActive = false;

// Demo Account Management Functions
function toggleDemoFilter() {
    demoFilterActive = !demoFilterActive;
    const filterText = document.getElementById('demoFilterText');

    if (demoFilterActive) {
        filterText.textContent = 'Show All';
        // Filter to show only demo accounts
        filterAccountsByDemo(true);
    } else {
        filterText.textContent = 'Show Demo Only';
        // Show all accounts
        filterAccountsByDemo(false);
    }
}

function filterAccountsByDemo(demoOnly) {
    // This will filter the account displays based on demo status
    // Implementation will be added when account rendering is updated
    console.log('Filtering accounts by demo status:', demoOnly);

    // Update account tabs with filtered data
    updateAccountTabs();
}

function confirmDeleteDemoAccounts() {
    // Get demo accounts from current state
    const demoAccounts = AppState.accounts.filter(account => account.is_demo);

    if (demoAccounts.length === 0) {
        showNotification('No demo accounts found to delete.', 'info');
        return;
    }

    // Update modal with demo account information
    document.getElementById('confirmDemoCount').textContent = demoAccounts.length;

    const demoAccountsList = document.getElementById('demoAccountsList');
    demoAccountsList.innerHTML = demoAccounts.map(account => `
        <li class="mb-1">
            <i class="fas fa-flask demo-icon"></i>
            <strong>${account.name}</strong> (${account.institution})
        </li>
    `).join('');

    // Show confirmation modal
    const modal = new bootstrap.Modal(document.getElementById('deleteDemoAccountsModal'));
    modal.show();
}

function deleteDemoAccounts() {
    // Show loading state
    const button = document.querySelector('button[onclick="deleteDemoAccounts()"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Deleting...';
    button.disabled = true;

    fetch('/api/demo/accounts', {
        method: 'DELETE'
    })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            showNotification(`Successfully deleted ${data.deleted_count} demo accounts.`, 'success');

            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteDemoAccountsModal'));
            modal.hide();

            // Refresh account data
            loadAccountData();
        })
        .catch(error => {
            console.error('Error deleting demo accounts:', error);
            showNotification('Failed to delete demo accounts. Please try again.', 'error');
        })
        .finally(() => {
            // Reset button state
            button.innerHTML = originalText;
            button.disabled = false;
        });
}

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
        'I_BONDS': 'I-Bonds Account',
        'HSA': 'HSA Account'
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
        'I_BONDS': '/templates/accounts/ibonds_form.html',
        'HSA': '/templates/accounts/hsa_form.html'
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

            // Create error alert safely
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';

            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle me-2';

            const mainText = document.createTextNode('Error loading account form. Please try again.');
            const lineBreak = document.createElement('br');

            const smallText = document.createElement('small');
            smallText.className = 'text-muted';
            smallText.textContent = `Error: ${error.message}`;

            errorDiv.appendChild(icon);
            errorDiv.appendChild(mainText);
            errorDiv.appendChild(lineBreak);
            errorDiv.appendChild(smallText);

            // Clear container and add error message
            container.innerHTML = '';
            container.appendChild(errorDiv);
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

    // Safely set text content to prevent XSS
    alertDiv.textContent = message;

    // Create and append close button safely
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');

    alertDiv.appendChild(closeButton);

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
        I_BONDS: 0,
        HSA: 0
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
            case 'HSA':
                accountValue = account.current_balance || 0;
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
                type === 'HSA' ? 'hsaTotal' :
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

    // Note: Summary table is populated by loadPortfolioSummary() which has more complete data including monthly changes

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
    updateHSAAccountsList();
}

function showAccountTab(accountType) {
    const tabMap = {
        'CD': 'cd-tab',
        'SAVINGS': 'savings-tab',
        '401K': 'retirement401k-tab',
        'TRADING': 'trading-tab',
        'I_BONDS': 'ibonds-tab',
        'HSA': 'hsa-tab'
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

            // Load watchlist summary
            console.log('About to call loadSimpleWatchlistSummary');
            if (typeof loadSimpleWatchlistSummary === 'function') {
                setTimeout(() => {
                    loadSimpleWatchlistSummary();
                }, 500);
            } else {
                console.warn('loadSimpleWatchlistSummary function not found');
            }
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

        case 'HSA':
            if (!accountData.current_balance || parseFloat(accountData.current_balance) < 0) {
                errors.push('Current balance must be 0 or greater.');
                isValid = false;
            }
            if (!accountData.annual_contribution_limit || parseFloat(accountData.annual_contribution_limit) < 0) {
                errors.push('Annual contribution limit must be 0 or greater.');
                isValid = false;
            }
            if (!accountData.current_year_contributions || parseFloat(accountData.current_year_contributions) < 0) {
                errors.push('Current year contributions must be 0 or greater.');
                isValid = false;
            }
            if (!accountData.investment_balance || parseFloat(accountData.investment_balance) < 0) {
                errors.push('Investment balance must be 0 or greater.');
                isValid = false;
            }
            if (!accountData.cash_balance || parseFloat(accountData.cash_balance) < 0) {
                errors.push('Cash balance must be 0 or greater.');
                isValid = false;
            }
            // Validate that investment + cash = current balance
            const currentBalance = parseFloat(accountData.current_balance) || 0;
            const investmentBalance = parseFloat(accountData.investment_balance) || 0;
            const cashBalance = parseFloat(accountData.cash_balance) || 0;
            if (Math.abs((investmentBalance + cashBalance) - currentBalance) > 0.01) {
                errors.push('Investment balance plus cash balance must equal current balance.');
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

        // Clear and rebuild safely
        networthChange.innerHTML = '';

        const icon = document.createElement('i');
        icon.className = `fas fa-arrow-${isPositive ? 'up' : 'down'} text-${isPositive ? 'success' : 'danger'}`;

        const changeText = document.createTextNode(` ${isPositive ? '+' : ''}${formatCurrency(change)} (${changePercent.toFixed(2)}%)`);

        networthChange.appendChild(icon);
        networthChange.appendChild(changeText);
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
            'I_BONDS': 'I-Bonds Treasury',
            'HSA': 'Health Savings Accounts'
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

                // Create table row safely
                const row = document.createElement('tr');

                // Account type cell
                const typeCell = document.createElement('td');
                const strongEl = document.createElement('strong');
                strongEl.textContent = accountTypeNames[type] || 'Unknown';
                const brEl = document.createElement('br');
                const smallEl = document.createElement('small');
                smallEl.className = 'text-muted';
                smallEl.textContent = `${typeData.count} account${typeData.count > 1 ? 's' : ''}`;
                typeCell.appendChild(strongEl);
                typeCell.appendChild(brEl);
                typeCell.appendChild(smallEl);

                // Value cell
                const valueCell = document.createElement('td');
                valueCell.textContent = formatCurrency(typeData.value);

                // Percentage cell
                const percentageCell = document.createElement('td');
                percentageCell.textContent = `${percentage.toFixed(1)}%`;

                // Change cell
                const changeCell = document.createElement('td');
                changeCell.className = monthlyChange >= 0 ? 'text-success' : 'text-danger';
                changeCell.textContent = `${monthlyChange >= 0 ? '+' : ''}${formatCurrency(monthlyChange)}`;

                // Action cell
                const actionCell = document.createElement('td');
                const button = document.createElement('button');
                button.className = 'btn btn-sm btn-outline-primary';
                button.textContent = 'View Details';
                button.onclick = () => showAccountTab(type);
                actionCell.appendChild(button);

                // Append all cells
                row.appendChild(typeCell);
                row.appendChild(valueCell);
                row.appendChild(percentageCell);
                row.appendChild(changeCell);
                row.appendChild(actionCell);

                summaryTableBody.appendChild(row);
            }
        });

        // summaryTableBody is populated above with DOM elements
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
        'I_BONDS': '#6c757d',  // secondary
        'HSA': '#007bff'       // primary
    };

    const typeNames = {
        'CD': 'CDs',
        'SAVINGS': 'Savings',
        '401K': '401k',
        'TRADING': 'Trading',
        'I_BONDS': 'I-Bonds',
        'HSA': 'HSA'
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

    // Portfolio summary list widget removed - information available in table below
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

    // Clear container
    container.innerHTML = '';

    activities.forEach(activity => {
        const isPositive = activity.change >= 0;
        const typeIcons = {
            'CD': 'fas fa-certificate',
            'SAVINGS': 'fas fa-piggy-bank',
            '401K': 'fas fa-briefcase',
            'TRADING': 'fas fa-chart-bar',
            'I_BONDS': 'fas fa-university'
        };

        // Create activity item safely
        const itemDiv = document.createElement('div');
        itemDiv.className = 'list-group-item list-group-item-action border-0 px-0';

        const mainDiv = document.createElement('div');
        mainDiv.className = 'd-flex justify-content-between align-items-center';

        // Left side
        const leftDiv = document.createElement('div');
        leftDiv.className = 'd-flex align-items-center';

        const icon = document.createElement('i');
        icon.className = `${typeIcons[activity.type] || 'fas fa-question'} text-muted me-2`;

        const textDiv = document.createElement('div');

        const accountName = document.createElement('small');
        accountName.className = 'fw-bold';
        accountName.textContent = activity.account_name || 'Unknown Account';

        const lineBreak = document.createElement('br');

        const institution = document.createElement('small');
        institution.className = 'text-muted';
        institution.textContent = activity.institution || 'Unknown Institution';

        textDiv.appendChild(accountName);
        textDiv.appendChild(lineBreak);
        textDiv.appendChild(institution);

        leftDiv.appendChild(icon);
        leftDiv.appendChild(textDiv);

        // Right side
        const rightDiv = document.createElement('div');
        rightDiv.className = 'text-end';

        const changeAmount = document.createElement('small');
        changeAmount.className = isPositive ? 'text-success' : 'text-danger';
        changeAmount.textContent = `${isPositive ? '+' : ''}${formatCurrency(activity.change)}`;

        const lineBreak2 = document.createElement('br');

        const changePercent = document.createElement('small');
        changePercent.className = 'text-muted';
        changePercent.textContent = `${activity.change_percent.toFixed(1)}%`;

        rightDiv.appendChild(changeAmount);
        rightDiv.appendChild(lineBreak2);
        rightDiv.appendChild(changePercent);

        // Assemble
        mainDiv.appendChild(leftDiv);
        mainDiv.appendChild(rightDiv);
        itemDiv.appendChild(mainDiv);

        container.appendChild(itemDiv);
    });
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

    // Clear container
    container.innerHTML = '';

    cdAccounts.forEach(account => {
        const maturityDate = new Date(account.maturity_date);
        const daysToMaturity = Math.ceil((maturityDate - new Date()) / (1000 * 60 * 60 * 24));

        // Create card element safely
        const cardDiv = document.createElement('div');
        cardDiv.className = `card mb-3 ${getDemoCardClass(account)}`;

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const row = document.createElement('div');
        row.className = 'row align-items-center';

        // Left column
        const leftCol = document.createElement('div');
        leftCol.className = 'col-md-8';

        const title = document.createElement('h6');
        title.className = 'card-title mb-1';
        // Create demo indicator safely - assuming getDemoIndicatorHTML returns safe HTML
        // If it contains user data, this should be refactored to use DOM methods
        const demoIndicator = document.createElement('span');
        demoIndicator.innerHTML = getDemoIndicatorHTML(account);
        title.appendChild(demoIndicator);
        title.appendChild(document.createTextNode(account.name || 'Unnamed Account'));

        const institution = document.createElement('p');
        institution.className = 'text-muted mb-1';
        institution.textContent = account.institution || 'Unknown Institution';

        const details = document.createElement('small');
        details.className = 'text-muted';
        details.textContent = `Principal: ${formatCurrency(account.principal_amount)} | Rate: ${account.interest_rate}% | Matures in ${daysToMaturity} days`;

        leftCol.appendChild(title);
        leftCol.appendChild(institution);
        leftCol.appendChild(details);

        // Value column
        const valueCol = document.createElement('div');
        valueCol.className = 'col-md-2 text-end';
        const valueH5 = document.createElement('h5');
        valueH5.className = 'mb-0';
        valueH5.textContent = formatCurrency(account.current_value);
        valueCol.appendChild(valueH5);

        // Actions column
        const actionsCol = document.createElement('div');
        actionsCol.className = 'col-md-2 text-end';

        // Details button
        const detailsBtn = document.createElement('button');
        detailsBtn.className = 'btn btn-sm btn-outline-info me-1';
        detailsBtn.title = 'View Details';
        detailsBtn.onclick = () => showAccountDetails(account.id);
        detailsBtn.innerHTML = '<i class="fas fa-chart-line"></i>';

        // Edit button
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.title = 'Edit';
        editBtn.onclick = () => showAccountForm('CD', account.id);
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';

        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.title = 'Delete';
        deleteBtn.onclick = () => deleteAccount(account.id);
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';

        actionsCol.appendChild(detailsBtn);
        actionsCol.appendChild(editBtn);
        actionsCol.appendChild(deleteBtn);

        // Assemble row
        row.appendChild(leftCol);
        row.appendChild(valueCol);
        row.appendChild(actionsCol);

        // Assemble card
        cardBody.appendChild(row);
        cardDiv.appendChild(cardBody);

        // Add to container
        container.appendChild(cardDiv);
    });
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

    // Clear container
    container.innerHTML = '';

    savingsAccounts.forEach(account => {
        // Create card element safely
        const cardDiv = document.createElement('div');
        cardDiv.className = `card mb-3 ${getDemoCardClass(account)}`;

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const row = document.createElement('div');
        row.className = 'row align-items-center';

        // Left column
        const leftCol = document.createElement('div');
        leftCol.className = 'col-md-8';

        const title = document.createElement('h6');
        title.className = 'card-title mb-1';
        const demoIndicator = document.createElement('span');
        demoIndicator.innerHTML = getDemoIndicatorHTML(account);
        title.appendChild(demoIndicator);
        title.appendChild(document.createTextNode(account.name || 'Unnamed Account'));

        const institution = document.createElement('p');
        institution.className = 'text-muted mb-1';
        institution.textContent = account.institution || 'Unknown Institution';

        const details = document.createElement('small');
        details.className = 'text-muted';
        details.textContent = `Interest Rate: ${account.interest_rate}%`;

        leftCol.appendChild(title);
        leftCol.appendChild(institution);
        leftCol.appendChild(details);

        // Value column
        const valueCol = document.createElement('div');
        valueCol.className = 'col-md-2 text-end';
        const valueH5 = document.createElement('h5');
        valueH5.className = 'mb-0';
        valueH5.textContent = formatCurrency(account.current_balance);
        valueCol.appendChild(valueH5);

        // Actions column
        const actionsCol = document.createElement('div');
        actionsCol.className = 'col-md-2 text-end';

        // Details button
        const detailsBtn = document.createElement('button');
        detailsBtn.className = 'btn btn-sm btn-outline-info me-1';
        detailsBtn.title = 'View Details';
        detailsBtn.onclick = () => showAccountDetails(account.id);
        detailsBtn.innerHTML = '<i class="fas fa-chart-line"></i>';

        // Edit button
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.title = 'Edit';
        editBtn.onclick = () => showAccountForm('SAVINGS', account.id);
        editBtn.innerHTML = '<i class="fas fa-edit"></i>';

        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger';
        deleteBtn.title = 'Delete';
        deleteBtn.onclick = () => deleteAccount(account.id);
        deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';

        actionsCol.appendChild(detailsBtn);
        actionsCol.appendChild(editBtn);
        actionsCol.appendChild(deleteBtn);

        // Assemble row
        row.appendChild(leftCol);
        row.appendChild(valueCol);
        row.appendChild(actionsCol);

        // Assemble card
        cardBody.appendChild(row);
        cardDiv.appendChild(cardBody);

        // Add to container
        container.appendChild(cardDiv);
    });
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

function updateHSAAccountsList() {
    const container = document.getElementById('hsaAccountsList');
    if (!container) return;

    const hsaAccounts = getFilteredAccounts(AppState.accounts, 'HSA');

    if (hsaAccounts.length === 0) {
        const emptyMessage = demoFilterActive ?
            'No demo HSA accounts found.' :
            'Add your Health Savings Account to track tax-advantaged healthcare savings.';

        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-medkit fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No HSA Accounts</h5>
                <p class="text-muted">${emptyMessage}</p>
            </div>
        `;
        return;
    }

    let html = '';
    hsaAccounts.forEach(account => {
        const contributionProgress = account.annual_contribution_limit > 0 ?
            (account.current_year_contributions / account.annual_contribution_limit * 100) : 0;
        const remainingCapacity = Math.max(0, account.annual_contribution_limit - account.current_year_contributions);

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
                                Contributions: ${formatCurrency(account.current_year_contributions)} / ${formatCurrency(account.annual_contribution_limit)}
                                (${contributionProgress.toFixed(1)}%) |
                                Remaining: ${formatCurrency(remainingCapacity)}
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <h5 class="mb-0">${formatCurrency(account.current_balance)}</h5>
                            <small class="text-muted">
                                Cash: ${formatCurrency(account.cash_balance)}<br>
                                Invested: ${formatCurrency(account.investment_balance)}
                            </small>
                        </div>
                        <div class="col-md-2 text-end">
                            <button class="btn btn-sm btn-outline-info me-1" onclick="showAccountDetails('${account.id}')" title="View Details">
                                <i class="fas fa-chart-line"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary me-1" onclick="showAccountForm('HSA', '${account.id}')" title="Edit">
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
    // Create content safely
    const contentDiv = document.createElement('div');
    contentDiv.className = 'd-flex align-items-center';

    const icon = document.createElement('i');
    icon.className = `fas fa-${getNotificationIcon(type)} me-2`;

    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;

    contentDiv.appendChild(icon);
    contentDiv.appendChild(messageSpan);

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');

    alertDiv.appendChild(contentDiv);
    alertDiv.appendChild(closeButton);

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

// Watchlist functionality is handled in dashboard template

console.log('Networth Tracker JavaScript fully loaded and initialized');