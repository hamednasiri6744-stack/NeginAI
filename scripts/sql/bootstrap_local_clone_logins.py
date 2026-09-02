r"""Repair NeginAI SQL logins on the local Varanegar clone.

This helper is deliberately pinned to the local default SQL instance and the
NeginPakhsh_WebDev database.  It reads passwords from the repository .env,
never prints them, and refuses to run unless the Windows caller is sysadmin.

Run from a normal Windows session whose account can administer local SQL:

    .venv\Scripts\python.exe scripts\sql\bootstrap_local_clone_logins.py
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pyodbc
import pytds
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT_DIR / ".env"
SERVER = "localhost"
DATABASE = "NeginPakhsh_WebDev"
LIVE_SERVER = "192.168.1.171"
LIVE_DATABASE = "NeginPakhsh"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Required setting {name} is missing from {ENV_PATH}.")
    return value


def _odbc_driver() -> str:
    installed = set(pyodbc.drivers())
    for candidate in (
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
        "SQL Server Native Client 11.0",
    ):
        if candidate in installed:
            return candidate
    raise RuntimeError("No supported Microsoft SQL Server ODBC driver is installed.")


def _admin_connection() -> pyodbc.Connection:
    driver = _odbc_driver()
    connection_string = (
        f"DRIVER={{{driver}}};SERVER={SERVER};DATABASE=master;"
        "Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
        "Connection Timeout=8"
    )
    return pyodbc.connect(connection_string, autocommit=True)


def _verify_local_target(cursor: pyodbc.Cursor) -> None:
    cursor.execute(
        """
        SELECT
            CONVERT(nvarchar(128), SERVERPROPERTY('MachineName')),
            CONVERT(nvarchar(128), @@SERVERNAME),
            CONVERT(int, SERVERPROPERTY('IsIntegratedSecurityOnly')),
            IS_SRVROLEMEMBER(N'sysadmin'),
            DB_ID(?)
        """,
        DATABASE,
    )
    machine_name, server_name, windows_only, is_sysadmin, database_id = cursor.fetchone()
    local_names = {socket.gethostname().casefold(), os.environ.get("COMPUTERNAME", "").casefold()}
    if str(machine_name).casefold() not in local_names:
        raise RuntimeError(
            f"Safety stop: SQL target {server_name!r} is not this computer ({socket.gethostname()!r})."
        )
    if windows_only:
        raise RuntimeError("SQL Server Authentication is disabled on the local instance.")
    if is_sysadmin != 1:
        raise RuntimeError("The current Windows account is not sysadmin on the local SQL instance.")
    if database_id is None:
        raise RuntimeError(f"Local clone database {DATABASE!r} was not found.")


def _quote_name(value: str) -> str:
    return "[" + value.replace("]", "]]" ) + "]"


def _sql_literal(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'"


def _database_user_sid(cursor: pyodbc.Cursor, user_name: str) -> str | None:
    cursor.execute(f"USE [{DATABASE}]")
    cursor.execute(
        "SELECT CONVERT(varchar(170), sid, 1) FROM sys.database_principals WHERE name = ?",
        user_name,
    )
    row = cursor.fetchone()
    cursor.execute("USE [master]")
    return None if row is None else str(row[0])


def _live_login_sid(login_name: str, password: str) -> str:
    connection = pytds.connect(
        dsn=LIVE_SERVER,
        database=LIVE_DATABASE,
        user=login_name,
        password=password,
        login_timeout=6,
        timeout=12,
        readonly=True,
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT CONVERT(varchar(170), SUSER_SID(), 1)")
        return str(cursor.fetchone()[0])
    finally:
        connection.close()


def _recreate_login(
    cursor: pyodbc.Cursor,
    *,
    login_name: str,
    password: str,
    sid: str,
) -> None:
    quoted_login = _quote_name(login_name)
    cursor.execute("SELECT COUNT(*) FROM sys.server_principals WHERE name = ?", login_name)
    if cursor.fetchone()[0]:
        cursor.execute(f"DROP LOGIN {quoted_login}")
    cursor.execute(
        f"CREATE LOGIN {quoted_login} WITH "
        f"PASSWORD={_sql_literal(password)}, SID={sid}, CHECK_POLICY=ON, "
        f"DEFAULT_DATABASE=[{DATABASE}]"
    )
    cursor.execute(
        """
        SELECT CONVERT(varchar(170), sid, 1), is_disabled, default_database_name
        FROM sys.server_principals
        WHERE name = ?
        """,
        login_name,
    )
    result = cursor.fetchone()
    if (
        result is None
        or str(result[0]).casefold() != sid.casefold()
        or result[1] != 0
        or result[2] != DATABASE
    ):
        raise RuntimeError(f"Server login verification failed for {login_name!r}: {result!r}")


def _map_database_users(cursor: pyodbc.Cursor) -> None:
    cursor.execute(
        f"""
        USE [{DATABASE}];

        IF USER_ID(N'Negin_Report_ReadOnly') IS NULL
            CREATE USER [Negin_Report_ReadOnly] FOR LOGIN [Negin_Report_ReadOnly];
        ELSE
            ALTER USER [Negin_Report_ReadOnly] WITH LOGIN = [Negin_Report_ReadOnly];

        IF USER_ID(N'neginai') IS NULL
            CREATE USER [neginai] FOR LOGIN [neginai];
        ELSE
            ALTER USER [neginai] WITH LOGIN = [neginai];

        IF IS_ROLEMEMBER(N'db_datareader', N'Negin_Report_ReadOnly') <> 1
            ALTER ROLE [db_datareader] ADD MEMBER [Negin_Report_ReadOnly];
        IF IS_ROLEMEMBER(N'db_datawriter', N'Negin_Report_ReadOnly') = 1
            ALTER ROLE [db_datawriter] DROP MEMBER [Negin_Report_ReadOnly];
        IF IS_ROLEMEMBER(N'db_denydatawriter', N'Negin_Report_ReadOnly') <> 1
            ALTER ROLE [db_denydatawriter] ADD MEMBER [Negin_Report_ReadOnly];
        GRANT CONNECT TO [Negin_Report_ReadOnly];
        GRANT VIEW DEFINITION TO [Negin_Report_ReadOnly];
        GRANT VIEW DATABASE STATE TO [Negin_Report_ReadOnly];
        GRANT SHOWPLAN TO [Negin_Report_ReadOnly];

        -- db_datareader covers tables and views but does not make scalar UDFs
        -- callable.  Grant only the encrypted functions needed for behavioral
        -- contract probes; deliberately do not grant EXECUTE on the mutating
        -- dbo.ChangeDatabaseToDBOne procedure.
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[dbo].[ufn_GetInvoiceGLId]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[DateTimeToSolarX]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[GetNumberStr]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDateADD]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDateAddX]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDateDiffX]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDateFormatIsValidX]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDateIsValidX]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarDatePart]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarToDateTime]
            TO [Negin_Report_ReadOnly];
        GRANT SELECT, REFERENCES, EXECUTE ON OBJECT::[GNR].[SolarToDateTimeX]
            TO [Negin_Report_ReadOnly];

        IF IS_ROLEMEMBER(N'db_datareader', N'neginai') = 1
            ALTER ROLE [db_datareader] DROP MEMBER [neginai];
        IF IS_ROLEMEMBER(N'db_datawriter', N'neginai') = 1
            ALTER ROLE [db_datawriter] DROP MEMBER [neginai];
        IF IS_ROLEMEMBER(N'db_denydatawriter', N'neginai') <> 1
            ALTER ROLE [db_denydatawriter] ADD MEMBER [neginai];
        GRANT CONNECT TO [neginai];
        """
    )


def _verify_sql_login(login_name: str, password: str, *, expect_select: bool) -> tuple:
    connection = pytds.connect(
        dsn="127.0.0.1",
        database=DATABASE,
        user=login_name,
        password=password,
        login_timeout=6,
        timeout=12,
        readonly=True,
        autocommit=True,
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                @@SERVERNAME,
                DB_NAME(),
                SUSER_SNAME(),
                USER_NAME(),
                IS_MEMBER(N'db_datareader'),
                IS_MEMBER(N'db_datawriter'),
                IS_MEMBER(N'db_denydatawriter'),
                HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'SELECT'),
                HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'VIEW DEFINITION'),
                DATABASEPROPERTYEX(DB_NAME(), N'Updateability')
            """
        )
        result = tuple(cursor.fetchone())
    finally:
        connection.close()

    can_select = result[7] == 1
    is_writer = result[5] == 1
    is_deny_writer = result[6] == 1
    is_read_only = result[9] == "READ_ONLY"
    if can_select is not expect_select or is_writer or not is_deny_writer or not is_read_only:
        raise RuntimeError(f"Permission verification failed for {login_name!r}: {result!r}")
    return result


def main() -> int:
    load_dotenv(ENV_PATH, override=True)
    accounts = (
        ("Negin_Report_ReadOnly", _required_env("SQL_PASSWORD")),
        ("neginai", _required_env("VARANEGAR_ORDER_SQL_PASSWORD")),
    )
    if _required_env("SQL_USERNAME") != accounts[0][0]:
        raise RuntimeError("SQL_USERNAME no longer matches the expected analysis login.")
    if _required_env("VARANEGAR_ORDER_SQL_USERNAME") != accounts[1][0]:
        raise RuntimeError("VARANEGAR_ORDER_SQL_USERNAME no longer matches the expected bridge login.")

    connection = _admin_connection()
    try:
        cursor = connection.cursor()
        _verify_local_target(cursor)

        # A restored read-only database keeps database users but not the
        # instance-level SQL logins.  Recreate each login with the existing
        # database-user SID when available; otherwise use the live login SID.
        sids: dict[str, str] = {}
        for login_name, password in accounts:
            sids[login_name] = _database_user_sid(cursor, login_name) or _live_login_sid(
                login_name, password
            )
            _recreate_login(
                cursor,
                login_name=login_name,
                password=password,
                sid=sids[login_name],
            )

        made_read_write = False
        try:
            cursor.execute(f"ALTER DATABASE [{DATABASE}] SET READ_WRITE")
            made_read_write = True
            _map_database_users(cursor)
        finally:
            if made_read_write:
                cursor.execute("USE [master]")
                cursor.execute(f"ALTER DATABASE [{DATABASE}] SET READ_ONLY")

        cursor.execute("SELECT is_read_only FROM sys.databases WHERE name = ?", DATABASE)
        if cursor.fetchone()[0] != 1:
            raise RuntimeError(f"Local clone database {DATABASE!r} was not restored to READ_ONLY.")
    finally:
        connection.close()

    analysis = _verify_sql_login(accounts[0][0], accounts[0][1], expect_select=True)
    bridge = _verify_sql_login(accounts[1][0], accounts[1][1], expect_select=False)
    print("Local clone SQL login repair completed.")
    print("analysis:", analysis)
    print("bridge:", bridge)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
