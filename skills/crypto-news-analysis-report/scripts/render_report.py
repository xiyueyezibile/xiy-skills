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


REPORT_TEMPLATE_VERSION = "crypto-news-analysis-report/v5-20260823-full-volume-analysis"
FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT = 10_000_000
CHASE_RISK_LEVELS = ("低", "中低", "中", "中高", "高", "极高")
REPORTABLE_CHASE_RISKS = {"低", "中低", "中", "中高"}
HOTSPOT_STAGES = {"萌芽", "扩散", "拥挤", "退潮"}
HOTSPOT_HEAT_LEVELS = {"低", "中", "高"}


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def default_output_path() -> Path:
    return Path.cwd() / ".tmp" / "crypto-news-analysis-report" / ("%s-skill-selection-report.html" % now_stamp())


def safe_text(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def rows(items: Iterable[Dict[str, object]], columns: Sequence[str]) -> str:
    rendered: List[str] = []
    for item in items:
        rendered.append(
            "<tr>"
            + "".join("<td>%s</td>" % safe_text(render_cell(item.get(column, ""))) for column in columns)
            + "</tr>"
        )
    return "\n".join(rendered)


def source_rows(items: Iterable[Dict[str, object]], columns: Sequence[str]) -> str:
    rendered: List[str] = []
    for item in items:
        cells: List[str] = []
        for column in columns:
            value = item.get(column, "")
            if column == "url":
                url = safe_href(value)
                cells.append(
                    '<td><a href="%s" target="_blank" rel="noreferrer">打开原始来源</a></td>' % url
                    if url
                    else "<td>%s</td>" % safe_text(value)
                )
            else:
                cells.append("<td>%s</td>" % safe_text(render_cell(value)))
        rendered.append("<tr>%s</tr>" % "".join(cells))
    return "\n".join(rendered)


def render_cell(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value) if value is not None else ""


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


def safe_href(value: object) -> str:
    url = str(value or "").strip()
    if url.startswith(("https://", "http://")):
        return html.escape(url, quote=True)
    return ""


def render_news_evidence(item: Dict[str, object], sources: Iterable[Dict[str, object]]) -> str:
    evidence = item.get("news_evidence")
    evidence_items = evidence if isinstance(evidence, list) else []
    source_refs = item.get("source_refs")
    refs = {str(value) for value in source_refs} if isinstance(source_refs, list) else set()
    if refs:
        evidence_items = evidence_items + [
            source
            for source in sources
            if isinstance(source, dict)
            and (
                str(source.get("url")) in refs
                or str(source.get("source_name")) in refs
                or str(source.get("title")) in refs
            )
        ]
    if not evidence_items:
        return (
            '<div class="evidence-warning"><strong>消息依据未逐项绑定</strong>'
            "<p>当前条目只有汇总描述，无法从本章节直接核对原始消息。新报告必须补充来源链接、来源层级和关键事实后才能生成。</p></div>"
        )

    cards: List[str] = []
    seen_urls = set()
    for source in evidence_items:
        if not isinstance(source, dict):
            continue
        url = safe_href(source.get("url"))
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        title = safe_text(source.get("title") or source.get("source_name") or "消息来源")
        title_html = '<a href="%s" target="_blank" rel="noreferrer">%s</a>' % (url, title) if url else title
        facts = source.get("key_facts")
        facts_html = render_value(facts) if facts else ""
        cards.append(
            '<div class="evidence-card"><h5>%s</h5>'
            '<div class="evidence-meta"><span>来源：%s</span><span>层级：%s</span><span>可靠性：%s</span>'
            '<span>发布：%s</span><span>事件：%s</span><span>检索：%s</span></div>%s</div>'
            % (
                title_html,
                safe_text(source.get("source_name")),
                safe_text(source.get("source_tier") or "未标注"),
                safe_text(source.get("reliability") or "未标注"),
                safe_text(source.get("published_at")),
                safe_text(source.get("event_time")),
                safe_text(source.get("retrieved_at")),
                facts_html,
            )
        )
    return '<div class="analysis-block evidence-block"><h4>消息依据与可靠性</h4>%s</div>' % "".join(cards)


def render_asset_profile(item: Dict[str, object]) -> str:
    profile = item.get("asset_profile") if isinstance(item.get("asset_profile"), dict) else {}
    profile_rows = [
        {"label": "资产类型", "value": profile.get("asset_type") or item.get("asset_type")},
        {"label": "所属行业/赛道", "value": profile.get("sector") or item.get("sector")},
        {"label": "细分模块", "value": profile.get("subsector") or item.get("subsector")},
        {"label": "核心业务/协议", "value": profile.get("core_business") or item.get("core_business")},
        {"label": "主要价格驱动", "value": profile.get("price_drivers") or item.get("price_drivers")},
        {"label": "同风险簇", "value": profile.get("risk_cluster") or item.get("risk_cluster")},
    ]
    profile_html = "".join(
        '<div><span>%s</span><strong>%s</strong></div>'
        % (safe_text(row["label"]), safe_text(render_cell(row["value"])))
        for row in profile_rows
        if row["value"]
    )
    if not profile_html:
        return ""
    background = profile.get("background") or item.get("background")
    background_html = (
        '<div class="asset-background"><span>背景介绍</span>%s</div>' % render_value(background)
        if background
        else ""
    )
    return '<div class="asset-profile-grid">%s</div>%s' % (profile_html, background_html)


def render_second_stage(item: Dict[str, object]) -> str:
    second_stage = item.get("second_stage") if isinstance(item.get("second_stage"), dict) else {}
    rows = [
        ("已完成传导", second_stage.get("completed_transmission")),
        ("未完成传导", second_stage.get("remaining_transmission")),
        ("下一验证节点", second_stage.get("next_validation")),
        ("二阶段触发", second_stage.get("trigger")),
        ("保守目标", second_stage.get("conservative_target")),
        ("结构失效位", second_stage.get("invalidation")),
        ("剩余净盈亏比", second_stage.get("remaining_net_risk_reward")),
        ("行情耗尽信号", second_stage.get("exhaustion_signals")),
    ]
    return "".join(
        '<div class="analysis-block"><h4>%s</h4>%s</div>' % (safe_text(label), render_value(value))
        for label, value in rows
        if value
    )


def render_coin_reports(items: Iterable[Dict[str, object]], sources: Iterable[Dict[str, object]]) -> str:
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
        second_stage_html = render_second_stage(item)
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
            '<article class="coin-report" id="%s"><h3>%s</h3>%s<div class="verdict-grid">%s</div><div class="time-grid">%s</div>%s%s%s%s</article>'
            % (
                slug(str(title)),
                title,
                render_asset_profile(item),
                verdict_html,
                time_html,
                pre_landing_html,
                render_news_evidence(item, sources),
                second_stage_html,
                section_html,
            )
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


def render_market_hotspots(hotspots: Dict[str, object]) -> str:
    if not hotspots:
        return ""
    overview_rows = [
        ("数据时间", hotspots.get("as_of")),
        ("市场状态", hotspots.get("market_regime")),
        ("涨跌广度", hotspots.get("breadth")),
        ("成交额集中度", hotspots.get("liquidity_concentration")),
        ("衍生品环境", hotspots.get("derivatives_context")),
    ]
    overview_html = "".join(
        '<div><span>%s</span><strong>%s</strong></div>'
        % (safe_text(label), safe_text(render_cell(value)))
        for label, value in overview_rows
        if value
    )
    theme_cards: List[str] = []
    themes = hotspots.get("themes") if isinstance(hotspots.get("themes"), list) else []
    for item in themes:
        if not isinstance(item, dict):
            continue
        source_links = []
        for source_index, source in enumerate(item.get("sources", []), start=1):
            url = safe_href(source)
            if url:
                source_links.append(
                    '<a href="%s" target="_blank" rel="noreferrer">来源 %d</a>'
                    % (url, source_index)
                )
        theme_cards.append(
            '<article class="hotspot-card"><div class="hotspot-heading"><strong>%s</strong>'
            '<span>%s · 热度%s</span></div>'
            '<p><b>代表标的：</b>%s</p><p><b>量价/广度证据：</b>%s</p>'
            '<p><b>催化与扩散：</b>%s</p><p><b>拥挤与反向风险：</b>%s</p>'
            '<p><b>选币用途：</b>%s</p><p><b>数据来源：</b>%s</p></article>'
            % (
                safe_text(item.get("name")),
                safe_text(item.get("stage")),
                safe_text(item.get("heat_level")),
                safe_text(render_cell(item.get("representative_symbols"))),
                safe_text(render_cell(item.get("evidence"))),
                safe_text(item.get("catalyst")),
                safe_text(item.get("crowding_risk")),
                safe_text(item.get("selection_use")),
                " · ".join(source_links),
            )
        )
    no_theme_html = ""
    if not theme_cards:
        no_theme_html = '<p class="muted">%s</p>' % safe_text(hotspots.get("no_dominant_theme_reason"))
    return (
        '<section id="market-hotspots"><h2>市场热点参考</h2>'
        '<p class="hotspot-notice">热点只用于判断资金偏好、叙事扩散和相关性风险，不能单独把标的升级为候选或替代消息、结构、盈亏比与账户门禁。</p>'
        '<div class="hotspot-overview">%s</div><div class="hotspot-grid">%s</div>%s'
        '<div class="analysis-block"><h4>对本轮选币的影响</h4>%s</div>'
        '<div class="analysis-block"><h4>局限与反向解释</h4>%s</div></section>'
        % (
            overview_html,
            "".join(theme_cards),
            no_theme_html,
            render_value(hotspots.get("selection_implication")),
            render_value(hotspots.get("limitations")),
        )
    )


def render_position_followups(items: Iterable[Dict[str, object]], sources: Iterable[Dict[str, object]]) -> str:
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
            '<article class="coin-report followup-report" id="followup-%s"><h3>%s</h3>%s<div class="followup-grid">%s</div>%s%s%s</article>'
            % (
                slug(str(title)),
                title,
                render_asset_profile(item),
                status_html,
                render_news_evidence(item, sources),
                render_second_stage(item),
                detail_html,
            )
        )
    return "\n".join(blocks)


def risk_class(value: object) -> str:
    level = normalize_chase_risk(value)
    if level in {"高", "极高"}:
        return "risk-high"
    if level in {"中", "中高"}:
        return "risk-medium"
    return "risk-low"


def normalize_chase_risk(value: object) -> Optional[str]:
    text = str(value or "").strip()
    for level in ("极高", "中高", "中低", "高", "中", "低"):
        if text == level or text.startswith(level + "，") or text.startswith(level + ","):
            return level
    return None


def render_risk_landing_overview(
    coin_reports: Iterable[Dict[str, object]],
    position_followups: Iterable[Dict[str, object]],
    candidates: Iterable[Dict[str, object]],
) -> str:
    cards: List[str] = []
    candidate_symbols = {
        str(item.get("symbol") or item.get("title") or "").strip()
        for item in candidates
    }
    for item in position_followups:
        symbol = str(item.get("symbol") or item.get("title") or "持仓")
        action = item.get("action_note") or "缺少处理建议"
        landing = item.get("landing_status") or "落地状态待补"
        warning = item.get("risk_warning") or item.get("invalidation") or "风险条件待补"
        cards.append(
            '<a class="risk-card risk-high" href="#followup-%s"><span class="risk-kicker">已开仓 · 优先处理</span>'
            "<strong>%s</strong><p><b>当前落地：</b>%s</p><p><b>风险/失效：</b>%s</p><p><b>现在动作：</b>%s</p></a>"
            % (slug(symbol), safe_text(symbol), safe_text(landing), safe_text(warning), safe_text(action))
        )
    for item in coin_reports:
        symbol = str(item.get("symbol") or item.get("title") or "标的")
        verdict = item.get("verdict") if isinstance(item.get("verdict"), dict) else {}
        chase_risk = verdict.get("chase_risk") or item.get("chase_risk") or "待评估"
        landing = verdict.get("landing") or item.get("landing") or item.get("landed_status") or "待评估"
        action = verdict.get("action_bias") or item.get("action_bias") or "待评估"
        novelty_status = str(item.get("novelty_status") or "").strip()
        repeat_penalty = item.get("repeat_penalty")
        if novelty_status == "cooldown":
            card_role = "冷却中 · 深度观察"
        elif novelty_status == "repeat_observation":
            card_role = "重复观察"
        elif novelty_status == "active_followup":
            card_role = "持仓跟踪"
        else:
            card_role = "新候选" if symbol in candidate_symbols else "深度观察"
        if repeat_penalty is not None:
            card_role = "%s · 重复惩罚 %s" % (card_role, safe_text(repeat_penalty))
        cards.append(
            '<a class="risk-card %s" href="#%s"><span class="risk-kicker">%s · 追入风险 %s</span>'
            "<strong>%s</strong><p><b>落地：</b>%s</p><p><b>现在动作：</b>%s</p></a>"
            % (
                risk_class(chase_risk),
                slug(symbol),
                card_role,
                safe_text(chase_risk),
                safe_text(symbol),
                safe_text(landing),
                safe_text(action),
            )
        )
    if not cards:
        return ""
    return (
        '<section id="risk-overview" class="risk-overview"><h2>风险与落地速览</h2>'
        '<p class="risk-lead">先看这里：已开仓标的置顶；红色代表当前不宜追入或必须优先降风险。点击任一卡片跳到完整依据。</p>'
        '<div class="risk-grid">%s</div></section>' % "".join(cards)
    )


def render_navigation(
    coin_reports: Iterable[Dict[str, object]],
    position_followups: Iterable[Dict[str, object]],
    has_market_hotspots: bool,
    has_audit: bool,
    has_stock_refs: bool,
    has_candidates: bool,
) -> str:
    links = [
        ("meta", "数据时间"),
        ("summary", "结论摘要"),
    ]
    if has_market_hotspots:
        links.append(("market-hotspots", "市场热点参考"))
    links.append(("risk-overview", "风险与落地速览"))
    if has_audit:
        links.append(("research-audit", "逐项研究审计"))
    if list(position_followups):
        links.append(("position-followups", "已开仓落地跟踪"))
        links.extend(
            ("followup-%s" % slug(str(item.get("symbol") or item.get("title") or "持仓")), "持仓 · %s" % str(item.get("symbol") or item.get("title") or "持仓"))
            for item in position_followups
        )
    links.append(("coin-reports", "逐币深度分析"))
    links.extend(
        (slug(str(item.get("symbol") or item.get("title") or "标的")), "分析 · %s" % str(item.get("symbol") or item.get("title") or "标的"))
        for item in coin_reports
    )
    if has_stock_refs:
        links.append(("stock-token-refs", "TradFi 合约信息"))
    if has_candidates:
        links.append(("candidates", "摘要矩阵"))
    links.extend([("sources", "来源列表"), ("disclaimer", "声明")])
    return '<nav class="report-nav" aria-label="报告目录"><strong>报告目录</strong>%s</nav>' % "".join(
        '<a href="#%s">%s</a>' % (safe_text(anchor), safe_text(label)) for anchor, label in links
    )


def validate_asset_profiles(payload: Dict[str, object]) -> None:
    required_profile_fields = (
        "asset_type",
        "sector",
        "subsector",
        "core_business",
        "price_drivers",
        "risk_cluster",
        "background",
    )
    for collection_name in ("coin_reports", "position_followups"):
        items = payload.get(collection_name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError("%s[%d] must be an object" % (collection_name, index))
            profile = item.get("asset_profile")
            if not isinstance(profile, dict):
                raise ValueError("%s[%d] requires asset_profile" % (collection_name, index))
            missing = [
                field
                for field in required_profile_fields
                if field not in profile or profile[field] is None or profile[field] == "" or profile[field] == []
            ]
            if missing:
                raise ValueError(
                    "%s[%d].asset_profile missing fields: %s"
                    % (collection_name, index, ", ".join(missing))
                )
            if not isinstance(profile["price_drivers"], list):
                raise ValueError("%s[%d].asset_profile.price_drivers must be a list" % (collection_name, index))

    for collection_name, required_fields in (
        ("candidates", ("sector", "subsector", "risk_cluster")),
        ("stock_token_refs", ("sector", "subsector", "core_business", "risk_cluster")),
    ):
        items = payload.get(collection_name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError("%s[%d] must be an object" % (collection_name, index))
            missing = [
                field
                for field in required_fields
                if field not in item or item[field] is None or item[field] == ""
            ]
            if missing:
                raise ValueError(
                    "%s[%d] missing asset classification fields: %s"
                    % (collection_name, index, ", ".join(missing))
                )


def validate_market_hotspots(payload: Dict[str, object]) -> None:
    hotspots = payload.get("market_hotspots")
    if hotspots is None:
        meta = payload.get("meta")
        if isinstance(meta, dict) and meta.get("report_contract") == "v5":
            raise ValueError("report_contract v5 requires market_hotspots")
        return
    if not isinstance(hotspots, dict):
        raise ValueError("market_hotspots must be an object")
    required_fields = (
        "as_of",
        "market_regime",
        "breadth",
        "liquidity_concentration",
        "derivatives_context",
        "themes",
        "selection_implication",
        "limitations",
    )
    missing = [
        field
        for field in required_fields
        if field not in hotspots
        or hotspots[field] is None
        or hotspots[field] == ""
        or (field != "themes" and hotspots[field] == [])
    ]
    if missing:
        raise ValueError("market_hotspots missing fields: %s" % ", ".join(missing))
    themes = hotspots["themes"]
    if not isinstance(themes, list):
        raise ValueError("market_hotspots.themes must be a list")
    if not themes and not hotspots.get("no_dominant_theme_reason"):
        raise ValueError(
            "market_hotspots.no_dominant_theme_reason is required when themes is empty"
        )
    theme_required_fields = (
        "name",
        "stage",
        "heat_level",
        "representative_symbols",
        "evidence",
        "catalyst",
        "crowding_risk",
        "selection_use",
        "sources",
    )
    for index, item in enumerate(themes):
        if not isinstance(item, dict):
            raise ValueError("market_hotspots.themes[%d] must be an object" % index)
        theme_missing = [
            field
            for field in theme_required_fields
            if field not in item or item[field] is None or item[field] == "" or item[field] == []
        ]
        if theme_missing:
            raise ValueError(
                "market_hotspots.themes[%d] missing fields: %s"
                % (index, ", ".join(theme_missing))
            )
        if item["stage"] not in HOTSPOT_STAGES:
            raise ValueError(
                "market_hotspots.themes[%d].stage must be one of: %s"
                % (index, ", ".join(sorted(HOTSPOT_STAGES)))
            )
        if item["heat_level"] not in HOTSPOT_HEAT_LEVELS:
            raise ValueError(
                "market_hotspots.themes[%d].heat_level must be one of: %s"
                % (index, ", ".join(sorted(HOTSPOT_HEAT_LEVELS)))
            )
        for field in ("representative_symbols", "evidence", "sources"):
            if not isinstance(item[field], list):
                raise ValueError(
                    "market_hotspots.themes[%d].%s must be a list" % (index, field)
                )
        if any(
            not isinstance(url, str) or not url.startswith(("https://", "http://"))
            for url in item["sources"]
        ):
            raise ValueError(
                "market_hotspots.themes[%d].sources must contain http(s) URLs" % index
            )


def validate_report_depth(payload: Dict[str, object]) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict) or meta.get("report_contract") not in {"v4", "v5"}:
        return

    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    source_lookup: Dict[str, Dict[str, object]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("url", "source_name", "title"):
            if source.get(key):
                source_lookup[str(source[key])] = source

    evidence_required = (
        "source_name",
        "title",
        "source_tier",
        "reliability",
        "published_at",
        "event_time",
        "retrieved_at",
        "url",
        "key_facts",
    )

    def validate_evidence(source: object, location: str) -> None:
        if not isinstance(source, dict):
            raise ValueError("%s must be an object" % location)
        evidence_missing = [
            field
            for field in evidence_required
            if field not in source or source[field] is None or source[field] == "" or source[field] == []
        ]
        if evidence_missing:
            raise ValueError("%s missing fields: %s" % (location, ", ".join(evidence_missing)))
        if not str(source["url"]).startswith(("https://", "http://")):
            raise ValueError("%s.url must be http(s)" % location)

    for collection_name in ("coin_reports", "position_followups"):
        items = payload.get(collection_name)
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValueError("%s[%d] must be an object" % (collection_name, index))
            evidence = item.get("news_evidence")
            refs = item.get("source_refs")
            if not (isinstance(evidence, list) and evidence) and not (isinstance(refs, list) and refs):
                raise ValueError("%s[%d] requires news_evidence or source_refs" % (collection_name, index))
            if isinstance(refs, list):
                for ref_index, ref in enumerate(refs):
                    source = source_lookup.get(str(ref))
                    if source is None:
                        raise ValueError(
                            "%s[%d].source_refs[%d] does not resolve: %s"
                            % (collection_name, index, ref_index, ref)
                        )
                    validate_evidence(
                        source,
                        "%s[%d].source_refs[%d]" % (collection_name, index, ref_index),
                    )
            if collection_name == "coin_reports":
                required_fields = (
                    "what_happened",
                    "why_bullish_bearish",
                    "landed_status",
                    "priced_in",
                    "market_structure",
                    "watch_points",
                    "risks",
                )
            else:
                required_fields = (
                    "original_catalyst",
                    "landing_status",
                    "latest_news",
                    "landing_commentary",
                    "action_note",
                    "invalidation",
                    "next_review",
                )
            missing = [
                field
                for field in required_fields
                if field not in item or item[field] is None or item[field] == "" or item[field] == []
            ]
            if missing:
                raise ValueError("%s[%d] missing depth fields: %s" % (collection_name, index, ", ".join(missing)))

            if isinstance(evidence, list):
                for evidence_index, source in enumerate(evidence):
                    validate_evidence(
                        source,
                        "%s[%d].news_evidence[%d]" % (collection_name, index, evidence_index),
                    )


def validate_full_universe_research(payload: Dict[str, object]) -> None:
    meta = payload.get("meta")
    if not isinstance(meta, dict) or meta.get("full_universe_research") is not True:
        return

    counts = payload.get("screening_counts")
    audit = payload.get("research_audit")
    liquidity_survivors = payload.get("liquidity_survivors")
    if not isinstance(counts, dict) or not isinstance(audit, list) or not isinstance(liquidity_survivors, list):
        raise ValueError(
            "full-universe report requires screening_counts, liquidity_survivors and research_audit"
        )

    survivor_count = counts.get("post_filter_survivors")
    researched_count = counts.get("researched_survivors")
    analyzed_count = counts.get("analyzed_survivors")
    threshold = counts.get("liquidity_threshold_quote_volume_usdt")
    if not isinstance(survivor_count, int) or not isinstance(researched_count, int) or not isinstance(analyzed_count, int):
        raise ValueError(
            "screening_counts must contain integer post_filter_survivors, researched_survivors and analyzed_survivors"
        )
    if threshold != FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT:
        raise ValueError(
            "full-universe liquidity_threshold_quote_volume_usdt must equal %d"
            % FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT
        )
    if survivor_count != researched_count:
        raise ValueError("full-universe research incomplete: researched_survivors != post_filter_survivors")
    if survivor_count != analyzed_count:
        raise ValueError("full-universe analysis incomplete: analyzed_survivors != post_filter_survivors")
    if len(audit) != survivor_count:
        raise ValueError("full-universe research incomplete: research_audit row count does not match survivors")
    if len(liquidity_survivors) != survivor_count:
        raise ValueError(
            "full-universe research incomplete: liquidity_survivors row count does not match survivors"
        )

    liquidity_by_symbol: Dict[str, object] = {}
    for index, item in enumerate(liquidity_survivors):
        if not isinstance(item, dict):
            raise ValueError("liquidity_survivors[%d] must be an object" % index)
        symbol = str(item.get("symbol") or "")
        quote_volume = item.get("quote_volume_24h_usdt")
        if not symbol:
            raise ValueError("liquidity_survivors[%d].symbol is required" % index)
        if symbol in liquidity_by_symbol:
            raise ValueError("liquidity_survivors symbols must be unique: %s" % symbol)
        if not isinstance(quote_volume, (int, float)) or quote_volume < FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT:
            raise ValueError(
                "liquidity_survivors[%d].quote_volume_24h_usdt must be >= %d"
                % (index, FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT)
            )
        liquidity_by_symbol[symbol] = quote_volume

    required_fields = (
        "symbol",
        "market_type",
        "contract_type",
        "quote_volume_24h_usdt",
        "checked_sources",
        "queries",
        "retrieved_at",
        "latest_event",
        "outcome",
        "status",
        "reason",
        "analysis_completed",
        "chase_risk",
        "analysis_summary",
        "news_conclusion",
        "market_structure_summary",
        "analyzed_timeframes",
        "market_data_time",
    )
    allowed_outcomes = {
        "opportunity",
        "watch",
        "no_valid_catalyst",
        "stale_or_priced",
        "source_conflict",
        "fetch_failed_unresolved",
    }
    audit_symbols: List[str] = []
    candidate_symbols = {
        str(item.get("symbol"))
        for item in payload.get("candidates", [])
        if isinstance(item, dict) and item.get("symbol")
    } if isinstance(payload.get("candidates"), list) else set()
    report_symbols = {
        str(item.get("symbol"))
        for item in payload.get("coin_reports", [])
        if isinstance(item, dict) and item.get("symbol")
    } if isinstance(payload.get("coin_reports"), list) else set()
    reportable_symbols = set()

    for index, item in enumerate(audit):
        if not isinstance(item, dict):
            raise ValueError("research_audit[%d] must be an object" % index)
        missing = [
            field
            for field in required_fields
            if field not in item or item[field] is None or item[field] == "" or item[field] == []
        ]
        if missing:
            raise ValueError("research_audit[%d] missing fields: %s" % (index, ", ".join(missing)))
        if not isinstance(item.get("checked_sources"), list) or not item["checked_sources"]:
            raise ValueError("research_audit[%d].checked_sources must be a non-empty list" % index)
        if any(not isinstance(source, str) or not source.startswith(("https://", "http://")) for source in item["checked_sources"]):
            raise ValueError("research_audit[%d].checked_sources must contain visited URLs" % index)
        if not isinstance(item.get("queries"), list) or not item["queries"]:
            raise ValueError("research_audit[%d].queries must be a non-empty list" % index)
        if not isinstance(item.get("deep_analysis_required"), bool):
            raise ValueError("research_audit[%d].deep_analysis_required must be boolean" % index)
        if item.get("analysis_completed") is not True:
            raise ValueError("research_audit[%d].analysis_completed must be true" % index)
        symbol = str(item["symbol"])
        audit_symbols.append(symbol)
        if symbol not in liquidity_by_symbol:
            raise ValueError("research_audit symbol is not in liquidity_survivors: %s" % symbol)
        quote_volume = item.get("quote_volume_24h_usdt")
        if not isinstance(quote_volume, (int, float)) or quote_volume < FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT:
            raise ValueError(
                "research_audit[%d].quote_volume_24h_usdt must be >= %d"
                % (index, FULL_UNIVERSE_LIQUIDITY_THRESHOLD_USDT)
            )
        if quote_volume != liquidity_by_symbol[symbol]:
            raise ValueError(
                "research_audit[%d].quote_volume_24h_usdt does not match liquidity_survivors"
                % index
            )
        analyzed_timeframes = item.get("analyzed_timeframes")
        if not isinstance(analyzed_timeframes, list) or set(analyzed_timeframes) != {"1d", "4h", "1h", "15m"}:
            raise ValueError(
                "research_audit[%d].analyzed_timeframes must contain exactly 1d, 4h, 1h and 15m"
                % index
            )
        chase_risk = normalize_chase_risk(item.get("chase_risk"))
        if chase_risk not in CHASE_RISK_LEVELS:
            raise ValueError(
                "research_audit[%d].chase_risk must start with one of: %s"
                % (index, ", ".join(CHASE_RISK_LEVELS))
            )
        if chase_risk in REPORTABLE_CHASE_RISKS:
            reportable_symbols.add(symbol)
        outcome = str(item["outcome"])
        if outcome not in allowed_outcomes:
            raise ValueError("research_audit[%d].outcome is invalid: %s" % (index, outcome))
        if outcome == "fetch_failed_unresolved":
            raise ValueError("full-universe research has unresolved fetch failure for %s" % symbol)
        if outcome in {"opportunity", "watch"} and symbol not in candidate_symbols:
            raise ValueError("researched opportunity/watch missing from candidates: %s" % symbol)
        if outcome == "opportunity" and item.get("deep_analysis_required") is not True:
            raise ValueError("opportunity must require deep analysis: %s" % symbol)
        if item.get("deep_analysis_required") is True and symbol not in report_symbols:
            raise ValueError("deep-analysis symbol missing from coin_reports: %s" % symbol)

    if len(set(audit_symbols)) != survivor_count:
        raise ValueError("research_audit symbols must be unique and match survivor count")
    if set(audit_symbols) != set(liquidity_by_symbol):
        missing = sorted(set(liquidity_by_symbol) - set(audit_symbols))
        extra = sorted(set(audit_symbols) - set(liquidity_by_symbol))
        raise ValueError(
            "research_audit symbols must exactly match liquidity_survivors; missing=%s extra=%s"
            % (", ".join(missing), ", ".join(extra))
        )
    missing_report_symbols = sorted(reportable_symbols - report_symbols)
    if missing_report_symbols:
        raise ValueError(
            "risk <= 中高 symbols missing from coin_reports: %s"
            % ", ".join(missing_report_symbols)
        )
    missing_candidate_symbols = sorted(reportable_symbols - candidate_symbols)
    if missing_candidate_symbols:
        raise ValueError(
            "risk <= 中高 symbols missing from candidates: %s"
            % ", ".join(missing_candidate_symbols)
        )
    reported_risk_eligible = counts.get("reported_risk_eligible")
    if reported_risk_eligible != len(reportable_symbols):
        raise ValueError(
            "screening_counts.reported_risk_eligible does not match risk <= 中高 audit rows"
        )
    deep_count = counts.get("deep_analysis")
    if deep_count is not None and deep_count != len(report_symbols):
        raise ValueError("screening_counts.deep_analysis does not match coin_reports")


def render(payload: Dict[str, object]) -> str:
    validate_asset_profiles(payload)
    validate_market_hotspots(payload)
    validate_report_depth(payload)
    validate_full_universe_research(payload)
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    candidates = payload.get("candidates") if isinstance(payload.get("candidates"), list) else []
    coin_reports = payload.get("coin_reports") if isinstance(payload.get("coin_reports"), list) else []
    details = payload.get("details") if isinstance(payload.get("details"), list) else []
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    summary = payload.get("summary") if isinstance(payload.get("summary"), list) else []
    market_hotspots = payload.get("market_hotspots") if isinstance(payload.get("market_hotspots"), dict) else {}
    position_followups = payload.get("position_followups") if isinstance(payload.get("position_followups"), list) else []
    screening_counts = payload.get("screening_counts") if isinstance(payload.get("screening_counts"), dict) else {}
    research_audit = payload.get("research_audit") if isinstance(payload.get("research_audit"), list) else []
    market_hotspots_html = render_market_hotspots(market_hotspots)
    candidate_columns = [
        "symbol",
        "sector",
        "subsector",
        "risk_cluster",
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
    stock_columns = [
        "symbol",
        "underlying_asset",
        "underlying_market",
        "sector",
        "subsector",
        "core_business",
        "risk_cluster",
        "contract_type",
        "underlying_type",
        "listed_at",
        "key_rule",
    ]
    stock_token_refs = payload.get("stock_token_refs") if isinstance(payload.get("stock_token_refs"), list) else []
    coin_report_html = render_coin_reports(coin_reports, sources) if coin_reports else render_details(details)
    matrix_html = ""
    if candidates:
        matrix_html = """
  <section id="candidates">
    <h2>摘要矩阵</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>标的</th><th>行业/赛道</th><th>细分模块</th><th>同风险簇</th><th>方向</th><th>消息事件</th><th>发布时间</th><th>事件/生效时间</th><th>检索时间</th><th>距当前多久</th><th>时效性</th><th>行情结构</th><th>状态</th><th>主要风险</th></tr></thead>
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
        <thead><tr><th>标的</th><th>底层资产</th><th>底层市场</th><th>行业</th><th>细分模块</th><th>核心业务</th><th>同风险簇</th><th>Binance 合约类型</th><th>Underlying Type</th><th>上线/生效时间</th><th>关键规则</th></tr></thead>
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
""" % render_position_followups(position_followups, sources)
    research_audit_html = ""
    if research_audit:
        analyzed_count = screening_counts.get("analyzed_survivors", screening_counts.get("researched_survivors"))
        reportable_count = screening_counts.get("reported_risk_eligible")
        if reportable_count is None:
            reportable_count = sum(
                1
                for item in coin_reports
                if normalize_chase_risk(
                    (item.get("verdict") if isinstance(item.get("verdict"), dict) else {}).get("chase_risk")
                    or item.get("chase_risk")
                )
                in {"低", "中低", "中", "中高"}
            )
        audit_columns = [
            "symbol",
            "market_type",
            "contract_type",
            "quote_volume_24h_usdt",
            "checked_sources",
            "queries",
            "retrieved_at",
            "latest_event",
            "outcome",
            "status",
            "chase_risk",
            "news_conclusion",
            "market_structure_summary",
            "analysis_summary",
            "reason",
        ]
        research_audit_html = """
  <section id="research-audit">
    <h2>逐项研究审计</h2>
    <p class="muted">24h 成交额达到 1000 万 USDT 的标的 %(survivors)s 个；已逐项核验 %(researched)s 个；已逐项分析 %(analyzed)s 个；写入报告的中高及以下风险标的 %(reportable)s 个；逐币深度章节 %(deep)s 个。渠道路由不计作访问证据。</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>标的</th><th>市场</th><th>合约类型</th><th>24h 成交额</th><th>实际检查渠道</th><th>查询词</th><th>检索时间</th><th>最新事件/未发现</th><th>结果</th><th>状态</th><th>追进去风险</th><th>消息结论</th><th>结构结论</th><th>逐币分析摘要</th><th>原因</th></tr></thead>
        <tbody>%(rows)s</tbody>
      </table>
    </div>
  </section>
""" % {
            "survivors": safe_text(screening_counts.get("post_filter_survivors")),
            "researched": safe_text(screening_counts.get("researched_survivors")),
            "analyzed": safe_text(analyzed_count),
            "reportable": safe_text(reportable_count),
            "deep": safe_text(screening_counts.get("deep_analysis", len(coin_reports))),
            "rows": rows(research_audit, audit_columns),
        }
    risk_overview_html = render_risk_landing_overview(coin_reports, position_followups, candidates)
    navigation_html = render_navigation(
        coin_reports,
        position_followups,
        bool(market_hotspots),
        bool(research_audit),
        bool(stock_token_refs),
        bool(candidates),
    )
    return """<!doctype html>
<!-- report-template: %s -->
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>消息面选币分析报告</title>
  <style>
    :root { color-scheme: light; --bg:#f6f7fb; --card:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --accent:#2563eb; }
    html { scroll-behavior:smooth; scroll-padding-top:18px; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }
    .report-shell { max-width:1480px; margin:0 auto; display:grid; grid-template-columns:240px minmax(0,1180px); gap:24px; padding:28px; }
    main { min-width:0; }
    .report-nav { position:sticky; top:20px; align-self:start; max-height:calc(100vh - 40px); overflow:auto; background:#111827; color:#fff; border-radius:8px; padding:14px 10px; }
    .report-nav strong { display:block; padding:4px 8px 10px; font-size:14px; }
    .report-nav a { display:block; color:#d1d5db; padding:7px 8px; border-left:2px solid transparent; font-size:13px; line-height:1.35; }
    .report-nav a:hover { color:#fff; background:#1f2937; border-left-color:#60a5fa; text-decoration:none; }
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
    .risk-overview { border:2px solid #dc2626; background:#fff; }
    .risk-lead { margin:0 0 12px; color:#991b1b; font-weight:700; }
    .risk-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:10px; }
    .risk-card { display:block; border:1px solid var(--line); border-left:6px solid #64748b; border-radius:8px; padding:12px; color:var(--ink); background:#fff; }
    .risk-card:hover { text-decoration:none; box-shadow:0 6px 18px rgba(15,23,42,.1); }
    .risk-card.risk-high { border-left-color:#dc2626; background:#fef2f2; }
    .risk-card.risk-medium { border-left-color:#d97706; background:#fffbeb; }
    .risk-card.risk-low { border-left-color:#15803d; background:#f0fdf4; }
    .risk-kicker { display:block; font-size:12px; font-weight:800; color:#991b1b; margin-bottom:5px; }
    .risk-card strong { font-size:18px; }
    .risk-card p { margin:7px 0 0; line-height:1.5; font-size:13px; }
    .hotspot-notice { border-left:4px solid #2563eb; background:#eff6ff; padding:10px 12px; line-height:1.6; }
    .hotspot-overview { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin:12px 0; }
    .hotspot-overview div { border:1px solid #dbeafe; background:#f8fafc; border-radius:8px; padding:12px; }
    .hotspot-overview span { display:block; color:#475569; font-size:12px; font-weight:700; margin-bottom:4px; }
    .hotspot-overview strong { display:block; font-size:14px; line-height:1.5; }
    .hotspot-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:10px; }
    .hotspot-card { border:1px solid #cbd5e1; border-radius:8px; padding:12px; background:#fff; }
    .hotspot-heading { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; }
    .hotspot-heading span { color:#b45309; font-size:12px; font-weight:800; white-space:nowrap; }
    .hotspot-card p { margin:8px 0 0; font-size:13px; line-height:1.55; }
    .asset-profile-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin:12px 0; }
    .asset-profile-grid div { background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:12px; }
    .asset-profile-grid span, .asset-background span { display:block; color:#166534; font-size:12px; font-weight:700; margin-bottom:4px; }
    .asset-profile-grid strong { display:block; color:#111827; font-size:14px; line-height:1.5; }
    .asset-background { background:#f8fafc; border-left:3px solid #22c55e; padding:10px 12px; margin:0 0 14px; }
    .asset-background p { margin:0; line-height:1.7; }
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
    .evidence-block { border:1px solid #bfdbfe; background:#eff6ff; border-radius:8px; padding:12px; }
    .evidence-card { background:#fff; border:1px solid #dbeafe; border-radius:8px; padding:10px; margin-top:8px; }
    .evidence-card h5 { margin:0 0 8px; font-size:14px; }
    .evidence-meta { display:flex; flex-wrap:wrap; gap:6px 12px; color:#475569; font-size:12px; }
    .evidence-warning { border:2px solid #dc2626; background:#fef2f2; color:#7f1d1d; border-radius:8px; padding:12px; margin:12px 0; }
    .evidence-warning p { margin:5px 0 0; line-height:1.6; }
    .pill { display:inline-block; border-radius:999px; background:#eff6ff; color:#1d4ed8; padding:4px 10px; font-size:12px; font-weight:700; }
    table { width:100%%; border-collapse:collapse; font-size:13px; }
    th,td { border-bottom:1px solid var(--line); padding:9px 8px; text-align:left; vertical-align:top; }
    th { background:#f9fafb; color:#374151; position:sticky; top:0; }
    .table-wrap { overflow-x:auto; }
    .muted { color:var(--muted); }
    a { color:var(--accent); text-decoration:none; }
    a:hover { text-decoration:underline; }
    ul { margin:8px 0 0 20px; padding:0; }
    @media (max-width: 900px) {
      .report-shell { display:block; padding:14px; }
      .report-nav { position:relative; top:auto; max-height:none; margin-bottom:14px; display:flex; gap:4px; overflow-x:auto; white-space:nowrap; }
      .report-nav strong { position:sticky; left:0; background:#111827; z-index:1; }
      .report-nav a { border-left:0; border-bottom:2px solid transparent; }
      section, .coin-report { border-radius:8px; padding:14px; }
    }
  </style>
</head>
<body>
<div class="report-shell">
%s
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
  %s
  %s
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
</div>
</body>
</html>
""" % (
        safe_text(REPORT_TEMPLATE_VERSION),
        navigation_html,
        safe_text(meta.get("research_time")),
        safe_text(meta.get("news_cutoff")),
        safe_text(meta.get("market_data_time")),
        safe_text(meta.get("timeliness_policy")),
        list_items(summary),
        market_hotspots_html,
        risk_overview_html,
        research_audit_html,
        position_followup_html,
        coin_report_html,
        stock_token_html,
        matrix_html,
        source_rows(sources, source_columns),
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
