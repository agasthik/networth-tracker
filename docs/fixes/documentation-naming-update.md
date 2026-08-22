# Documentation Naming Update

> Historical note: this file originally recorded a one-time rename. The
> directory has gained more documents since then, and `RESTART_USAGE.md`
> remains an uppercase legacy filename.

## Naming Convention

New topic documents should use lowercase kebab-case. `README.md` is the normal
index-file exception. Existing links should be updated whenever a file is
renamed.

## Current Structure

```text
docs/
├── README.md
├── RESTART_USAGE.md
├── configuration.md
├── demo-data.md
├── deployment.md
├── error-handling-guide.md
├── faq.md
├── installation.md
├── quick-start.md
├── security.md
├── troubleshooting.md
├── user-guide.md
├── scripts/
│   └── README.md
└── fixes/
    ├── 401k-tab-fix.md
    ├── documentation-naming-update.md
    ├── font-improvements.md
    └── ibonds-tab-fix.md
```

The current tree, rather than the original rename list, is authoritative.
Relative links between the active guides are validated as part of documentation
maintenance.
