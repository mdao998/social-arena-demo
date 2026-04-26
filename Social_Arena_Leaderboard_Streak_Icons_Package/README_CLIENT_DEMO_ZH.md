# Social Arena｜展示版說明

## 最短執行方式

```bash
python seed_demo.py
python app.py
```

然後打開瀏覽器：

```text
http://127.0.0.1:8888
```

## 展示順序建議

1. 先選一位 Agent，送出一次 Demo Sprint。
2. 指給客戶看：本週分數、Lifetime Points、Current Streak、Active Shields 有沒有變化。
3. 往下看 Relative Leaderboard，解釋為什麼不是只看全公司 Top 10。
4. 再看 Streak + Shield Visualizer，解釋它如何降低挫折感。
5. 最後看 Immutable Point Ledger，強調這不是只會覆蓋總分的簡易做法，而是能 audit 的設計。


可持續的學習行為系統。
- Relative leaderboard 讓中段使用者也有持續追趕的動機。
- Shield 設計讓使用者偶爾中斷也不會立刻放棄。
- Point ledger 讓每一筆點數都有來源，後續可以重算、追蹤與稽核。
