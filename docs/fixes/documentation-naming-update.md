# Documentation File Naming Standardization

## Overview
Updated all documentation files to use consistent **lowercase-with-hyphens** (kebab-case) naming convention, except for `README.md` files which conventionally use uppercase.

## File Renames Completed

### docs/ directory:
- `DEPLOYMENT.md` → `deployment.md`
- `ERROR_HANDLING_GUIDE.md` → `error-handling-guide.md`
- `INSTALLATION.md` → `installation.md`
- `USER_GUIDE.md` → `user-guide.md`

### docs/fixes/ directory:
- `401K_TAB_FIX.md` → `401k-tab-fix.md`
- `FONT_IMPROVEMENTS.md` → `font-improvements.md`
- `IBONDS_TAB_FIX.md` → `ibonds-tab-fix.md`

### Files that remained unchanged (already following convention):
- `configuration.md`
- `demo-data.md`
- `faq.md`
- `quick-start.md`
- `security.md`
- `troubleshooting.md`
- `README.md` (uppercase is conventional for README files)

## Cross-Reference Updates

Updated all internal documentation links in the following files:
- `README.md` (root)
- `docs/README.md`
- `docs/installation.md`
- `docs/quick-start.md`
- `docs/faq.md`
- `docs/troubleshooting.md`
- `.kiro/steering/structure.md`

## Final Documentation Structure

```
docs/
├── README.md                    # Main documentation index
├── configuration.md             # Configuration reference
├── demo-data.md                 # Demo database guide
├── deployment.md                # Production deployment guide
├── error-handling-guide.md      # Error handling and debugging
├── faq.md                       # Frequently asked questions
├── installation.md              # Installation instructions
├── quick-start.md               # Quick start guide
├── security.md                  # Security best practices
├── troubleshooting.md           # Troubleshooting guide
├── user-guide.md                # Complete user manual
└── fixes/                       # Technical fix documentation
    ├── 401k-tab-fix.md          # 401K tab selector fix
    ├── font-improvements.md     # Typography improvements
    └── ibonds-tab-fix.md        # I-Bonds tab selector fix
```

## Benefits of Consistent Naming

1. **Improved readability**: Lowercase with hyphens is easier to read
2. **URL-friendly**: Works well in web contexts and URLs
3. **Cross-platform compatibility**: Avoids case sensitivity issues
4. **Professional appearance**: Consistent with modern documentation standards
5. **Better organization**: Clear separation between user docs and technical fixes

## Naming Convention Rules Applied

- **Lowercase letters only** (except README.md)
- **Hyphens for word separation** (kebab-case)
- **Descriptive names** that clearly indicate content
- **Consistent suffixes** (.md for all markdown files)
- **Logical grouping** (technical fixes moved to fixes/ subdirectory)

All internal links have been updated to reflect the new file names, ensuring no broken references exist in the documentation.