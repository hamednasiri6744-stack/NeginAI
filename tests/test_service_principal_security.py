from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.access_control import policy_for_user
from app.organization_structure_service import require_admin
from app.routes.dependencies import require_user_or_local


def _remote_request(settings, path: str):
    request = Mock()
    request.app.state.settings = settings
    request.client.host = "10.10.10.10"
    request.cookies = {}
    request.url.path = path
    request.state = SimpleNamespace()
    return request


@pytest.mark.parametrize(
    "path",
    ["/planning", "/automations", "/organization-structure", "/seller-workspace"],
)
def test_action_api_key_cannot_own_user_scoped_resources(settings, path):
    request = _remote_request(settings, path)

    with pytest.raises(HTTPException) as exc:
        require_user_or_local(request, settings.action_api_key, None)

    assert exc.value.status_code == 403


def test_action_api_key_keeps_internal_reporting_identity(settings):
    request = _remote_request(settings, "/chat")

    require_user_or_local(request, settings.action_api_key, None)

    assert request.state.username == "action-api-key"
    policy = policy_for_user(settings, request.state.username)
    assert policy.is_service_principal is True
    assert policy.is_admin is False
    assert policy.trusted_context()["write_access"] is False
    assert policy.trusted_context()["user_owned_resource_access"] is False


def test_action_api_key_is_not_organization_admin(settings):
    with pytest.raises(PermissionError):
        require_admin(settings, "action-api-key")


def test_reporting_odbc_requires_encryption(settings):
    from app.database import _connection_string

    configured = replace(
        settings,
        sql_server="sql.internal.example",
        sql_username="reader",
        sql_password="secret",
        sql_trust_certificate=False,
    )
    value = _connection_string(configured)

    assert "Encrypt=yes;" in value
    assert "TrustServerCertificate=no;" in value
    assert "ApplicationIntent=ReadOnly;" in value
