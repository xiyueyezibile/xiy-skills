#!/usr/bin/env python3
"""Render a self-contained crypto news + market-structure HTML report.

The input is a UTF-8 JSON file. This helper intentionally performs no network
request and never reads account credentials. It only converts already collected
public news and public market-structure facts into a portable HTML file.
"""

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def default_output_path() -> Path:
    return Path.cwd() / ".tmp" / "crypto-news-analysis-report" / ("%s-report.html" % now_stamp())


def safe_text(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def rows(items: Iterable[Dict[str, object]], columns: Sequence[str]) -> str:
    rendered: List[str] = []
    for item in items:
        rendered.append(
            "<tr>"
            + "".join("<td>%s</td>" % safe_text(item.get(column, "")) for column in columns)
            + "</tr>"
        )
    return "\n".join(rendered)


def list_items(items: Iterable[object]) -> str:
    return "\n".join("<li>%s</li>" % safe_text(item) for item in items)


def slug(value: str) -> str:
    output = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return output or "section"


def paragraph(text: object) -> str:
    return "<p>%s</p>" % safe_text(text)


def render_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "<ul>%s</ul>" % list_items(value)
    return paragraph(value)


def render_coin_reports(items: Iterable[Dict[str, object]]) -> str:
    blocks: List[str] = []
    for item in items:
        title = safe_text(item.get("symbol") or item.get("title") or "详情")
        verdict = item.get("verdict") if isinstance(item.get("verdict"), dict) else {}
        verdict_rows = [
            {"label": "方向判断", "value": verdict.get("direction") or item.get("direction")},
            {"label": "利好/利空落地", "value": verdict.get("landing") or item.get("landing")},
            {"label": "追进去风险", "value": verdict.get("chase_risk") or item.get("chase_risk")},
            {"label": "操作倾向", "value": verdict.get("action_bias") or item.get("action_bias")},
        ]
        verdict_html = "".join(
            '<div class="verdict-item"><span>%s</span><strong>%s</strong></div>' % (safe_text(row["label"]), safe_text(row["value"]))
            for row in verdict_rows
            if row["value"]
        )
        facts = item.get("time_facts") if isinstance(item.get("time_facts"), dict) else {}
        time_rows = [
            {"label": "发布时间", "value": facts.get("published_at") or item.get("published_at")},
            {"label": "事件/生效时间", "value": facts.get("event_time") or item.get("event_time")},
            {"label": "检索时间", "value": facts.get("retrieved_at") or item.get("retrieved_at")},
            {"label": "距当前多久", "value": facts.get("age") or item.get("age")},
            {"label": "时效性", "value": facts.get("timeliness") or item.get("timeliness")},
            {"label": "有效窗口/复核点", "value": facts.get("valid_window") or item.get("valid_window")},
        ]
        time_html = "".join(
            '<div><span class="pill">%s</span><br>%s</div>' % (safe_text(row["label"]), safe_text(row["value"]))
            for row in time_rows
        )
        pre_landing = item.get("pre_landing") if isinstance(item.get("pre_landing"), dict) else {}
        pre_landing_html = ""
        if pre_landing:
            pre_landing_rows = [
                {"label": "未来催化节点", "value": pre_landing.get("future_catalyst")},
                {"label": "当前阶段", "value": pre_landing.get("current_stage")},
                {"label": "剩余时间", "value": pre_landing.get("time_remaining")},
                {"label": "是否已被抢跑", "value": pre_landing.get("front_run_status")},
                {"label": "提前埋伏条件", "value": pre_landing.get("ambush_condition")},
                {"label": "兑现风险", "value": pre_landing.get("realization_risk")},
            ]
            pre_landing_html = '<div class="prelanding-grid">%s</div>' % "".join(
                '<div><span>%s</span><strong>%s</strong></div>' % (safe_text(row["label"]), safe_text(row["value"]))
                for row in pre_landing_rows
                if row["value"]
            )
        sections = [
            ("消息是什么", item.get("what_happened")),
            ("为什么利多/利空", item.get("why_bullish_bearish")),
            ("利好/利空效应落地了吗", item.get("landed_status")),
            ("是否已被定价", item.get("priced_in")),
            ("行情结构如何配合", item.get("market_structure")),
            ("股票代币额外说明", item.get("stock_token_notes")),
            ("后续观察点", item.get("watch_points")),
            ("主要风险", item.get("risks")),
        ]
        section_html = "".join(
            '<div class="analysis-block"><h4>%s</h4>%s</div>' % (safe_text(label), render_value(value))
            for label, value in sections
            if value
        )
        blocks.append(
            '<article class="coin-report" id="%s"><h3>%s</h3><div class="verdict-grid">%s</div><div class="time-grid">%s</div>%s%s</article>'
            % (slug(str(title)), title, verdict_html, time_html, pre_landing_html, section_html)
        )
    return "\n".join(blocks)


def render_details(details: Iterable[Dict[str, object]]) -> str:
    blocks: List[str] = []
    for item in details:
        title = safe_text(item.get("symbol") or item.get("title") or "详情")
        bullets = item.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        blocks.append(
            '<article class="coin-report" id="%s"><h3>%s</h3><ul>%s</ul></article>'
            % (slug(str(title)), title, list_items(bullets))
        )
    return "\n".join(blocks)


def render_position_followups(items: Iterable[Dict[str, object]]) -> str:
    blocks: List[str] = []
    for item in items:
        title = safe_text(item.get("symbol") or item.get("title") or "持仓")
        status_rows = [
            {"label": "仓位来源", "value": item.get("venue")},
            {"label": "跟踪状态", "value": item.get("tracking_status")},
            {"label": "上次开仓催化", "value": item.get("original_catalyst")},
            {"label": "事件时间", "value": item.get("event_time")},
            {"label": "当前落地情况", "value": item.get("landing_status")},
            {"label": "关键失效位", "value": item.get("invalidation")},
            {"label": "下一次复核", "value": item.get("next_review")},
        ]
        status_html = "".join(
            '<div><span>%s</span><strong>%s</strong></div>' % (safe_text(row["label"]), safe_text(row["value"]))
            for row in status_rows
            if row["value"]
        )
        detail_sections = [
            ("最新相关新闻/公告", item.get("latest_news")),
            ("落地判断", item.get("landing_commentary")),
            ("当前处理建议", item.get("action_note")),
            ("需要补充的成交细节", item.get("missing_trade_details")),
        ]
        detail_html = "".join(
            '<div class="analysis-block"><h4>%s</h4>%s</div>' % (safe_text(label), render_value(value))
            for label, value in detail_sections
            if value
        )
        blocks.append(
            '<article class="coin-report followup-report" id="followup-%s"><h3>%s</h3><div class="followup-grid">%s</div>%s</article>'
            % (slug(str(title)), title, status_html, detail_html)
        )
    return "\n".join(blocks)


def render(payload: Dict[str, object]) -> str:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    coin_reports = payload.get("coin_reports") if isinstance(payload.get("coin_reports"), list) else []
    details = payload.get("details") if isinstance(payload.get("details"), list) else []
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    summary = payload.get("summary") if isinstance(payload.get("summary"), list) else []
    position_followups = payload.get("position_followups") if isinstance(payload.get("position_followups"), list) else []
    candidate_columns = [
        "symbol",
        "side",
        "event",
        "published_at",
        "event_time",
        "retrieved_at",
        "age",
        "timeliness",
        "market_structure",
        "status",
        "risk",
    ]
    source_columns = ["source_name", "title", "published_at", "event_time", "retrieved_at", "url"]
    stock_columns = ["symbol", "underlying_asset", "underlying_market", "contract_type", "underlying_type", "listed_at", "key_rule"]
    stock_token_refs = payload.get("stock_token_refs") if isinstance(payload.get("stock_token_refs"), list) else []
    coin_report_html = render_coin_reports(coin_reports) if coin_reports else render_details(details)
    matrix_html = ""
    if candidates:
        matrix_html = """
  <section id="candidates">
    <h2>摘要矩阵</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>标的</th><th>方向</th><th>消息事件</th><th>发布时间</th><th>事件/生效时间</th><th>检索时间</th><th>距当前多久</th><th>时效性</th><th>行情结构</th><th>状态</th><th>主要风险</th></tr></thead>
        <tbody>%s</tbody>
      </table>
    </div>
  </section>
""" % rows(candidates, candidate_columns)
    stock_token_html = ""
    if stock_token_refs:
        stock_token_html = """
  <section id="stock-token-refs">
    <h2>股票代币 / TradFi 合约信息</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>标的</th><th>底层资产</th><th>底层市场</th><th>Binance 合约类型</th><th>Underlying Type</th><th>上线/生效时间</th><th>关键规则</th></tr></thead>
        <tbody>%s</tbody>
      </table>
    </div>
  </section>
""" % rows(stock_token_refs, stock_columns)
    position_followup_html = ""
    if position_followups:
        position_followup_html = """
  <section id="position-followups">
    <h2>已开仓催化落地跟踪</h2>
    <p class="muted">此区块来自本地 position-watch 跟踪清单。跟单仓、子账户或其他交易所仓位在用户未声明平仓前持续跟踪；若缺少方向、入场价、数量，则不计算盈亏/R 倍数/仓位风险。</p>
    %s
  </section>
""" % render_position_followups(position_followups)
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>消息面选币分析报告</title>
  <style>
    :root { color-scheme: light; --bg:#f6f7fb; --card:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --accent:#2563eb; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }
    main { max-width:1180px; margin:0 auto; padding:28px; }
    h1 { margin:0 0 16px; font-size:30px; }
    h2 { margin:0 0 12px; font-size:20px; }
    h3 { margin:0 0 8px; font-size:17px; }
    section, .coin-report { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; margin:16px 0; box-shadow:0 8px 28px rgba(15,23,42,.05); }
    .meta-grid, .time-grid, .verdict-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; }
    .time-grid { margin:10px 0 14px; }
    .verdict-grid { margin:12px 0 14px; }
    .verdict-item { background:#fff7ed; border:1px solid #fed7aa; border-radius:14px; padding:12px; }
    .verdict-item span { display:block; color:#9a3412; font-size:12px; font-weight:700; margin-bottom:4px; }
    .verdict-item strong { display:block; color:#111827; font-size:16px; line-height:1.45; }
    .prelanding-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin:12px 0 14px; }
    .prelanding-grid div { background:#ecfdf5; border:1px solid #bbf7d0; border-radius:14px; padding:12px; }
    .prelanding-grid span { display:block; color:#047857; font-size:12px; font-weight:700; margin-bottom:4px; }
    .prelanding-grid strong { display:block; color:#111827; font-size:14px; line-height:1.5; }
    .followup-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin:12px 0 14px; }
    .followup-grid div { background:#eef2ff; border:1px solid #c7d2fe; border-radius:14px; padding:12px; }
    .followup-grid span { display:block; color:#4338ca; font-size:12px; font-weight:700; margin-bottom:4px; }
    .followup-grid strong { display:block; color:#111827; font-size:14px; line-height:1.5; }
    .analysis-block { border-top:1px solid var(--line); padding-top:12px; margin-top:12px; }
    .analysis-block h4 { margin:0 0 6px; font-size:14px; color:#374151; }
    .analysis-block p { margin:0; line-height:1.7; }
    .pill { display:inline-block; border-radius:999px; background:#eff6ff; color:#1d4ed8; padding:4px 10px; font-size:12px; font-weight:700; }
    table { width:100%%; border-collapse:collapse; font-size:13px; }
    th,td { border-bottom:1px solid var(--line); padding:9px 8px; text-align:left; vertical-align:top; }
    th { background:#f9fafb; color:#374151; position:sticky; top:0; }
    .table-wrap { overflow-x:auto; }
    .muted { color:var(--muted); }
    a { color:var(--accent); text-decoration:none; }
    a:hover { text-decoration:underline; }
    ul { margin:8px 0 0 20px; padding:0; }
  </style>
</head>
<body>
<main>
  <h1>消息面选币分析报告</h1>
  <section id="meta">
    <h2>数据时间</h2>
    <div class="meta-grid">
      <div><span class="pill">当前研究时间</span><br>%s</div>
      <div><span class="pill">消息检索截止</span><br>%s</div>
      <div><span class="pill">行情数据时间</span><br>%s</div>
      <div><span class="pill">时效性口径</span><br>%s</div>
    </div>
  </section>
  <section id="summary">
    <h2>结论摘要</h2>
    <ul>%s</ul>
  </section>
  %s
  <section id="coin-reports">
    <h2>逐币消息面深度分析</h2>
    %s
  </section>
  %s
  %s
  <section id="sources">
    <h2>来源列表</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>来源</th><th>标题</th><th>发布时间</th><th>事件/生效时间</th><th>检索时间</th><th>链接</th></tr></thead>
        <tbody>%s</tbody>
      </table>
    </div>
  </section>
  <section id="disclaimer">
    <h2>声明</h2>
    <p class="muted">仅为基于公开信息和公开行情的高风险研究记录，不构成投资建议；本流程不读取账户、不计算仓位、不生成订单、不调用交易写接口。</p>
  </section>
</main>
</body>
</html>
""" % (
        safe_text(meta.get("research_time")),
        safe_text(meta.get("news_cutoff")),
        safe_text(meta.get("market_data_time")),
        safe_text(meta.get("timeliness_policy")),
        list_items(summary),
        position_followup_html,
        coin_report_html,
        stock_token_html,
        matrix_html,
        rows(sources, source_columns),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="UTF-8 JSON report payload")
    parser.add_argument("--output", help="HTML output path; defaults to .tmp/crypto-news-analysis-report/<timestamp>-report.html")
    args = parser.parse_args(argv)
    input_path = Path(args.input).expanduser()
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input JSON must be an object")
    output_path = Path(args.output).expanduser() if args.output else default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render(payload), encoding="utf-8")
    resolved_output = output_path.resolve()
    print(json.dumps({"status": "ok", "output": str(resolved_output), "file_url": resolved_output.as_uri()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
