/*
  NeginAI read-only analysis access for the live Varanegar database.

  Run in SSMS while connected to SERVERNEW with a DBA/sysadmin account.
  This script is intentionally limited to NeginPakhsh and grants no write,
  ALTER, CONTROL, db_owner, db_datawriter, or sysadmin permission.

  Accounts:
    - Negin_Report_ReadOnly: broad read-only schema/data analysis identity.
    - neginai: isolated operational bridge identity; direct DML remains denied.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

IF DB_NAME() <> N'NeginPakhsh'
    THROW 51000, N'Run this script only in the NeginPakhsh database.', 1;

IF USER_ID(N'Negin_Report_ReadOnly') IS NULL
    THROW 51001, N'Database user Negin_Report_ReadOnly was not found.', 1;

IF USER_ID(N'neginai') IS NULL
    THROW 51002, N'Database user neginai was not found.', 1;

/* Full read-only data and metadata access for analysis/reporting. */
IF IS_ROLEMEMBER(N'db_datareader', N'Negin_Report_ReadOnly') <> 1
    ALTER ROLE [db_datareader] ADD MEMBER [Negin_Report_ReadOnly];

IF IS_ROLEMEMBER(N'db_denydatawriter', N'Negin_Report_ReadOnly') <> 1
    ALTER ROLE [db_denydatawriter] ADD MEMBER [Negin_Report_ReadOnly];

GRANT CONNECT TO [Negin_Report_ReadOnly];
GRANT VIEW DEFINITION TO [Negin_Report_ReadOnly];
GRANT VIEW DATABASE STATE TO [Negin_Report_ReadOnly];
GRANT SHOWPLAN TO [Negin_Report_ReadOnly];

/* Keep the future order bridge unable to write directly to tables. */
IF IS_ROLEMEMBER(N'db_denydatawriter', N'neginai') <> 1
    ALTER ROLE [db_denydatawriter] ADD MEMBER [neginai];

GRANT CONNECT TO [neginai];

/* Verification output: every analysis value should be 1; writer values 0. */
EXECUTE AS USER = N'Negin_Report_ReadOnly';
SELECT
    USER_NAME() AS DatabaseUser,
    IS_MEMBER(N'db_datareader') AS IsDataReader,
    IS_MEMBER(N'db_datawriter') AS IsDataWriter,
    IS_MEMBER(N'db_denydatawriter') AS IsDenyDataWriter,
    HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'SELECT') AS CanSelectDatabase,
    HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'VIEW DEFINITION') AS CanViewDefinition,
    HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'VIEW DATABASE STATE') AS CanViewDatabaseState,
    HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'SHOWPLAN') AS CanShowplan;
REVERT;

EXECUTE AS USER = N'neginai';
SELECT
    USER_NAME() AS DatabaseUser,
    IS_MEMBER(N'db_datareader') AS IsDataReader,
    IS_MEMBER(N'db_datawriter') AS IsDataWriter,
    IS_MEMBER(N'db_denydatawriter') AS IsDenyDataWriter,
    HAS_PERMS_BY_NAME(DB_NAME(), N'DATABASE', N'SELECT') AS CanSelectDatabase;
REVERT;
