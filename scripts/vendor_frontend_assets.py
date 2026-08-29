#!/usr/bin/env python3
"""
Download and vendor third-party frontend assets for offline/local-only runtime.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STATIC_VENDOR = ROOT / "static" / "vendor"

ASSETS = {
    "bootstrap/css/bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
    "bootstrap/js/bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js",
    "fontawesome/css/all.min.css": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
    "fontawesome/webfonts/fa-solid-900.woff2": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.woff2",
    "fontawesome/webfonts/fa-solid-900.ttf": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/fa-solid-900.ttf",
    "chartjs/chart.umd.min.js": "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js",
}

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Cormorant+Garamond:wght@400;500;600;700"
    "&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700"
    "&family=Inter:wght@300;400;500;600;700;800"
    "&family=JetBrains+Mono:wght@400;500;600"
    "&display=swap"
)

FONT_DESTINATIONS = {
    "Cormorant Garamond": ("cormorant-garamond", "Cormorant Garamond"),
    "DM Sans": ("dm-sans", "DM Sans"),
    "Inter": ("inter", "Inter"),
    "JetBrains Mono": ("jetbrains-mono", "JetBrains Mono"),
}


def download(
    url: str, destination: Path, headers: dict[str, str] | None = None
) -> None:
    """Download URL contents after validating only http/https schemes are used (B310 mitigation)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            "Only http and https schemes are permitted."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request) as response:  # nosec B310 - scheme validated above
        destination.write_bytes(response.read())


def vendor_google_fonts() -> None:
    headers = {"User-Agent": "Mozilla/5.0"}
    # Validate scheme for direct urlopen (B310 mitigation)
    parsed = urllib.parse.urlparse(GOOGLE_FONTS_URL)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            "Only http and https schemes are permitted."
        )
    request = urllib.request.Request(GOOGLE_FONTS_URL, headers=headers)
    with urllib.request.urlopen(request) as response:  # nosec B310 - scheme validated above
        css = response.read().decode("utf-8")

    font_face_blocks: list[str] = []
    for block in css.split("@font-face"):
        if "fonts.gstatic.com" not in block:
            continue

        family_match = re.search(r"font-family:\s*'([^']+)'", block)
        weight_match = re.search(r"font-weight:\s*(\d+)", block)
        url_match = re.search(r"url\((https://[^)]+)\)\s+format\('([^']+)'\)", block)
        if not (family_match and weight_match and url_match):
            continue

        family = family_match.group(1)
        weight = weight_match.group(1)
        font_url = url_match.group(1)
        font_format = url_match.group(2)

        if family not in FONT_DESTINATIONS:
            continue

        folder_name, css_family = FONT_DESTINATIONS[family]
        font_dir = STATIC_VENDOR / "fonts" / folder_name
        extension = Path(font_url).suffix or ".bin"
        file_name = f"{folder_name}-{weight}{extension}"
        download(font_url, font_dir / file_name, headers=headers)

        font_face_blocks.append(
            "\n".join(
                [
                    "@font-face {",
                    f"    font-family: '{css_family}';",
                    "    font-style: normal;",
                    f"    font-weight: {weight};",
                    "    font-display: swap;",
                    f"    src: url('../{folder_name}/{file_name}') format('{font_format}');",
                    "}",
                ]
            )
        )

    if not font_face_blocks:
        raise RuntimeError("No local Google Font assets were generated")

    fonts_css_path = STATIC_VENDOR / "fonts" / "css" / "fonts.css"
    fonts_css_path.parent.mkdir(parents=True, exist_ok=True)
    fonts_css_path.write_text("\n\n".join(font_face_blocks) + "\n", encoding="utf-8")


def main() -> None:
    for relative_path, url in ASSETS.items():
        download(url, STATIC_VENDOR / relative_path)

    vendor_google_fonts()


if __name__ == "__main__":
    main()
