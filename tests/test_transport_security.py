from dataclasses import replace

import pytest

from app.config import validate_transport_security


def test_production_rejects_reporting_certificate_bypass(settings):
    production = replace(
        settings,
        deployment_environment="production",
        sql_server="sql.internal.example",
        sql_username="reporting",
        sql_password="configured-for-test",
        sql_trust_certificate=True,
        redis_url="redis://localhost:6379/0",
    )

    with pytest.raises(RuntimeError, match="reporting SQL Server"):
        validate_transport_security(production)


def test_production_rejects_varanegar_write_certificate_bypass(settings):
    production = replace(
        settings,
        deployment_environment="production",
        sql_trust_certificate=False,
        varanegar_order_sql_server="sql.internal.example",
        varanegar_order_sql_username="writer",
        varanegar_order_sql_password="configured-for-test",
        varanegar_order_sql_trust_certificate=True,
        redis_url="redis://localhost:6379/0",
    )

    with pytest.raises(RuntimeError, match="Varanegar order SQL Server"):
        validate_transport_security(production)


def test_production_accepts_validated_sql_connections(settings):
    production = replace(
        settings,
        deployment_environment="production",
        sql_server="sql.internal.example",
        sql_username="reporting",
        sql_password="configured-for-test",
        sql_trust_certificate=False,
        varanegar_order_sql_server="sql.internal.example",
        varanegar_order_sql_username="writer",
        varanegar_order_sql_password="configured-for-test",
        varanegar_order_sql_trust_certificate=False,
        redis_url="redis://localhost:6379/0",
    )

    validate_transport_security(production)


def test_production_requires_redis_for_authentication_rate_limiting(settings):
    production = replace(settings, deployment_environment="production", redis_url="")

    with pytest.raises(RuntimeError, match="authentication rate limiting"):
        validate_transport_security(production)


def test_staging_cannot_use_process_local_authentication_limiter(settings):
    staging = replace(settings, deployment_environment="staging", redis_url="")

    with pytest.raises(RuntimeError, match="authentication rate limiting"):
        validate_transport_security(staging)
