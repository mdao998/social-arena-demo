from __future__ import annotations

"""
資料庫層（Database Layer）
-------------------------
這個檔案只做一件事：
把專案需要的資料表準備好，並提供一個穩定的 SQLite 連線。

你可以把它想成：
- get_connection() = 打開保險箱
- initialize_database() = 先把所有帳本和名冊建好
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "social_arena.db"


def get_connection() -> sqlite3.Connection:
    """回傳一個可直接使用的 SQLite 連線。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 讓查詢結果可用 row['欄位名'] 讀取
    conn.execute("PRAGMA foreign_keys = ON;")  # 開啟外鍵檢查，避免資料對不上
    return conn


def initialize_database() -> None:
    """
    第一次執行專案時，建立所有核心資料表。

    表的角色：
    1. branches               -> 分行名單
    2. agents                 -> 業務員名單
    3. study_sessions         -> 每一次 7 分鐘學習紀錄
    4. point_ledger           -> 不可變點數帳本（每一筆加分都留痕）
    5. leaderboard_standings  -> 每週排行榜快取表
    6. agent_streaks          -> streak / shield 狀態機
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS branches (
            branch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT NOT NULL UNIQUE,
            city TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agents (
            agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            branch_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        );

        CREATE TABLE IF NOT EXISTS study_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            module_name TEXT NOT NULL,
            quiz_score INTEGER NOT NULL,
            bio_rhythm_respected INTEGER NOT NULL DEFAULT 0,
            sprint_minutes INTEGER NOT NULL DEFAULT 7,
            studied_at TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );

        CREATE TABLE IF NOT EXISTS point_ledger (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            points_awarded INTEGER NOT NULL,
            reference_id INTEGER,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
            FOREIGN KEY (reference_id) REFERENCES study_sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS leaderboard_standings (
            standing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            epoch_week_number TEXT NOT NULL,
            weekly_points_total INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(agent_id, epoch_week_number),
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id),
            FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
        );

        CREATE TABLE IF NOT EXISTS agent_streaks (
            streak_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL UNIQUE,
            current_streak_days INTEGER NOT NULL DEFAULT 0,
            longest_historical_streak INTEGER NOT NULL DEFAULT 0,
            active_shields_count INTEGER NOT NULL DEFAULT 0,
            last_study_date TEXT,
            FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
        );
        """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database ready: {DB_PATH}")
