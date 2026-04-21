from __future__ import annotations

"""
示範資料腳本
-------------
這個檔案的目的不是做真實上線資料，而是快速建立一組「能展示」的情境：
- 有幾個不同分行
- 有幾位分數高低不同的業務員
- 有人 streak 很長
- 有人剛好拿到 shield
- 有人會落在相對排行榜中間
"""

from datetime import datetime, timedelta

from db import get_connection, initialize_database
from logic import create_study_session, refresh_weekly_standings

BRANCHES = [
    ("Nangang District Branch", "Taipei"),
    ("Xinyi District Branch", "Taipei"),
    ("Banqiao Branch", "New Taipei"),
    ("Taoyuan Branch", "Taoyuan"),
]

AGENTS = [
    ("Alicia", "Nangang District Branch"),
    ("Ben", "Nangang District Branch"),
    ("Cindy", "Xinyi District Branch"),
    ("David", "Xinyi District Branch"),
    ("Ethan", "Banqiao Branch"),
    ("Fiona", "Banqiao Branch"),
    ("Grace", "Taoyuan Branch"),
    ("Henry", "Taoyuan Branch"),
]

# agent_name, days_ago, quiz_score, bio_rhythm, module_name
SESSIONS = [
    ("Alicia", 4, 100, True, "Investment-Linked Product Basics"),
    ("Alicia", 3, 90, True, "Term Life Policy Refresher"),
    ("Alicia", 2, 100, False, "FSC Compliance Sprint"),
    ("Alicia", 0, 100, True, "Cross-Selling Framework Sprint"),

    ("Ben", 2, 80, False, "Term Life Policy Refresher"),
    ("Ben", 1, 100, False, "FSC Compliance Sprint"),
    ("Ben", 0, 100, True, "Cross-Selling Framework Sprint"),

    ("Cindy", 4, 100, True, "FSC Compliance Sprint"),
    ("Cindy", 3, 100, True, "FSC Compliance Sprint"),
    ("Cindy", 2, 100, True, "Cross-Selling Framework Sprint"),
    ("Cindy", 1, 90, False, "Objection Handling"),
    ("Cindy", 0, 100, True, "Investment-Linked Product Basics"),

    ("David", 0, 100, False, "Objection Handling"),

    ("Ethan", 3, 90, False, "Term Life Policy Refresher"),
    ("Ethan", 1, 100, True, "FSC Compliance Sprint"),

    ("Fiona", 2, 100, True, "Cross-Selling Framework Sprint"),
    ("Fiona", 0, 100, True, "Cross-Selling Framework Sprint"),

    ("Grace", 6, 100, True, "Investment-Linked Product Basics"),
    ("Grace", 5, 100, True, "Investment-Linked Product Basics"),
    ("Grace", 4, 100, True, "Investment-Linked Product Basics"),
    ("Grace", 3, 100, True, "FSC Compliance Sprint"),
    ("Grace", 2, 100, False, "FSC Compliance Sprint"),
    ("Grace", 1, 100, True, "Cross-Selling Framework Sprint"),
    ("Grace", 0, 100, True, "Cross-Selling Framework Sprint"),

    ("Henry", 1, 70, False, "Objection Handling"),
]


def reset_database() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(
        """
        DELETE FROM leaderboard_standings;
        DELETE FROM point_ledger;
        DELETE FROM study_sessions;
        DELETE FROM agent_streaks;
        DELETE FROM agents;
        DELETE FROM branches;
        DELETE FROM sqlite_sequence;
        """
    )
    conn.commit()
    conn.close()


def seed() -> None:
    initialize_database()
    reset_database()

    conn = get_connection()
    cur = conn.cursor()

    for branch_name, city in BRANCHES:
        cur.execute("INSERT INTO branches (branch_name, city) VALUES (?, ?)", (branch_name, city))

    cur.execute("SELECT branch_id, branch_name FROM branches")
    branch_map = {row["branch_name"]: row["branch_id"] for row in cur.fetchall()}

    for agent_name, branch_name in AGENTS:
        cur.execute("INSERT INTO agents (agent_name, branch_id) VALUES (?, ?)", (agent_name, branch_map[branch_name]))

    cur.execute("SELECT agent_id, agent_name FROM agents")
    agent_map = {row["agent_name"]: row["agent_id"] for row in cur.fetchall()}
    conn.commit()
    conn.close()

    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for agent_name, days_ago, quiz_score, bio_rhythm, module_name in sorted(SESSIONS, key=lambda x: x[1], reverse=True):
        create_study_session(
            agent_id=agent_map[agent_name],
            module_name=module_name,
            quiz_score=quiz_score,
            bio_rhythm_respected=bio_rhythm,
            studied_at=base_time - timedelta(days=days_ago),
        )

    refresh_weekly_standings()
    print("Demo database seeded successfully.")
    print("Next step: python app.py")


if __name__ == "__main__":
    seed()
