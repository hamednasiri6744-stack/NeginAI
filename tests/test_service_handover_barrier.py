import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def make_db(tmp_path, busy=False):
    db = tmp_path / 'warehouse-assistant.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE warehouse_automatic_refresh_state (id INTEGER, lock_token TEXT, lock_expires_at TEXT)')
        conn.execute('CREATE TABLE warehouse_email_attempts (status TEXT)')
        if busy:
            conn.execute("INSERT INTO warehouse_email_attempts VALUES ('sending')")
    return db


def start_barrier(tmp_path):
    env = dict(os.environ, NEGINAI_SQLITE_PATH=str(tmp_path / 'main.db'))
    return subprocess.Popen(
        [sys.executable, str(ROOT / 'scripts/service_handover_barrier.py'), str(tmp_path / 'ready.json'), str(tmp_path / 'release')],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def test_active_email_prevents_handover(tmp_path):
    make_db(tmp_path, busy=True)
    worker = start_barrier(tmp_path)
    assert worker.wait(timeout=10) != 0
    assert not (tmp_path / 'ready.json').exists()


def test_active_refresh_prevents_handover(tmp_path):
    db = make_db(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO warehouse_automatic_refresh_state VALUES (1, 'busy', '2999-01-01T00:00:00+00:00')")
    worker = start_barrier(tmp_path)
    assert worker.wait(timeout=10) != 0
    assert not (tmp_path / 'ready.json').exists()


def test_idle_barrier_blocks_writes_until_release(tmp_path):
    db = make_db(tmp_path)
    worker = start_barrier(tmp_path)
    try:
        deadline = time.monotonic() + 10
        while not (tmp_path / 'ready.json').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        assert json.loads((tmp_path / 'ready.json').read_text())['ready']
        with sqlite3.connect(db, timeout=.1) as conn:
            try:
                conn.execute('BEGIN IMMEDIATE')
                raise AssertionError('Write boundary was not held')
            except sqlite3.OperationalError as exc:
                assert 'locked' in str(exc)
        (tmp_path / 'release').touch()
        assert worker.wait(timeout=5) == 0
        with sqlite3.connect(db, timeout=.1) as conn:
            conn.execute('BEGIN IMMEDIATE')
    finally:
        if worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=5)
