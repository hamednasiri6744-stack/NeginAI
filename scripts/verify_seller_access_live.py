from __future__ import annotations

import json
from urllib.request import Request, urlopen

from app.access_control import (
    _object_metadata,
    enforce_sql_access,
    policy_for_user,
    schema_item_allowed,
)
from app.config import get_settings
from app.sql_guard import validate_read_only_sql


def main() -> None:
    settings = get_settings()
    policy = policy_for_user(settings, "A.kamran")
    queries = {
        "sales": "SELECT TOP (1) CustomerId FROM dbo.SalesReviewFast",
        "cardex": "SELECT TOP (1) CustID FROM dbo.CustomerCardex_Info",
        "receipts": "SELECT TOP (1) CustId FROM Acc.vwRcvPaymentsReview",
        "ngt": "SELECT TOP (1) BackOfficeId FROM FRU.NGT_TourCustomerModel",
    }
    for name, sql in queries.items():
        validated = validate_read_only_sql(sql)
        source = validated.sources[0]
        schema, object_name = source.split(".", 1)
        metadata = _object_metadata(settings, schema, object_name)
        if metadata is None:
            raise RuntimeError(f"Missing schema metadata for {source}")
        actual_schema, actual_name, columns = metadata
        visible = schema_item_allowed(
            policy,
            {"schema": actual_schema, "name": actual_name, "columns": columns},
        )
        secured = enforce_sql_access(settings, policy, validate_read_only_sql(sql))
        request = Request(
            "http://127.0.0.1:8000/sql/query",
            data=json.dumps({"sql": secured.sql}).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": settings.action_api_key,
            },
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
        print(
            name,
            response.status,
            payload["row_count"],
            payload["execution_time"],
            "schema-visible" if visible else "schema-hidden",
        )


if __name__ == "__main__":
    main()
