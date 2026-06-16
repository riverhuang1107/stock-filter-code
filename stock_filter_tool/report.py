from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from pathlib import Path

from .models import StockCandidate


def write_reports(candidates: list[StockCandidate], output: Path | None, report_dir: Path) -> tuple[Path, Path, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    html_path = output if output and output.suffix.lower() == ".html" else report_dir / "latest.html"
    md_path = output if output and output.suffix.lower() == ".md" else report_dir / "latest.md"
    html = render_html(candidates)
    markdown = render_markdown(candidates)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return html_path, md_path, html


def render_html(candidates: list[StockCandidate], inline_images: bool = True) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for idx, candidate in enumerate(candidates, 1):
        image_html = ""
        if candidate.chart_path:
            src = _image_src(candidate.chart_path) if inline_images else candidate.chart_path.as_posix()
            image_html = f'<img src="{src}" alt="{escape(candidate.meta.code)} kline" class="chart">'
        rows.append(
            f"""
            <section class="stock">
              <h2>#{idx} {escape(candidate.meta.code)} {escape(candidate.meta.name)} - {candidate.score:.2f}</h2>
              <p>{escape(candidate.reason)}</p>
              <table>
                <tr><th>信号日</th><td>{escape(candidate.signal.signal_date)}</td><th>实体倍数</th><td>{candidate.signal.body_ratio:.2f}</td></tr>
                <tr><th>实体涨幅</th><td>{candidate.signal.body_pct:.2f}%</td><th>量比</th><td>{candidate.signal.volume_ratio:.2f}</td></tr>
                <tr><th>ROE</th><td>{_fmt(candidate.financials.roe)}</td><th>净利增长</th><td>{_fmt(candidate.financials.net_profit_growth)}</td></tr>
                <tr><th>营收增长</th><td>{_fmt(candidate.financials.revenue_growth)}</td><th>评分</th><td>{candidate.score:.2f}</td></tr>
              </table>
              {image_html}
            </section>
            """
        )
    empty = "<p>未筛选到符合条件的股票。</p>" if not rows else ""
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>A股大阳包小阴筛选报告</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #222; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #666; margin-bottom: 20px; }}
    .stock {{ border-top: 1px solid #ddd; padding: 18px 0; }}
    table {{ border-collapse: collapse; margin: 10px 0 14px; width: 100%; max-width: 900px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; }}
    th {{ background: #f6f8fa; width: 110px; }}
    .chart {{ max-width: 900px; width: 100%; height: auto; border: 1px solid #ddd; }}
  </style>
</head>
<body>
  <h1>A股大阳包小阴筛选报告</h1>
  <div class="meta">生成时间：{generated_at}；排名数量：{len(candidates)}</div>
  {empty}
  {''.join(rows)}
</body>
</html>
"""


def render_markdown(candidates: list[StockCandidate]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# A股大阳包小阴筛选报告",
        "",
        f"生成时间：{generated_at}",
        "",
    ]
    if not candidates:
        lines.append("未筛选到符合条件的股票。")
        return "\n".join(lines)
    for idx, candidate in enumerate(candidates, 1):
        lines.extend(
            [
                f"## #{idx} {candidate.meta.code} {candidate.meta.name} - {candidate.score:.2f}",
                "",
                candidate.reason,
                "",
                f"- 信号日：{candidate.signal.signal_date}",
                f"- 实体倍数：{candidate.signal.body_ratio:.2f}",
                f"- 实体涨幅：{candidate.signal.body_pct:.2f}%",
                f"- 量比：{candidate.signal.volume_ratio:.2f}",
                f"- ROE：{_fmt(candidate.financials.roe)}",
                f"- 净利增长：{_fmt(candidate.financials.net_profit_growth)}",
                f"- 营收增长：{_fmt(candidate.financials.revenue_growth)}",
            ]
        )
        if candidate.chart_path:
            lines.extend(["", f"![{candidate.meta.code} K线图]({candidate.chart_path.as_posix()})"])
        lines.append("")
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}%"


def _image_src(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"
