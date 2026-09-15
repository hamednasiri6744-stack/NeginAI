"""A TDS transaction must begin in snapshot isolation, not switch after BEGIN."""
import pytest

from app import warehouse_receipt_reflection as reflection


class TdsConnection:
    def __init__(self):
        self._isolation = 0
        self.events = []

    @property
    def isolation_level(self):
        return self._isolation

    @isolation_level.setter
    def isolation_level(self, value):
        self.events.append(('isolation', value))
        self._isolation = value

    def cursor(self):
        self.events.append(('cursor', self._isolation))
        return self

    def execute(self, sql):
        if sql.startswith('SET TRANSACTION'):
            raise RuntimeError('snapshot cannot be set after TDS BEGIN')
        assert self._isolation == 5
        self.events.append(('select', sql))


def test_tds_selects_share_snapshot_selected_before_cursor():
    conn = TdsConnection()
    cursor = reflection.snapshot_cursor(conn)
    cursor.execute('SELECT inventory')
    cursor.execute('SELECT receipt')
    assert conn.events == [('isolation', 5), ('cursor', 5),
                           ('select', 'SELECT inventory'), ('select', 'SELECT receipt')]


def test_odbc_configures_same_cursor_before_first_select():
    class OdbcConnection:
        def __init__(self): self.events = []
        def cursor(self): return self
        def execute(self, sql): self.events.append(sql)
    conn = OdbcConnection()
    cursor = reflection.snapshot_cursor(conn)
    cursor.execute('SELECT inventory')
    assert conn.events == ['SET TRANSACTION ISOLATION LEVEL SNAPSHOT', 'SELECT inventory']


def test_isolation_failure_never_falls_back_to_inconsistent_reads():
    class Denied(TdsConnection):
        @TdsConnection.isolation_level.setter
        def isolation_level(self, value): raise RuntimeError('snapshot unavailable')
    conn = Denied()
    with pytest.raises(RuntimeError, match='snapshot unavailable'):
        reflection.snapshot_cursor(conn)
    assert conn.events == []
