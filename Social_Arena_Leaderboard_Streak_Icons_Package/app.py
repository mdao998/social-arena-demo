
from __future__ import annotations

"""
展示版 Demo  v2
----------------------
本版調整：
1. 將 Step 區塊整合成最上方的橫式展示列
2. 將 Relative Leaderboard / Global Top 10 合併成同一卡片，用按鈕切換
3. 保留 agent 切換後整頁 snapshot 同步更新
"""

from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from pathlib import Path
import base64

from db import initialize_database
from logic import (
    create_study_session,
    current_epoch_week,
    get_agent_snapshot,
    get_agents,
    get_branch_vs_branch,
    get_global_top_n,
    get_recent_ledger,
    get_relative_leaderboard,
)

HOST = "127.0.0.1"
PORT = 8888

BASE_DIR = Path(__file__).resolve().parent
LOGO_DATA_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAAZdEVYdFNvZnR3YXJlAEFkb2JlIEltYWdlUmVhZHlxyWU8AAADdmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNy4xLWMwMDAgNzkuOWNjYzRkZTkzLCAyMDIyLzAzLzE0LTE0OjA3OjIyICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyIgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOjg0Mzg5YTdkLTNhMDctYWY0Mi1hZTU1LWRjMmZkYjEwNmRhZCIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDpGRUI5NTIyNkU4ODMxMUVDQjJFMkM5N0E5MjMzNTgyQSIgeG1wTU06SW5zdGFuY2VJRD0ieG1wLmlpZDpGRUI5NTIyNUU4ODMxMUVDQjJFMkM5N0E5MjMzNTgyQSIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgMjMuMiAoV2luZG93cykiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpmOGQ2MGQ5Mi0wNTA4LTc0NGItYWYxZS01YTQ0MzNiNjM5NzYiIHN0UmVmOmRvY3VtZW50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"

CSS = """
body {
    font-family: Arial, sans-serif;
    background: #f4f7fb;
    color: #1f2937;
    margin: 0;
}
.container {
    max-width: 1240px;
    margin: 0 auto;
    padding: 24px;
}
.card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    margin-bottom: 18px;
}
.hero {
    background: linear-gradient(135deg, #0f172a, #1d4ed8);
    color: white;
}
.hero-logo-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 16px;
}
.hero-logo {
    width: 92px;
    height: 92px;
    object-fit: contain;
    border-radius: 18px;
    background: rgba(255,255,255,0.12);
    padding: 10px;
    box-shadow: 0 10px 24px rgba(0,0,0,0.18);
}
.hero .sub {
    color: rgba(255,255,255,0.86);
    font-size: 15px;
}
.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.15);
    font-size: 12px;
    font-weight: bold;
}
.grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
}
.grid-2 {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 18px;
}
.step-strip {
    display: grid;
    grid-template-columns: 1.2fr 1.3fr 1fr;
    gap: 16px;
    align-items: start;
}
.step-panel {
    background: #f8fbff;
    border: 1px solid #dbeafe;
    border-radius: 14px;
    padding: 16px;
    height: 100%;
    box-sizing: border-box;
}
.step-kicker {
    font-size: 12px;
    font-weight: 700;
    color: #2563eb;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
}
.metric {
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 16px;
    background: #fff;
}
.metric .label {
    color: #6b7280;
    font-size: 13px;
}
.metric .value {
    font-size: 28px;
    font-weight: 700;
    margin-top: 6px;
}
.demo-box {
    background: #eef5ff;
    border: 1px solid #c7dcff;
    border-radius: 14px;
    padding: 14px;
}
.note {
    color: #4b5563;
    font-size: 14px;
    line-height: 1.7;
}
.callout {
    background: #f9fafb;
    border-left: 4px solid #2563eb;
    padding: 12px 14px;
    border-radius: 8px;
    margin-top: 12px;
}
.relative-row {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 10px;
}
.relative-row.me {
    background: #eef5ff;
    border-color: #93c5fd;
}
form {
    display: grid;
    gap: 12px;
}
.inline-form {
    display: flex;
    gap: 10px;
    align-items: end;
    flex-wrap: wrap;
}
.inline-form .grow {
    flex: 1 1 240px;
}
label {
    font-weight: 600;
    font-size: 14px;
}
input, select {
    width: 100%;
    padding: 10px;
    border-radius: 10px;
    border: 1px solid #d1d5db;
    box-sizing: border-box;
    margin-top: 6px;
}
button {
    background: #2563eb;
    color: white;
    border: 0;
    border-radius: 10px;
    padding: 12px 16px;
    cursor: pointer;
    font-weight: 700;
}
button.secondary, .tab-link {
    background: white;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
}
.tab-group {
    display: inline-flex;
    gap: 10px;
    margin: 6px 0 14px;
    flex-wrap: wrap;
}
.tab-link {
    text-decoration: none;
    padding: 10px 14px;
    border-radius: 999px;
    font-weight: 700;
}
.tab-link.active {
    background: #2563eb;
    color: white;
    border-color: #2563eb;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    border-bottom: 1px solid #e5e7eb;
    padding: 10px;
    text-align: left;
    font-size: 14px;
}
.small {
    font-size: 13px;
    color: #6b7280;
}
.success {
    background: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 16px;
}
@media (max-width: 1024px) {
    .step-strip, .grid-4, .grid-2 {
        grid-template-columns: 1fr;
    }
}
"""


def h(value: object) -> str:
    return escape(str(value))


def render_table(rows, columns):
    header = "".join(f"<th>{h(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{h(row.get(key, ''))}</td>" for key, _ in columns) + "</tr>")
    if not body:
        body.append(f"<tr><td colspan='{len(columns)}'>No data</td></tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def streak_icons(days: int) -> str:
    days = int(days or 0)
    if days <= 0:
        return "—"
    if days <= 3:
        return " ".join("🔥" for _ in range(days))
    extra_days = days - 3
    return f"🔥 🔥 🔥 +{extra_days}"


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        initialize_database()
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        message = params.get("message", [""])[0]
        agent_id = self._pick_agent(params)
        leader_view = params.get("leader_view", ["relative"])[0]
        if leader_view not in {"relative", "global"}:
            leader_view = "relative"
        self._respond(self.render_page(agent_id, message, leader_view))

    def do_POST(self):
        initialize_database()
        content_length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(content_length).decode("utf-8"))

        agent_id = int(form.get("agent_id", ["1"])[0])
        module_name = form.get("module_name", ["FSC Compliance Sprint"])[0]
        quiz_score = int(form.get("quiz_score", ["100"])[0])
        bio_rhythm = form.get("bio_rhythm_respected", ["0"])[0] == "1"
        leader_view = form.get("leader_view", ["relative"])[0]

        result = create_study_session(
            agent_id=agent_id,
            module_name=module_name,
            quiz_score=quiz_score,
            bio_rhythm_respected=bio_rhythm,
        )

        message = (
            f"Demo 成功：系統已新增 session #{result.session_id}，"
            f"本次共加 {result.points_added} 分。{result.streak_message}"
        )
        query = urlencode({"agent_id": agent_id, "leader_view": leader_view, "message": message})
        self.send_response(303)
        self.send_header("Location", f"/?{query}")
        self.end_headers()

    def _pick_agent(self, params):
        agents = get_agents()
        default_id = agents[0]["agent_id"] if agents else 1
        return int(params.get("agent_id", [default_id])[0])

    def _respond(self, html_text: str):
        body = html_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def render_page(self, agent_id: int, message: str, leader_view: str) -> str:
        agents = get_agents()
        if not agents:
            return "<h1>請先執行 python seed_demo.py</h1>"

        snapshot = get_agent_snapshot(agent_id)
        relative_rows = get_relative_leaderboard(agent_id)
        global_rows = get_global_top_n()
        for row in global_rows:
            row["streak_visual"] = streak_icons(row["current_streak_days"])
        branch_rows = get_branch_vs_branch()
        ledger_rows = get_recent_ledger(agent_id)

        agent_options = []
        for agent in agents:
            selected = " selected" if agent["agent_id"] == agent_id else ""
            label = f"{agent['agent_name']} ({agent['branch_name']})"
            agent_options.append(f"<option value='{agent['agent_id']}'{selected}>{h(label)}</option>")

        relative_html = []
        for row in relative_rows:
            klass = "relative-row me" if row["is_current_user"] else "relative-row"
            marker = " ← 現在展示中的 Agent" if row["is_current_user"] else ""
            relative_html.append(
                f"<div class='{klass}'>"
                f"<strong>{h(row['agent_name'])}</strong> — {h(row['branch_name'])}<br>"
                f"Weekly Points: <strong>{row['weekly_points_total']}</strong>"
                f" <span style='margin-left:10px;'>Lifetime Points: <strong>{row['lifetime_points']}</strong></span>"
                f" <span style='margin-left:10px;'>Streak: {streak_icons(row['current_streak_days'])}</span>{h(marker)}"
                f"</div>"
            )

        fire_icons = streak_icons(snapshot["current_streak_days"]) if int(snapshot["current_streak_days"] or 0) > 0 else "尚未形成 streak"
        shield_icons = " ".join("🛡️" for _ in range(snapshot["active_shields_count"])) or "目前沒有 shield"
        success_html = f"<div class='success'>{h(message)}</div>" if message else ""

        leader_relative_query = urlencode({"agent_id": agent_id, "leader_view": "relative"})
        leader_global_query = urlencode({"agent_id": agent_id, "leader_view": "global"})
        relative_btn_class = "tab-link active" if leader_view == "relative" else "tab-link"
        global_btn_class = "tab-link active" if leader_view == "global" else "tab-link"

        if leader_view == "global":
            leaderboard_title = "Global Top 10"
            leaderboard_note = "這個榜單適合給管理層看整體衝刺表現；現在也能同步看到每位使用者的 streak 火花，讓大家同時看到分數與學習動能。"
            leaderboard_body = render_table(global_rows, [('rank', 'Rank'), ('agent_name', 'Agent'), ('branch_name', 'Branch'), ('weekly_points_total', 'Weekly Points'), ('streak_visual', 'Streak')])
        else:
            leaderboard_title = "Relative Leaderboard"
            leaderboard_note = "這裡以目前展示中的 Agent 為中心，呈現前後各 2 名；不顯示全域名次，只聚焦在你前後的人。同時補上 Lifetime Points 與 streak 火花，讓你更容易看出自己和前後使用者的差距。"
            leaderboard_body = "".join(relative_html)

        return f"""
<!DOCTYPE html>
<html lang='zh-Hant'>
<head>
    <meta charset='UTF-8'>
    <title>Social Arena Client Demo</title>
    <style>{CSS}</style>
</head>
<body>
<div class='container'>
    <div class='card hero'>
        <div class='hero-logo-wrap'>
            <img class='hero-logo' src='{LOGO_DATA_URI}' alt='Social Arena logo'>
        </div>
        <div class='badge'>Demo Mode</div>
        <h1>Social Arena — Streak Shield Leaderboard</h1>
        <p class='sub'>這個版本不是單純展示排行榜，而是展示：如何用 streak、shield 與 relative leaderboard，讓業務員更願意每天回來學習。</p>
        <p class='sub'>目前週期：{h(current_epoch_week())}</p>
    </div>

    {success_html}

    <div class='card'>
        <div class='step-strip'>
            <div class='step-panel'>
                <div class='step-kicker'>Step 1</div>
                <h2>切換展示中的 Agent</h2>
                <p class='note'>選取Agent，下面 Snapshot、Streak、Shield、Leaderboard、Ledger 就全部切到那位 Agent，而且 Leaderboard 會自動回到預設的 Relative Leaderboard。</p>
                <form method='get' action='/'>
                    <label>目前展示中的 Agent
                        <select name='agent_id' onchange='this.form.submit()'>{''.join(agent_options)}</select>
                    </label>
                    <input type='hidden' name='leader_view' value='relative'>
                    <noscript><button type='submit'>切換展示 Agent</button></noscript>
                </form>
                <div class='callout'>所屬分行：<strong>{h(snapshot['branch_name'])}</strong><br>現在展示中的 Agent：<strong>{h(snapshot['agent_name'])}</strong></div>
            </div>

            <div class='step-panel'>
                <div class='step-kicker'>Step 2</div>
                <h2>模擬這位 Agent 今天的一次學習</h2>
                <p class='note'>送出後，系統會新增一筆學習事件，並同步更新 Weekly Points、Lifetime Points、Streak、Shield 與 Ledger。</p>
                <form method='post'>
                    <input type='hidden' name='leader_view' value='{h(leader_view)}'>
                    <label>這次要幫哪位 Agent 新增學習事件
                        <select name='agent_id'>{''.join(agent_options)}</select>
                    </label>
                    <label>今天學習的模組
                        <input type='text' name='module_name' value='FSC Compliance Sprint'>
                    </label>
                    <div class='inline-form'>
                        <label class='grow'>小考分數
                            <input type='number' name='quiz_score' value='100' min='0' max='100'>
                        </label>
                        <label class='grow'>
                            <input type='checkbox' name='bio_rhythm_respected' value='1' checked>
                            觸發 +2 Bio-Rhythm bonus
                        </label>
                    </div>
                    <button type='submit'>送出這次 Demo Sprint</button>
                </form>
            </div>

            <div class='step-panel'>
                <div class='step-kicker'>Step 3</div>
                <h2>測試memo</h2>
                <div class='demo-box'>
                    <strong>Demo Script</strong>
                    <ol>
                        <li>先切換一位 Agent，確認整個頁面是 live 的。</li>
                        <li>送一筆新學習事件，確認系統不是靜態 Mockup。</li>
                        <li>切換排行榜視角，確認個人激勵與管理視角都支援。</li>
                        <li>打開 Ledger，確認分數是可稽核、可追溯的。</li>
                    </ol>
                </div>
                <div class='callout'>目的:<strong>可持續的學習行為系統。</strong></div>
            </div>
        </div>
    </div>

    <div class='card'>
        <h2>Agent Snapshot</h2>
        <div class='grid-4'>
            <div class='metric'><div class='label'>本週分數</div><div class='value'>{snapshot['weekly_points']}</div></div>
            <div class='metric'><div class='label'>Lifetime Points</div><div class='value'>{snapshot['lifetime_points']}</div></div>
            <div class='metric'><div class='label'>Current Streak</div><div class='value'>{snapshot['current_streak_days']} 天</div></div>
            <div class='metric'><div class='label'>Active Shields</div><div class='value'>{snapshot['active_shields_count']}</div></div>
        </div>
        <p class='small'>所屬分行：{h(snapshot['branch_name'])} ｜ 展示人物：{h(snapshot['agent_name'])}</p>
    </div>

    <div class='grid-2'>
        <div>
            <div class='card'>
                <h2>Leaderboard View</h2>
                <div class='tab-group'>
                    <a class='{relative_btn_class}' href='/?{leader_relative_query}'>Relative Leaderboard</a>
                    <a class='{global_btn_class}' href='/?{leader_global_query}'>Global Top 10</a>
                </div>
                <p class='note'>{h(leaderboard_note)}</p>
                <div class='callout'>目前檢視模式：<strong>{h(leaderboard_title)}</strong></div>
                <div style='margin-top: 14px;'>
                    {leaderboard_body}
                </div>
            </div>
        </div>

        <div>
            <div class='card'>
                <h2>Streak + Shield Visualizer</h2>
                <p style='font-size: 24px'>{fire_icons}</p>
                <p style='font-size: 22px'>Shield 庫存：{shield_icons}</p>
                <p class='note'>偶爾失誤也不會前功盡棄!!，休息一下再重新出發GOGO</p>
            </div>

            <div class='card'>
                <h2>Branch vs. Branch Arena</h2>
                <p class='note'>團隊戰!一起合作讓分行強大 Make Branch Great Again!</p>
                {render_table(branch_rows, [('rank', 'Rank'), ('branch_name', 'Branch'), ('city', 'City'), ('total_points', 'Points'), ('agent_count', 'Agents')])}
            </div>
        </div>
    </div>

    <div class='card'>
        <h2>Immutable Point Ledger（查核完整紀錄）</h2>
        <p class='note'>每次 module 完成、100 分 quiz bonus、bio-rhythm bonus，系統都新增一筆 ledger event，而不是直接覆寫總分。這讓系統能 audit、能重算，也比較符合金融級資料治理思維。</p>
        {render_table(ledger_rows, [('event_type', 'Event Type'), ('points_awarded', 'Points'), ('timestamp', 'Timestamp')])}
    </div>

    <div class='card'>
        <h2>作者最後總結</h2>
        <ul>
            <li>PointLedger：保留每次加分原因，未來 bug 時可追溯、可重算。</li>
            <li>LeaderboardStandings：排行榜是每週快取表，避免每次都從明細表硬算。</li>
            <li>AgentStreaks：把 streak 與 shield 當作獨立狀態機管理，不跟 agents 的表單混在一起。</li>
            <li>Weekly Reset：每週重新競賽，但 lifetime points 與歷史 streak 都會保留。</li>
        </ul>
    </div>
</div>
</body>
</html>
"""


def run_server():
    initialize_database()
    server = HTTPServer((HOST, PORT), DemoHandler)
    print(f"Client demo server running at http://{HOST}:{PORT}")
    print("First time? Run: python seed_demo.py")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
