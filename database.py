# ============================================================
# DATABASE / DUPLICATE PROTECTION
# ============================================================

import sqlite3
import threading
from datetime import datetime

from config import DATABASE_FILE, MAX_SIGNAL_HISTORY


class SignalDatabase:

    def __init__(self):
        self.db_file = DATABASE_FILE
        self.lock = threading.Lock()
        self._create_database()

    def _connect(self):
        return sqlite3.connect(
            self.db_file,
            timeout=30,
            check_same_thread=False
        )

    def _create_database(self):

        with self._connect() as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signature TEXT UNIQUE,
                    direction TEXT,
                    entry REAL,
                    stop_loss REAL,
                    tp1 REAL,
                    tp2 REAL,
                    tp3 REAL,
                    video_id TEXT,
                    detected_at TEXT,
                    sent INTEGER DEFAULT 0
                )
            """)

            conn.commit()

    def exists(self, signature):

        with self.lock:

            with self._connect() as conn:

                row = conn.execute(
                    """
                    SELECT id
                    FROM signals
                    WHERE signature = ?
                    """,
                    (signature,)
                ).fetchone()

                return row is not None

    def save_signal(
        self,
        signature,
        direction,
        entry,
        stop_loss,
        tp1,
        tp2,
        tp3,
        video_id,
        sent
    ):

        with self.lock:

            with self._connect() as conn:

                conn.execute(
                    """
                    INSERT OR IGNORE INTO signals
                    (
                        signature,
                        direction,
                        entry,
                        stop_loss,
                        tp1,
                        tp2,
                        tp3,
                        video_id,
                        detected_at,
                        sent
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        signature,
                        direction,
                        entry,
                        stop_loss,
                        tp1,
                        tp2,
                        tp3,
                        video_id,
                        datetime.now().isoformat(),
                        int(sent)
                    )
                )

                conn.commit()

                self._cleanup(conn)

    def _cleanup(self, conn):

        conn.execute(
            """
            DELETE FROM signals
            WHERE id NOT IN
            (
                SELECT id
                FROM signals
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (MAX_SIGNAL_HISTORY,)
        )

        conn.commit()