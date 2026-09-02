import pytest

from app.sql_guard import SqlSecurityError, validate_read_only_sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO dbo.Users(name) VALUES ('x')",
        "UPDATE dbo.Users SET name='x'",
        "DELETE FROM dbo.Users",
        "MERGE dbo.Target AS t USING dbo.Source AS s ON t.id=s.id WHEN MATCHED THEN UPDATE SET t.x=s.x;",
        "DROP TABLE dbo.Users",
        "ALTER TABLE dbo.Users ADD x int",
        "CREATE TABLE dbo.Bad(id int)",
        "TRUNCATE TABLE dbo.Users",
        "EXEC dbo.DoThing",
        "EXECUTE dbo.DoThing",
        "SELECT * INTO dbo.Copy FROM dbo.Users",
        "SELECT 1; SELECT 2",
    ],
)
def test_forbidden_sql_is_rejected(sql):
    with pytest.raises(SqlSecurityError):
        validate_read_only_sql(sql)


def test_select_is_allowed_and_sources_are_returned():
    result = validate_read_only_sql("SELECT u.Id FROM dbo.Users AS u")
    assert result.sources == ["dbo.Users"]


def test_cte_select_is_allowed():
    result = validate_read_only_sql("WITH recent AS (SELECT Id FROM sales.Orders) SELECT Id FROM recent")
    assert result.sources == ["sales.Orders"]


def test_sql_server_rowcount_alias_is_safely_quoted():
    result = validate_read_only_sql(
        "SELECT COUNT(*) AS RowCount FROM dbo.Sales ORDER BY RowCount DESC"
    )

    assert "AS [RowCount]" in result.sql
    assert "ORDER BY [RowCount] DESC" in result.sql
    assert result.sources == ["dbo.Sales"]


def test_empty_and_invalid_sql_are_rejected():
    for sql in ("", "this is not sql ???"):
        with pytest.raises(SqlSecurityError):
            validate_read_only_sql(sql)
