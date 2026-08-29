"""Regression tests for browser request protections."""

import io
from unittest.mock import MagicMock, patch

import app as app_module


def _authenticated_manager():
    manager = MagicMock()
    manager.is_setup_required.return_value = False
    manager.is_authenticated.return_value = True
    manager.require_authentication.return_value = True
    manager.get_database_service.return_value = MagicMock()
    manager.get_encryption_service.return_value = MagicMock()
    return manager


def test_api_post_requires_valid_csrf_token():
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    manager = _authenticated_manager()

    with patch.object(app_module, "auth_manager", manager):
        with app_module.app.test_client() as client:
            client.get("/health")
            missing = client.post("/api/accounts", json={})
            assert missing.status_code == 400
            assert missing.get_json()["code"] == "SEC_CSRF_TOKEN"

            with client.session_transaction() as session:
                token = session["_csrf_token"]
            accepted = client.post(
                "/api/accounts",
                json={},
                headers={"X-CSRF-Token": token},
            )
            assert accepted.status_code == 400
            assert accepted.get_json()["code"] != "SEC_CSRF_TOKEN"


def test_backup_upload_honors_explicit_size_limit():
    app_module.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        MAX_BACKUP_SIZE=16,
    )
    manager = _authenticated_manager()

    with patch.object(app_module, "auth_manager", manager):
        with app_module.app.test_client() as client:
            response = client.post(
                "/api/import",
                data={
                    "backup_file": (
                        io.BytesIO(b"x" * 32),
                        "oversized.nwb",
                    )
                },
            )

    assert response.status_code == 413
    assert response.get_json()["code"] == "HTTP_413"
