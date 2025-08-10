# 401K Tab Selector Fix

## Problem
The 401K tab was causing a JavaScript error: `Uncaught SyntaxError: Failed to execute 'querySelector' on 'Document': '#401k' is not a valid selector.`

This occurred because CSS selectors cannot start with a number, and the tab had `id="401k"` which creates an invalid selector when referenced as `#401k`.

## Root Cause
- Tab button had `data-bs-target="#401k"`
- Tab pane had `id="401k"`
- JavaScript was trying to use `document.getElementById('401k-tab')` and similar selectors
- CSS selectors starting with numbers are invalid in CSS/JavaScript

## Solution
Changed all 401K-related IDs to use valid CSS selector names:

### Template Changes (templates/dashboard.html)
1. **Tab Button**: Changed from `id="401k-tab"` and `data-bs-target="#401k"` to:
   - `id="retirement401k-tab"`
   - `data-bs-target="#retirement401k"`

2. **Tab Pane**: Changed from `id="401k"` to:
   - `id="retirement401k"`

3. **Accounts List Container**: Changed from `id="401kAccountsList"` to:
   - `id="retirement401kAccountsList"`

4. **Account Type Card Click Handler**: Updated the inline JavaScript to handle the special case:
   ```javascript
   // Handle special case for 401K to avoid invalid selector
   let tabId;
   if (type === '401K') {
       tabId = 'retirement401k-tab';
   } else {
       tabId = type.toLowerCase() + '-tab';
   }
   ```

### JavaScript Changes (static/js/app.js)
1. **showAccountTab Function**: Updated the tabMap to use the new ID:
   ```javascript
   const tabMap = {
       'CD': 'cd-tab',
       'SAVINGS': 'savings-tab',
       '401K': 'retirement401k-tab',  // Changed from '401k-tab'
       'TRADING': 'trading-tab',
       'I_BONDS': 'ibonds-tab'
   };
   ```

2. **update401kAccountsList Function**: Updated to reference the new container ID:
   ```javascript
   const container = document.getElementById('retirement401kAccountsList');
   ```

## What Remained Unchanged
- Account type card `data-type="401K"` - still correct
- `401kTotal` ID for the summary display - still valid (doesn't start with number)
- All other 401K-related functionality and data handling

## Result
- 401K tab now works correctly without JavaScript errors
- All tab switching functionality works properly
- Account type cards correctly navigate to the 401K tab
- Summary table "View Details" buttons work for 401K accounts
- No impact on other account types or functionality

## CSS Selector Naming Best Practices
- Never start IDs or class names with numbers
- Use descriptive prefixes like `retirement401k` instead of `401k`
- Consider using camelCase or kebab-case for multi-word identifiers
- Always test selectors in browser console before implementing