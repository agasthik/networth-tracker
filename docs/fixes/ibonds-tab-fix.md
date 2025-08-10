# I-Bonds Tab Selector Fix

## Problem
Clicking on the I-Bonds account type card was causing a JavaScript error:
```
TypeError: Cannot read properties of null (reading 'click')
```

This occurred because the JavaScript was trying to click on a tab element that didn't exist.

## Root Cause
The I-Bonds account type card has `data-type="I_BONDS"`, and the JavaScript click handler was creating a tab ID by doing:
```javascript
tabId = type.toLowerCase() + '-tab';
```

This resulted in `i_bonds-tab`, but the actual tab ID is `ibonds-tab` (without the underscore).

## Solution
Updated both the dashboard template and JavaScript to properly handle the I_BONDS case:

### Template Changes (templates/dashboard.html)
Updated the account type card click handler to include a special case for I_BONDS:
```javascript
// Handle special cases for tab ID mapping
let tabId;
if (type === '401K') {
    tabId = 'retirement401k-tab';
} else if (type === 'I_BONDS') {
    tabId = 'ibonds-tab';
} else {
    tabId = type.toLowerCase() + '-tab';
}
const tabElement = document.getElementById(tabId);
if (tabElement) {
    tabElement.click();
} else {
    console.error('Tab element not found:', tabId);
}
```

### JavaScript Changes (static/js/app.js)
Updated the `showAccountTab` function to include better error handling:
```javascript
function showAccountTab(accountType) {
    const tabMap = {
        'CD': 'cd-tab',
        'SAVINGS': 'savings-tab',
        '401K': 'retirement401k-tab',
        'TRADING': 'trading-tab',
        'I_BONDS': 'ibonds-tab'  // Correctly maps to 'ibonds-tab'
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
```

## Account Type to Tab ID Mapping
The correct mapping for all account types:
- `CD` → `cd-tab`
- `SAVINGS` → `savings-tab`
- `401K` → `retirement401k-tab` (special case due to invalid CSS selector)
- `TRADING` → `trading-tab`
- `I_BONDS` → `ibonds-tab` (special case due to underscore in data-type)

## Error Handling Improvements
- Added null checks before calling `.click()`
- Added console error messages for debugging
- Proper error handling for missing tab elements

## Result
- ✅ I-Bonds account type card now works correctly
- ✅ Clicking I-Bonds card navigates to the correct tab
- ✅ "View Details" buttons work for I-Bonds accounts in summary table
- ✅ Better error handling and debugging information
- ✅ All other account types continue to work properly

## Lessons Learned
- Account type data attributes should match tab IDs when possible
- Special cases need explicit handling in JavaScript
- Always include null checks when manipulating DOM elements
- Consistent naming conventions prevent these issues