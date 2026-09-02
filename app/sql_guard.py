from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class SqlSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedSql:
    sql: str
    sources: list[str]


FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
)

# SQL Server treats ROWCOUNT as a keyword even when it is used as a result
# column alias. Models commonly generate ``COUNT(*) AS RowCount``; quote that
# alias (and references to it, such as in ORDER BY) before execution.
TSQL_RESERVED_ALIASES = {"ROWCOUNT"}


def _quote_reserved_aliases(statement: exp.Expression) -> bool:
    aliases = {
        alias.alias.upper()
        for alias in statement.find_all(exp.Alias)
        if alias.alias and alias.alias.upper() in TSQL_RESERVED_ALIASES
    }
    if not aliases:
        return False

    for alias in statement.find_all(exp.Alias):
        identifier = alias.args.get("alias")
        if isinstance(identifier, exp.Identifier) and identifier.name.upper() in aliases:
            identifier.set("quoted", True)

    for column in statement.find_all(exp.Column):
        identifier = column.args.get("this")
        if isinstance(identifier, exp.Identifier) and identifier.name.upper() in aliases:
            identifier.set("quoted", True)
    return True


def validate_read_only_sql(sql: str) -> ValidatedSql:
    candidate = sql.strip()
    if not candidate:
        raise SqlSecurityError("SQL cannot be empty")

    try:
        statements = [item for item in parse(candidate, read="tsql") if item is not None]
    except ParseError as exc:
        raise SqlSecurityError("SQL is not valid T-SQL") from exc

    if len(statements) != 1:
        raise SqlSecurityError("Exactly one SQL statement is allowed")

    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise SqlSecurityError("Only SELECT or WITH ... SELECT is allowed")
    if any(statement.find(node_type) is not None for node_type in FORBIDDEN_NODES):
        raise SqlSecurityError("The SQL contains a forbidden operation")
    if statement.find(exp.Into) is not None:
        raise SqlSecurityError("SELECT INTO is not allowed")

    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE) if cte.alias_or_name}
    sources: set[str] = set()
    for table in statement.find_all(exp.Table):
        name = table.name
        if not name or (not table.db and name.lower() in cte_names):
            continue
        schema = table.db
        sources.add(f"{schema}.{name}" if schema else name)

    executable_sql = statement.sql(dialect="tsql") if _quote_reserved_aliases(statement) else candidate
    return ValidatedSql(sql=executable_sql, sources=sorted(sources, key=str.lower))
