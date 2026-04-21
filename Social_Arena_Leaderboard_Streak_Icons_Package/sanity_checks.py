from __future__ import annotations

"""簡單健康檢查：確認 demo 專案能順利初始化並讀到主要資料。"""

from db import initialize_database
from logic import get_agents, get_agent_snapshot, get_branch_vs_branch, get_global_top_n


def run_checks() -> None:
    initialize_database()
    agents = get_agents()
    assert agents, "沒有 agents，請先執行 python seed_demo.py"

    sample_agent_id = agents[0]["agent_id"]
    snapshot = get_agent_snapshot(sample_agent_id)
    global_top = get_global_top_n()
    branches = get_branch_vs_branch()

    assert "weekly_points" in snapshot
    assert global_top, "排行榜應該要有資料"
    assert branches, "Branch vs Branch 應該要有資料"

    print("Sanity checks passed.")
    print(f"Sample agent: {snapshot['agent_name']}")
    print(f"Weekly points: {snapshot['weekly_points']}")
    print(f"Current streak: {snapshot['current_streak_days']}")


if __name__ == "__main__":
    run_checks()
