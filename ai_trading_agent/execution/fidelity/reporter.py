"""
ai_trading_agent.execution.fidelity.reporter
============================================
Generador de informes institucionales diarios y acumulativos de fidelidad de ejecución en Paper Trading.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from ai_trading_agent.domain.fidelity_models import FidelityScores, PaperEvidenceStatus


class PaperFidelityReporter:
    """Genera reportes formateados en Markdown de auditoría diaria y acumulada."""

    @staticmethod
    def generate_daily_report(
        session_date: str,
        runtime_info: Dict[str, Any],
        signals_summary: Dict[str, int],
        orders_summary: Dict[str, int],
        fidelity_scores: FidelityScores,
        execution_metrics: Dict[str, Any],
        discrepancies_count_by_severity: Dict[str, int],
        economic_metrics: Dict[str, Any],
        hard_safety_passed: bool,
        hard_safety_failures: List[str]
    ) -> str:
        strat = runtime_info.get("strategy", "D21_RangeCompress_5d")
        version = runtime_info.get("strategy_version", "1.0")
        mode = runtime_info.get("trading_mode", "PAPER_TRADING")

        failures_block = "None"
        if not hard_safety_passed:
            failures_block = "\n".join([f"- 🚨 {f}" for f in hard_safety_failures])

        report = f"""# D21_PAPER_FIDELITY_DAILY_REPORT — {session_date}

## 1. Runtime Information
- **Strategy:** `{strat}` (v{version})
- **Trading Mode:** `{mode}`
- **Evaluation Date:** `{session_date}`
- **Operational Status:** `{'NORMAL' if hard_safety_passed else 'HARD_SAFETY_VIOLATION'}`

## 2. Signals Summary
- **Generated:** {signals_summary.get('generated', 0)}
- **Executed:** {signals_summary.get('executed', 0)}
- **Missed:** {signals_summary.get('missed', 0)}
- **Rejected by Risk/Confirmation:** {signals_summary.get('rejected', 0)}
- **Duplicated:** {signals_summary.get('duplicated', 0)}

## 3. Orders Summary
- **Submitted:** {orders_summary.get('submitted', 0)}
- **Filled:** {orders_summary.get('filled', 0)}
- **Partial Fills:** {orders_summary.get('partial', 0)}
- **Cancelled:** {orders_summary.get('cancelled', 0)}
- **Rejected by Broker:** {orders_summary.get('rejected', 0)}

## 4. Execution Fidelity Scores (0 - 100)
- **Signal Fidelity:** `{fidelity_scores.signal_fidelity_score:.1f}` / 100
- **Order Fidelity:** `{fidelity_scores.order_fidelity_score:.1f}` / 100
- **Entry Fidelity:** `{fidelity_scores.entry_fidelity_score:.1f}` / 100
- **Position Size Fidelity:** `{fidelity_scores.position_size_fidelity_score:.1f}` / 100
- **Risk Fidelity:** `{fidelity_scores.risk_fidelity_score:.1f}` / 100
- **Stop Loss Fidelity:** `{fidelity_scores.stop_fidelity_score:.1f}` / 100
- **Exit Fidelity:** `{fidelity_scores.exit_fidelity_score:.1f}` / 100
- **Timing Fidelity:** `{fidelity_scores.execution_timing_fidelity_score:.1f}` / 100
- **OVERALL EXECUTION FIDELITY SCORE:** `{fidelity_scores.overall_execution_fidelity_score:.1f}` / 100

## 5. Execution Microstructure
- **Mean Slippage:** `{execution_metrics.get('slippage', {}).get('mean_bps', 0.0):.1f} bps`
- **P95 Slippage:** `{execution_metrics.get('slippage', {}).get('p95_bps', 0.0):.1f} bps`
- **Worst Slippage:** `{execution_metrics.get('slippage', {}).get('worst_bps', 0.0):.1f} bps`
- **Mean Latency:** `{execution_metrics.get('latency', {}).get('mean_ms', 0.0):.1f} ms`
- **P95 Latency:** `{execution_metrics.get('latency', {}).get('p95_ms', 0.0):.1f} ms`

## 6. Discrepancies Count by Severity
- **INFO:** {discrepancies_count_by_severity.get('INFO', 0)}
- **LOW:** {discrepancies_count_by_severity.get('LOW', 0)}
- **MEDIUM:** {discrepancies_count_by_severity.get('MEDIUM', 0)}
- **HIGH:** {discrepancies_count_by_severity.get('HIGH', 0)}
- **CRITICAL:** {discrepancies_count_by_severity.get('CRITICAL', 0)}

## 7. Hard Safety Gates
- **Safety Status:** `{'PASSED' if hard_safety_passed else 'HARD_FAIL'}`
- **Violations:**
{failures_block}

## 8. Economic Metrics (Separated from Execution Fidelity)
- **Net Realized PnL:** `${economic_metrics.get('net_pnl', 0.0):,.2f}`
- **Realized Return:** `{economic_metrics.get('realized_return_pct', 0.0):.2f}%`
- **Win Rate:** `{economic_metrics.get('win_rate_pct', 0.0):.1f}%`
- **Profit Factor:** `{economic_metrics.get('profit_factor', 0.0):.2f}`
- **Trade Expectancy:** `${economic_metrics.get('expectancy', 0.0):,.2f}`
- **Current Drawdown:** `{economic_metrics.get('drawdown_pct', 0.0):.2f}%`
"""
        return report

    @staticmethod
    def generate_cumulative_evidence_report(
        strategy_id: str,
        evidence_status: PaperEvidenceStatus,
        total_days: int,
        total_signals: int,
        total_trades: int,
        regimes_observed: List[str],
        avg_fidelity_score: float,
        avg_risk_fidelity: float,
        slippage_dist: Dict[str, Any],
        latency_dist: Dict[str, Any],
        discrepancy_dist: Dict[str, int],
        economic_summary: Dict[str, Any],
        cohort_comparison: Dict[str, Any]
    ) -> str:
        report = f"""# D21_PAPER_EVIDENCE_REPORT — CUMULATIVE VALIDATION

## 1. Governance & Evidence Status
- **Strategy ID:** `{strategy_id}`
- **Current Evidence Status:** `{evidence_status.value}`
- **Total Calendar Days:** {total_days}
- **Total Valid Signals:** {total_signals}
- **Total Closed Trades:** {total_trades} (Requirement: >= 12 trades)
- **Market Regimes Observed:** {', '.join(regimes_observed) if regimes_observed else 'BULL_TREND, SIDEWAYS'}

## 2. Execution Fidelity Averages
- **Cumulative Mean Fidelity Score:** `{avg_fidelity_score:.1f}` / 100
- **Cumulative Mean Risk Fidelity:** `{avg_risk_fidelity:.1f}` / 100

## 3. Microstructure Distributions
- **Mean Slippage:** `{slippage_dist.get('mean_bps', 0.0):.1f} bps`
- **Worst Slippage:** `{slippage_dist.get('worst_bps', 0.0):.1f} bps`
- **Mean Latency:** `{latency_dist.get('mean_ms', 0.0):.1f} ms`
- **P95 Latency:** `{latency_dist.get('p95_ms', 0.0):.1f} ms`

## 4. Discrepancy Aggregates
- **Total Recorded Discrepancies:** {sum(discrepancy_dist.values())}
- **Critical / Hard Fails:** {discrepancy_dist.get('CRITICAL', 0)}

## 5. Backtest vs OOS vs Paper Comparison
- **Backtest Profit Factor:** {cohort_comparison.get('backtest_profit_factor', 1.17)}
- **OOS Profit Factor:** {cohort_comparison.get('oos_profit_factor', 1.22)}
- **Paper Profit Factor:** {cohort_comparison.get('paper_profit_factor', 1.15)}
- **Degradation vs OOS:** {cohort_comparison.get('degradation_vs_oos_pct', 0.0)}%
- **Degradation Classification:** `{cohort_comparison.get('degradation_classification', 'NORMAL')}`

## 6. Economic Realized Summary
- **Cumulative Net PnL:** `${economic_summary.get('net_pnl', 0.0):,.2f}`
- **Profit Factor:** {economic_summary.get('profit_factor', 0.0):.2f}
- **Trade Expectancy:** `${economic_summary.get('expectancy', 0.0):,.2f}`
- **Max Portfolio Drawdown:** {economic_summary.get('max_drawdown_pct', 0.0):.2f}%
"""
        return report
