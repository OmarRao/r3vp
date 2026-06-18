"""Hash-chained audit log for tamper-evident test run evidence."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path


CHAIN_DB = Path("/data/audit_chain.db")


@dataclass
class ChainEntry:
    seq: int
    timestamp: float
    event_type: str
    payload: dict
    prev_hash: str
    entry_hash: str


def _init_db(path: Path = CHAIN_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chain (
            seq        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  REAL    NOT NULL,
            event_type TEXT    NOT NULL,
            payload    TEXT    NOT NULL,
            prev_hash  TEXT    NOT NULL,
            entry_hash TEXT    NOT NULL UNIQUE
        )
    """)
    conn.commit()
    return conn


def _last_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT entry_hash FROM chain ORDER BY seq DESC LIMIT 1").fetchone()
    return row[0] if row else "0" * 64


def append(event_type: str, payload: dict, db_path: Path = CHAIN_DB) -> ChainEntry:
    """Append a hash-chained entry. Returns the new ChainEntry."""
    conn = _init_db(db_path)
    ts = time.time()
    prev = _last_hash(conn)
    raw = prev + str(ts) + event_type + json.dumps(payload, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    conn.execute(
        "INSERT INTO chain (timestamp, event_type, payload, prev_hash, entry_hash) VALUES (?,?,?,?,?)",
        (ts, event_type, json.dumps(payload), prev, digest),
    )
    conn.commit()
    row = conn.execute("SELECT seq FROM chain WHERE entry_hash=?", (digest,)).fetchone()
    conn.close()
    return ChainEntry(seq=row[0], timestamp=ts, event_type=event_type, payload=payload, prev_hash=prev, entry_hash=digest)


def verify_chain(db_path: Path = CHAIN_DB) -> tuple[bool, int]:
    """Verify integrity of the entire chain. Returns (ok, first_broken_seq or -1)."""
    conn = _init_db(db_path)
    rows = conn.execute("SELECT seq, timestamp, event_type, payload, prev_hash, entry_hash FROM chain ORDER BY seq").fetchall()
    conn.close()
    prev = "0" * 64
    for seq, ts, et, payload, stored_prev, stored_hash in rows:
        if stored_prev != prev:
            return False, seq
        raw = prev + str(ts) + et + payload
        expected = hashlib.sha256(raw.encode()).hexdigest()
        if expected != stored_hash:
            return False, seq
        prev = stored_hash
    return True, -1


def export_entries(db_path: Path = CHAIN_DB) -> list[dict]:
    conn = _init_db(db_path)
    rows = conn.execute("SELECT seq, timestamp, event_type, payload, prev_hash, entry_hash FROM chain ORDER BY seq").fetchall()
    conn.close()
    return [
        {"seq": r[0], "timestamp": r[1], "event_type": r[2], "payload": json.loads(r[3]), "prev_hash": r[4], "entry_hash": r[5]}
        for r in rows
    ]
