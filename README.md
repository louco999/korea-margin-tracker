# Korea Margin Tracker

自动抓取并追踪 **韩国股市信用交易融资余额（신용거래융자）** 变化。

数据源：[韩国金融投资协会 KOFIA FreeSIS](https://freesis.kofia.or.kr/) 公开接口（`STATSCUSUBMAIN01`）。

> 全市场融资余额是 **日频** 指标（交易日更新），不是盘中 tick 实时。本仓库通过 GitHub Actions 每个工作日自动拉取并入库，形成可持续的时间序列。

---

## Latest snapshot

<!-- LATEST:START -->
| Field | Value |
|---|---|
| **As of** | `2026-08-20` |
| **Margin loan (신용거래융자)** | **31.89 trillion KRW** |
| **Day change** | `+0.58` trillion KRW |
| **Securities-backed loan** | 25.38 T |
| **Credit total** | 57.30 T |
| **Investor deposits** | 105.35 T |
| **Fetched at (UTC)** | `2026-08-24T02:22:46Z` |
<!-- LATEST:END -->

![Margin loan chart](charts/margin_balance.png?v=20260820)

原始数据：[`data/margin_balance.csv`](data/margin_balance.csv) · 最新快照：[`data/latest.json`](data/latest.json)

---

## 指标说明

| 字段 | 韩文 | 含义 |
|------|------|------|
| `margin_loan` | 신용거래융자 | **融资余额**（主杠杆指标） |
| `short_sale` | 신용거래대주 | 融券余额 |
| `securities_backed_loan` | 예탁증권담보융자 | 证券担保贷款 |
| `credit_total` | 합계 | 信用供与合计 |
| `investor_deposit` | 투자자예탁금 | 投资者预托金（散户子弹购买力） |

单位：万亿韩元（trillion KRW）。API 原始单位为百万韩元，入库时已换算。

---

## 自动更新

GitHub Actions 工作流：`.github/workflows/update.yml`

| 触发 | 时间 |
|------|------|
| 工作日定时 | 01:00 UTC、10:00 UTC（约 10:00 / 19:00 KST） |
| 手动 | Actions → **Update Korea margin data** → Run workflow |
| 代码变更 | push 到 `main` 且改动 `src/` 时 |

每次成功拉取会：

1. 合并最新约 15 个交易日数据进 CSV  
2. 重绘 `charts/margin_balance.png?v=20260820`  
3. 更新 README 最新快照表  
4. 自动 commit / push（仅在有变化时）

---

## 本地运行

```bash
git clone https://github.com/louco999/korea-margin-tracker.git
cd korea-margin-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 拉取并更新
python -m src.update

# 仅用已有 CSV 重画图 / 刷新 README
python -m src.update --skip-fetch
```

只看接口返回：

```bash
python -m src.fetch_kofia
```

---

## 项目结构

```
korea-margin-tracker/
├── src/
│   ├── fetch_kofia.py   # KOFIA FreeSIS 抓取
│   ├── storage.py       # CSV 合并存储
│   ├── chart.py         # 绘图
│   └── update.py        # 一键更新入口
├── data/
│   ├── margin_balance.csv
│   └── latest.json
├── charts/
│   └── margin_balance.png
└── .github/workflows/update.yml
```

---

## 数据说明

- **主序列**：KOFIA 官方日频；每次请求返回最近约 15 个交易日，历史靠持续抓取累积。  
- **seed 行**：仓库初始化时写入的历史关键节点（公开报道交叉核实），`source=seed`。同日期一旦被 API 覆盖，以 API 为准。  
- **免责声明**：本项目仅供研究/学习，不构成投资建议。数据以 KOFIA 原文为准。

---

## License

MIT
