from __future__ import annotations

from threading import Lock

from backend.services import audit_service as audit_module
from backend.services import auth_service as auth_module


def build_auth_service(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_module, "USER_DB_PATH", tmp_path / "users.json")
    monkeypatch.setattr(auth_module, "USER_DB_LOCK", Lock())
    monkeypatch.setattr(audit_module, "AUDIT_LOG_PATH", tmp_path / "audit_logs.jsonl")
    monkeypatch.setattr(
        auth_module.platform_service,
        "allow_registration",
        lambda: True,
    )
    monkeypatch.setattr(
        auth_module.platform_service,
        "get_policy",
        lambda: {
            "default_subscription_tier": "free",
        },
    )
    return auth_module.AuthService()


def test_role_permissions_and_last_admin_protection(tmp_path, monkeypatch):
    service = build_auth_service(tmp_path, monkeypatch)

    assert service.has_permission_for_role("support", "users.view") is True
    assert service.has_permission_for_role("support", "policy.edit") is False
    assert service.has_permission_for_role("operator", "api_config.edit") is True
    assert service.has_permission_for_role("customer", "backoffice.view") is False

    success, _, first_result = service.create_user("admin@example.com", "secret123", "admin")
    assert success is True
    assert first_result["user"]["role"] == "admin"

    success, _, second_result = service.create_user("staff@example.com", "secret123", "staff")
    assert success is True
    assert second_result["user"]["role"] == "customer"

    second_id = second_result["user"]["id"]
    success, message, updated = service.update_user_role(second_id, "support")
    assert success is True
    assert updated["role"] == "support"
    assert updated["role_name"] == "客服支持"
    assert "audit.view" in updated["permissions"]

    first_id = first_result["user"]["id"]
    success, message, updated = service.update_user_role(first_id, "operator")
    assert success is False
    assert message == "至少保留一个管理员账号"
    assert updated is None

    success, _, promoted = service.update_user_role(second_id, "admin")
    assert success is True
    assert promoted["role"] == "admin"

    success, _, demoted = service.update_user_role(first_id, "operator")
    assert success is True
    assert demoted["role"] == "operator"


def test_audit_log_masks_sensitive_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_module, "AUDIT_LOG_PATH", tmp_path / "audit_logs.jsonl")

    audit_module.audit_service.record(
        "admin.api_config.save",
        actor={"user_id": "u-1", "email": "admin@example.com", "role": "admin"},
        status="success",
        target_type="api_provider",
        target_label="openai",
        message="接口配置已保存",
        metadata={
            "provider": "openai",
            "api_key": "sk-test-secret",
            "nested": {
                "password": "p@ss",
                "enabled": True,
            },
        },
    )

    logs = audit_module.audit_service.list_logs(limit=5)
    assert len(logs) == 1
    assert logs[0]["metadata"]["provider"] == "openai"
    assert logs[0]["metadata"]["api_key"] == "***"
    assert logs[0]["metadata"]["nested"]["password"] == "***"
    assert logs[0]["metadata"]["nested"]["enabled"] is True
