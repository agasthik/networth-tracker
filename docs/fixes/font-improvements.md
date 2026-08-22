# Typography Update

> Historical note: the original typography change has since been revised. This
> file records the current typography state so it does not present the earlier
> Inter-based design as active.

## Current Fonts

The active stylesheet uses:

- **DM Sans** for interface text, controls, navigation, and body copy
- **Cormorant Garamond** for display headings and selected titles
- **JetBrains Mono** for currency, numeric, and code-like values

`Inter` remains available in the vendored font bundle but is not the primary
font in `static/css/styles.css`.

## Loading

Fonts are declared in `static/vendor/fonts/css/fonts.css` and loaded from local
files under `static/vendor/fonts/`. The current interface does not depend on
Google Fonts or another font CDN.

Local font loading supports the application's local-first operation. System
font fallbacks remain in the CSS for cases where a font asset cannot load.

## Source of Truth

Current typography variables and component rules are in:

- `static/css/styles.css`
- `static/vendor/fonts/css/fonts.css`

Those files supersede any implementation details from the original typography
change.
