"""The staged activation pin must match the current SQL module, not an old build."""
import hashlib
from pathlib import Path
import re


def test_activation_hash_matches_native_sql_module_normalization():
    installer=Path('scripts/sql/install_interwarehouse_credit_bridge.sql').read_text(encoding='utf-8')
    batch=next(b for b in re.split(r'^GO\s*$',installer,flags=re.M|re.I)
               if b.strip().startswith('CREATE OR ALTER PROCEDURE NeginAI.usp_CreateInterwarehouseCredit'))
    # Fresh clone OBJECT_DEFINITION shows SQL Server replaces "OR ALTER" with
    # two spaces: the resulting prefix is exactly "CREATE   PROCEDURE".
    stored=batch.replace('CREATE OR ALTER PROCEDURE','CREATE   PROCEDURE',1).replace('\r\n','\n').strip(' \t\r\n')
    digest=hashlib.sha256(stored.encode('utf-16le')).hexdigest().upper()
    activation=Path('scripts/sql/activate_interwarehouse_credit_access.sql').read_text(encoding='utf-8')
    assert f"<>'{digest}'" in activation
    assert "TRIM(NCHAR(9)+NCHAR(10)+NCHAR(13)+N' ' FROM" in activation
    assert 'NCHAR(13)+NCHAR(10),NCHAR(10)' in activation
