"""Shared pytest fixtures and global-state isolation.

The Flask app in ``app.py`` keeps a module-level ``auth_manager`` singleton
(referenced directly by the route functions) and mirrors it on
``app.auth_manager`` (used by the error handlers). Different test modules
manipulate this singleton in incompatible ways:

* Some rebind the module attribute: ``app_module.auth_manager = AuthenticationManager(...)``
* Others re-initialise an imported reference: ``from app import auth_manager; auth_manager.__init__(...)``

Without isolation, a "rebinding" test leaves the module global pointing at a
stale instance (often backed by an already-deleted temp database), which then
breaks the next test that relies on the original imported reference. The
autouse fixture below snapshots the singleton and the mutated config keys
before every test and restores them afterwards, so test ordering no longer
matters.
"""

import pytest

import app as app_module


# Config keys that individual tests overwrite in their setup and that must be
# restored so later tests see the app's original configuration.
_MUTATED_CONFIG_KEYS = (
    "TESTING",
    "DATABASE_PATH",
    "SECRET_KEY",
    "WTF_CSRF_ENABLED",
)


@pytest.fixture(autouse=True)
def _isolate_global_state():
    """Restore the shared ``auth_manager`` singleton and config after each test."""
    original_auth = app_module.auth_manager
    original_app_auth = getattr(app_module.app, "auth_manager", original_auth)
    saved_config = {key: app_module.app.config.get(key) for key in _MUTATED_CONFIG_KEYS}
    config_present = {key: key in app_module.app.config for key in _MUTATED_CONFIG_KEYS}

    # Existing route tests focus on their route contract rather than CSRF.
    # Security-specific tests explicitly re-enable it when exercising the
    # middleware.
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    yield

    # Restore the singleton on both the module global (used by routes) and the
    # app attribute (used by error handlers) so they never diverge.
    app_module.auth_manager = original_auth
    app_module.app.auth_manager = original_app_auth

    for key in _MUTATED_CONFIG_KEYS:
        if config_present[key]:
            app_module.app.config[key] = saved_config[key]
        else:
            app_module.app.config.pop(key, None)
