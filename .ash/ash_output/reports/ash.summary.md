# ASH Security Scan Report

- **Report generated**: 2025-09-09T13:25:00+00:00
- **Time since scan**: 0 minutes

## Scan Metadata

- **Project**: ASH
- **Scan executed**: 2025-09-09T13:24:11+00:00
- **ASH version**: 3.0.0

## Summary

### Scanner Results

The table below shows findings by scanner, with status based on severity thresholds and dependencies:

- **Severity levels**:
  - **Suppressed (S)**: Findings that have been explicitly suppressed and don't affect scanner status
  - **Critical (C)**: Highest severity findings that require immediate attention
  - **High (H)**: Serious findings that should be addressed soon
  - **Medium (M)**: Moderate risk findings
  - **Low (L)**: Lower risk findings
  - **Info (I)**: Informational findings with minimal risk
- **Duration (Time)**: Time taken by the scanner to complete its execution
- **Actionable**: Number of findings at or above the threshold severity level that require attention
- **Result**:
  - **PASSED** = No findings at or above threshold
  - **FAILED** = Findings at or above threshold
  - **MISSING** = Required dependencies not available
  - **SKIPPED** = Scanner explicitly disabled
  - **ERROR** = Scanner execution error
- **Threshold**: The minimum severity level that will cause a scanner to fail
  - Thresholds: ALL, LOW, MEDIUM, HIGH, CRITICAL
  - Source: Values in parentheses indicate where the threshold is set:
    - `global` (global_settings section in the ASH_CONFIG used)
    - `config` (scanner config section in the ASH_CONFIG used)
    - `scanner` (default configuration in the plugin, if explicitly set)
- **Statistics calculation**:
  - All statistics are calculated from the final aggregated SARIF report
  - Suppressed findings are counted separately and do not contribute to actionable findings
  - Scanner status is determined by comparing actionable findings to the threshold

| Scanner | Suppressed | Critical | High | Medium | Low | Info | Actionable | Result | Threshold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| bandit | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SKIPPED | MEDIUM (global) |
| cdk-nag | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SKIPPED | MEDIUM (global) |
| cfn-nag | 0 | 0 | 0 | 0 | 0 | 0 | 0 | MISSING | MEDIUM (global) |
| checkov | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SKIPPED | MEDIUM (global) |
| detect-secrets | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SKIPPED | MEDIUM (global) |
| grype | 0 | 0 | 0 | 0 | 0 | 0 | 0 | MISSING | MEDIUM (global) |
| npm-audit | 0 | 0 | 0 | 0 | 0 | 0 | 0 | SKIPPED | MEDIUM (global) |
| opengrep | 0 | 0 | 0 | 0 | 0 | 0 | 0 | MISSING | MEDIUM (global) |
| semgrep | 7 | 15 | 0 | 0 | 0 | 0 | 15 | FAILED | MEDIUM (global) |
| syft | 0 | 0 | 0 | 0 | 0 | 0 | 0 | MISSING | MEDIUM (global) |

### Top 2 Hotspots

Files with the highest number of security findings:

| Finding Count | File Location |
| ---: | --- |
| 14 | static/js/app.js |
| 1 | app.py |

<h2>Detailed Findings</h2>

<details>
<summary>Show 15 actionable findings</summary>

### Finding 1: python.flask.security.audit.debug-enabled.debug-enabled

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: python.flask.security.audit.debug-enabled.debug-enabled
- **Location**: app.py:3298-3303

**Description**:
Detected Flask app with debug=True. Do not deploy to production with this flag enabled as it will leak sensitive information. Instead, consider using Flask configuration variables or setting 'debug' using system environment variables.

**Code Snippet**:
```
app.run(
        host='127.0.0.1',  # Localhost only for security
        port=5000,
        debug=True,
        threaded=True
    )
```

---

### Finding 2: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:56-61

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
demoAccountsList.innerHTML = demoAccounts.map(account => `
        <li class="mb-1">
            <i class="fas fa-flask demo-icon"></i>
            <strong>${account.name}</strong> (${account.institution})
        </li>
    `).join('');
```

---

### Finding 3: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:100

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
button.innerHTML = originalText;
```

---

### Finding 4: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:177

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
container.innerHTML = html;
```

---

### Finding 5: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:381

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
submitButton.innerHTML = originalText;
```

---

### Finding 6: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:680

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
button.innerHTML = originalText;
```

---

### Finding 7: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:719

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
button.innerHTML = originalText;
```

---

### Finding 8: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:804

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
button.innerHTML = originalText;
```

---

### Finding 9: typescript.react.security.audit.react-unsanitized-method.react-unsanitized-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: typescript.react.security.audit.react-unsanitized-method.react-unsanitized-method
- **Location**: static/js/app.js:1552

**Description**:
Detection of insertAdjacentHTML from non-constant definition. This can inadvertently expose users to cross-site scripting (XSS) attacks if this comes from user-provided input. If you have to use insertAdjacentHTML, consider using a sanitization library such as DOMPurify to sanitize your HTML.

**Code Snippet**:
```
document.body.insertAdjacentHTML('beforeend', modalHTML);
```

---

### Finding 10: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:1640

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
demoIndicator.innerHTML = getDemoIndicatorHTML(account);
```

---

### Finding 11: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:1749

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
demoIndicator.innerHTML = getDemoIndicatorHTML(account);
```

---

### Finding 12: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:1874

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
container.innerHTML = html;
```

---

### Finding 13: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:1954

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
container.innerHTML = html;
```

---

### Finding 14: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:2020

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
container.innerHTML = html;
```

---

### Finding 15: javascript.browser.security.insecure-document-method.insecure-document-method

- **Severity**: HIGH
- **Scanner**: semgrep
- **Rule ID**: javascript.browser.security.insecure-document-method.insecure-document-method
- **Location**: static/js/app.js:2090

**Description**:
User controlled data in methods like `innerHTML`, `outerHTML` or `document.write` is an anti-pattern that can lead to XSS vulnerabilities

**Code Snippet**:
```
container.innerHTML = html;
```

</details>

---

*Report generated by [Automated Security Helper (ASH)](https://github.com/awslabs/automated-security-helper) at 2025-09-09T13:25:00+00:00*