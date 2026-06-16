from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .emailer import DEFAULT_RECIPIENTS, send_report_email


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stock-filter", description="筛选 A 股大阳包小阴股票并生成报告。")
    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="运行筛选")
    run.add_argument("--top", type=int, default=10, help="输出排名数量")
    run.add_argument("--days", type=int, default=3, help="最近多少个交易日内出现信号")
    run.add_argument("--chart-days", type=int, default=5, help="K 线图展示交易日数量")
    run.add_argument("--output", type=Path, default=None, help="指定 HTML 或 Markdown 输出路径")
    run.add_argument("--report-dir", type=Path, default=Path("reports"), help="报告输出目录")
    run.add_argument("--limit", type=int, default=None, help="调试用：限制扫描股票数量")
    run.add_argument("--workers", type=int, default=24, help="并发扫描线程数")
    run.add_argument("--financial-pool", type=int, default=30, help="进入财务重排的技术候选池数量")
    run.add_argument("--scan-limit-matches", type=int, default=None, help="找到指定数量候选后停止等待剩余扫描")
    run.add_argument("--fail-on-empty", action="store_true", help="未筛选到股票时返回非零退出码，适合云端监控")
    run.add_argument("--send-email", action="store_true", help="发送邮件")
    run.add_argument("--no-email", action="store_true", help="不发送邮件")
    run.add_argument("--recipient", action="append", default=None, help="额外或自定义收件人，可重复传入")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "run":
        parser.print_help()
        return 0
    return run(args)


def run(args: argparse.Namespace) -> int:
    from .charts import create_kline_chart
    from .data import load_a_share_universe, load_daily_bars, load_financial_metrics
    from .models import FinancialMetrics
    from .ranking import score_candidate
    from .report import write_reports
    from .signals import find_bullish_engulfing_signal

    report_dir: Path = args.report_dir
    chart_dir = report_dir / "charts"
    try:
        stocks = load_a_share_universe(limit=args.limit)
    except Exception as exc:
        print(f"Unable to load stock universe: {exc}", file=sys.stderr)
        return 1

    candidates = []
    total = len(stocks)
    print(f"Loaded {total} non-ST A-share stocks.", flush=True)

    def scan_one(meta):
        bars = load_daily_bars(meta.code)
        signal = find_bullish_engulfing_signal(bars, days=args.days)
        if not signal:
            return None
        candidate = score_candidate(meta, signal, FinancialMetrics())
        return candidate, bars

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(scan_one, meta): meta for meta in stocks}
        for idx, future in enumerate(as_completed(futures), 1):
            meta = futures[future]
            try:
                result = future.result()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"[{idx}/{total}] skipped {meta.code} {meta.name}: {exc}", file=sys.stderr, flush=True)
                continue
            if result:
                candidate, bars = result
                candidate._bars = bars
                candidates.append(candidate)
                print(f"[{idx}/{total}] matched {meta.code} {meta.name}: score={candidate.score:.2f}", flush=True)
            if args.scan_limit_matches and len(candidates) >= args.scan_limit_matches:
                for pending in futures:
                    pending.cancel()
                break

    candidates.sort(key=lambda item: item.score, reverse=True)
    candidate_bars = {candidate.meta.code: getattr(candidate, "_bars", None) for candidate in candidates}
    reranked = []
    for candidate in candidates[: max(args.top, args.financial_pool)]:
        try:
            financials = load_financial_metrics(candidate.meta.code)
            refreshed = score_candidate(candidate.meta, candidate.signal, financials)
            refreshed._bars = candidate_bars.get(candidate.meta.code)
            reranked.append(refreshed)
        except Exception as exc:
            print(f"financials unavailable for {candidate.meta.code} {candidate.meta.name}: {exc}", file=sys.stderr)
            reranked.append(candidate)

    reranked.sort(key=lambda item: item.score, reverse=True)
    selected = reranked[: args.top]
    for candidate in selected:
        bars = getattr(candidate, "_bars", None)
        if bars is not None:
            candidate.chart_path = create_kline_chart(
                bars,
                candidate.meta,
                candidate.signal,
                chart_dir,
                chart_days=args.chart_days,
            )
            delattr(candidate, "_bars")

    html_path, md_path, html = write_reports(selected, args.output, report_dir)
    print(f"HTML report: {html_path}")
    print(f"Markdown report: {md_path}")
    for rank, candidate in enumerate(selected, 1):
        print(f"{rank}. {candidate.meta.code} {candidate.meta.name} {candidate.score:.2f} - {candidate.reason}")

    if args.fail_on_empty and not selected:
        print("No matching stocks found; exiting with code 2 because --fail-on-empty was set.", file=sys.stderr)
        return 2

    should_send = args.send_email and not args.no_email
    if should_send:
        recipients = args.recipient or DEFAULT_RECIPIENTS
        send_report_email(html=html, recipients=recipients, attachments=[html_path, md_path])
        print(f"Email sent to: {', '.join(recipients)}")
    else:
        print("Email sending skipped.")
    return 0
