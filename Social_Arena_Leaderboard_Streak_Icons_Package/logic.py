from __future__ import annotations

"""
邏輯層（Logic Layer）
---------------------------------
這裡負責遊戲規則：
- 完成模組怎麼加分
- 100 分小考怎麼加 bonus
- Bio-Rhythm 怎麼加 bonus
- streak 怎麼累積
- shield 怎麼發、怎麼消耗
- 每週排行榜怎麼刷新

系統裁判 + 記分員
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from db import get_connection

MODULE_POINTS = 10
PERFECT_QUIZ_BONUS = 5
BIO_RHYTHM_BONUS = 2


@dataclass
class StudyResult:
    """前端表單送出一次學習後，要回傳給畫面的結果。"""

    session_id: int
    points_added: int
    streak_message: str


def today_local() -> date:
    return datetime.now().date()


def current_epoch_week(target_date: Optional[date] = None) -> str:
    """把今天轉成 2026-W15 這種週期字串。"""
    target_date = target_date or today_local()
    iso_year, iso_week, _ = target_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def week_bounds(target_date: Optional[date] = None) -> Tuple[datetime, datetime]:
    """回傳本週的起點與下週起點，用來計算 weekly leaderboard。"""
    target_date = target_date or today_local()
    monday = target_date - timedelta(days=target_date.weekday())
    next_monday = monday + timedelta(days=7)
    return (
        datetime.combine(monday, datetime.min.time()),
        datetime.combine(next_monday, datetime.min.time()),
    )


def _ensure_streak_row(cur, agent_id: int) -> None:
    """保證每個 agent 在 agent_streaks 都有一筆狀態資料。"""
    cur.execute(
        """
        INSERT OR IGNORE INTO agent_streaks (
            agent_id,
            current_streak_days,
            longest_historical_streak,
            active_shields_count,
            last_study_date
        ) VALUES (?, 0, 0, 0, NULL)
        """,
        (agent_id,),
    )


def _record_ledger_event(
    cur,
    agent_id: int,
    event_type: str,
    points_awarded: int,
    event_time: datetime,
    reference_id: Optional[int] = None,
) -> None:
    """把一筆點數事件寫進 immutable ledger。"""
    cur.execute(
        """
        INSERT INTO point_ledger (agent_id, event_type, points_awarded, reference_id, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (agent_id, event_type, points_awarded, reference_id, event_time.isoformat(timespec="seconds")),
    )


def create_study_session(
    agent_id: int,
    module_name: str,
    quiz_score: int,
    bio_rhythm_respected: bool,
    studied_at: Optional[datetime] = None,
) -> StudyResult:
    """
    一次完整學習事件的主流程：
    1. 寫入 study_sessions
    2. 根據規則寫入 point_ledger
    3. 更新 streak / shield
    4. 刷新 weekly standings
    """
    studied_at = studied_at or datetime.now()
    study_date = studied_at.date()

    conn = get_connection()
    cur = conn.cursor()

    _ensure_streak_row(cur, agent_id)

    cur.execute(
        """
        INSERT INTO study_sessions (agent_id, module_name, quiz_score, bio_rhythm_respected, studied_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (agent_id, module_name, quiz_score, int(bio_rhythm_respected), studied_at.isoformat(timespec="seconds")),
    )
    session_id = int(cur.lastrowid)

    total_points = 0

    # 1) 完成模組固定 +10
    _record_ledger_event(cur, agent_id, "module_completed", MODULE_POINTS, studied_at, session_id)
    total_points += MODULE_POINTS

    # 2) 小考 100 分再 +5
    if quiz_score == 100:
        _record_ledger_event(cur, agent_id, "quiz_perfect", PERFECT_QUIZ_BONUS, studied_at, session_id)
        total_points += PERFECT_QUIZ_BONUS

    # 3) 題目原文 +2 bonus multiplier；為表清楚，這裡寫為可稽核的 +2 bonus event
    if bio_rhythm_respected:
        _record_ledger_event(cur, agent_id, "bio_rhythm_bonus", BIO_RHYTHM_BONUS, studied_at, session_id)
        total_points += BIO_RHYTHM_BONUS

    streak_message = update_streak_state(cur, agent_id, study_date, studied_at)

    conn.commit()
    conn.close()

    refresh_weekly_standings(study_date)
    return StudyResult(session_id=session_id, points_added=total_points, streak_message=streak_message)


def update_streak_state(cur, agent_id: int, study_date: date, event_time: datetime) -> str:
    """
    streak 規則：
    - 同一天重複學習：streak 不重複加
    - 連續隔天有學：streak +1
    - 中斷一天：若有 shield，先消耗 shield；否則 streak 重設為 1（因為今天有學）
    - 每滿 3 天，送 1 個 shield
    """
    _ensure_streak_row(cur, agent_id)

    cur.execute(
        """
        SELECT current_streak_days, longest_historical_streak, active_shields_count, last_study_date
        FROM agent_streaks
        WHERE agent_id = ?
        """,
        (agent_id,),
    )
    row = cur.fetchone()

    current_streak = row["current_streak_days"]
    longest_streak = row["longest_historical_streak"]
    shields = row["active_shields_count"]
    last_study_date = row["last_study_date"]
    last_date = datetime.strptime(last_study_date, "%Y-%m-%d").date() if last_study_date else None

    if last_date is None:
        new_streak = 1
        message = "這是第一天學習，streak 從 1 開始。"
    elif last_date == study_date:
        new_streak = current_streak
        message = "同一天再次學習：分數照算，但 streak 不重複加。"
    elif last_date == study_date - timedelta(days=1):
        new_streak = current_streak + 1
        message = "今天有接續昨天，streak +1。"
    else:
        if shields > 0:
            shields -= 1
            new_streak = current_streak + 1
            _record_ledger_event(cur, agent_id, "shield_consumed", 0, event_time, None)
            message = "中間有漏一天，但系統先幫你消耗 1 個 Shield，所以 streak 保住了。"
        else:
            new_streak = 1
            message = "中間有漏一天且沒有 Shield，所以 streak 重新從 1 開始。"

    shield_earned = False
    if new_streak > 0 and new_streak % 3 == 0:
        shields += 1
        shield_earned = True
        _record_ledger_event(cur, agent_id, "shield_earned", 0, event_time, None)

    longest_streak = max(longest_streak, new_streak)

    cur.execute(
        """
        UPDATE agent_streaks
        SET current_streak_days = ?,
            longest_historical_streak = ?,
            active_shields_count = ?,
            last_study_date = ?
        WHERE agent_id = ?
        """,
        (new_streak, longest_streak, shields, study_date.isoformat(), agent_id),
    )

    if shield_earned:
        return message + " 連續 3 天達成，因此再獲得 1 個 Shield。"
    return message


def refresh_weekly_standings(target_date: Optional[date] = None) -> None:
    """從 ledger 重新計算本週所有人的 weekly points，寫入 standings 快取表。"""
    target_date = target_date or today_local()
    epoch = current_epoch_week(target_date)
    start_dt, end_dt = week_bounds(target_date)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT a.agent_id, a.branch_id, COALESCE(SUM(pl.points_awarded), 0) AS weekly_points
        FROM agents a
        LEFT JOIN point_ledger pl
            ON a.agent_id = pl.agent_id
            AND pl.timestamp >= ?
            AND pl.timestamp < ?
        GROUP BY a.agent_id, a.branch_id
        """,
        (start_dt.isoformat(timespec="seconds"), end_dt.isoformat(timespec="seconds")),
    )

    for row in cur.fetchall():
        cur.execute(
            """
            INSERT INTO leaderboard_standings (agent_id, branch_id, epoch_week_number, weekly_points_total, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, epoch_week_number)
            DO UPDATE SET weekly_points_total = excluded.weekly_points_total,
                          updated_at = excluded.updated_at,
                          branch_id = excluded.branch_id
            """,
            (
                row["agent_id"],
                row["branch_id"],
                epoch,
                row["weekly_points"],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    conn.commit()
    conn.close()


def get_agents() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.agent_id, a.agent_name, b.branch_name
        FROM agents a
        JOIN branches b ON a.branch_id = b.branch_id
        ORDER BY a.agent_name
        """
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_agent_snapshot(agent_id: int) -> Dict:
    refresh_weekly_standings()
    conn = get_connection()
    cur = conn.cursor()
    epoch = current_epoch_week()

    cur.execute(
        """
        SELECT a.agent_id,
               a.agent_name,
               b.branch_name,
               COALESCE(ls.weekly_points_total, 0) AS weekly_points,
               COALESCE(s.current_streak_days, 0) AS current_streak_days,
               COALESCE(s.longest_historical_streak, 0) AS longest_historical_streak,
               COALESCE(s.active_shields_count, 0) AS active_shields_count
        FROM agents a
        JOIN branches b ON a.branch_id = b.branch_id
        LEFT JOIN leaderboard_standings ls
            ON a.agent_id = ls.agent_id AND ls.epoch_week_number = ?
        LEFT JOIN agent_streaks s
            ON a.agent_id = s.agent_id
        WHERE a.agent_id = ?
        """,
        (epoch, agent_id),
    )
    agent = dict(cur.fetchone())

    cur.execute(
        "SELECT COALESCE(SUM(points_awarded), 0) AS lifetime_points FROM point_ledger WHERE agent_id = ?",
        (agent_id,),
    )
    agent["lifetime_points"] = cur.fetchone()["lifetime_points"]

    conn.close()
    return agent


def get_relative_leaderboard(agent_id: int, window: int = 2) -> List[Dict]:
    """回傳當前使用者前後各 2 名的相對排名，並附帶 streak 天數。"""
    refresh_weekly_standings()
    conn = get_connection()
    cur = conn.cursor()
    epoch = current_epoch_week()
    cur.execute(
        """
        SELECT ls.agent_id,
               a.agent_name,
               b.branch_name,
               ls.weekly_points_total,
               COALESCE(s.current_streak_days, 0) AS current_streak_days,
               COALESCE(lp.lifetime_points, 0) AS lifetime_points
        FROM leaderboard_standings ls
        JOIN agents a ON ls.agent_id = a.agent_id
        JOIN branches b ON ls.branch_id = b.branch_id
        LEFT JOIN agent_streaks s ON ls.agent_id = s.agent_id
        LEFT JOIN (
            SELECT agent_id, COALESCE(SUM(points_awarded), 0) AS lifetime_points
            FROM point_ledger
            GROUP BY agent_id
        ) lp ON ls.agent_id = lp.agent_id
        WHERE ls.epoch_week_number = ?
        ORDER BY ls.weekly_points_total DESC, a.agent_name ASC
        """,
        (epoch,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    position = next((i for i, row in enumerate(rows) if row["agent_id"] == agent_id), 0)
    start = max(0, position - window)
    end = min(len(rows), position + window + 1)
    sliced = rows[start:end]

    for idx, row in enumerate(sliced, start=start + 1):
        row["rank"] = idx
        row["is_current_user"] = row["agent_id"] == agent_id
    return sliced


def get_global_top_n(n: int = 10) -> List[Dict]:
    refresh_weekly_standings()
    conn = get_connection()
    cur = conn.cursor()
    epoch = current_epoch_week()
    cur.execute(
        """
        SELECT ls.agent_id,
               a.agent_name,
               b.branch_name,
               ls.weekly_points_total,
               COALESCE(s.current_streak_days, 0) AS current_streak_days,
               COALESCE(lp.lifetime_points, 0) AS lifetime_points
        FROM leaderboard_standings ls
        JOIN agents a ON ls.agent_id = a.agent_id
        JOIN branches b ON ls.branch_id = b.branch_id
        LEFT JOIN agent_streaks s ON ls.agent_id = s.agent_id
        LEFT JOIN (
            SELECT agent_id, COALESCE(SUM(points_awarded), 0) AS lifetime_points
            FROM point_ledger
            GROUP BY agent_id
        ) lp ON ls.agent_id = lp.agent_id
        WHERE ls.epoch_week_number = ?
        ORDER BY ls.weekly_points_total DESC, a.agent_name ASC
        LIMIT ?
        """,
        (epoch, n),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def get_branch_vs_branch() -> List[Dict]:
    refresh_weekly_standings()
    conn = get_connection()
    cur = conn.cursor()
    epoch = current_epoch_week()
    cur.execute(
        """
        SELECT b.branch_name,
               b.city,
               COALESCE(SUM(ls.weekly_points_total), 0) AS total_points,
               COUNT(a.agent_id) AS agent_count
        FROM branches b
        LEFT JOIN agents a ON b.branch_id = a.branch_id
        LEFT JOIN leaderboard_standings ls
            ON a.agent_id = ls.agent_id AND ls.epoch_week_number = ?
        GROUP BY b.branch_id, b.branch_name, b.city
        ORDER BY total_points DESC, b.branch_name ASC
        """,
        (epoch,),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def get_recent_ledger(agent_id: int, limit: int = 10) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT event_type, points_awarded, timestamp
        FROM point_ledger
        WHERE agent_id = ?
        ORDER BY timestamp DESC, transaction_id DESC
        LIMIT ?
        """,
        (agent_id, limit),
    )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
