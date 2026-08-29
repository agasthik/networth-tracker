"""Regression coverage for page-scoped frontend initialization."""

from pathlib import Path


def test_dashboard_api_initialization_is_guarded_by_dashboard_marker():
    source = (Path(__file__).parents[1] / "static" / "js" / "app.js").read_text()
    initialize_app = source.split(
        "function initializeApp() {",
        1,
    )[1].split(
        "function isDashboardPage()",
        1,
    )[0]

    guard_position = initialize_app.index("if (!isDashboardPage())")
    account_load_position = initialize_app.index("loadAccountData();")
    refresh_position = initialize_app.index("setInterval(updateStockPrices")

    assert guard_position < account_load_position
    assert guard_position < refresh_position
    assert "document.getElementById('networthAmount')" in source


def test_add_account_menu_redirects_to_dashboard_when_modal_is_unavailable():
    root = Path(__file__).parents[1]
    source = (root / "static" / "js" / "app.js").read_text()
    base_template = (root / "templates" / "base.html").read_text()

    show_account_form = source.split(
        "function showAccountForm(accountType, accountId = null) {",
        1,
    )[1].split(
        "function openRequestedAccountForm()",
        1,
    )[0]

    assert "if (!modalElement || !title || !body)" in show_account_form
    assert "window.location.assign(" in show_account_form
    assert "/dashboard?add_account=" in show_account_form
    assert "openRequestedAccountForm();" in source
    assert 'href="#" onclick="showAccountForm' not in base_template
    assert "onclick=\"return showAccountForm('CD')\"" in base_template
