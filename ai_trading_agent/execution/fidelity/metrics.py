"""
ai_trading_agent.execution.fidelity.metrics
==========================================
Cálculo de distribuciones de Slippage, Latencia y Spreads para Paper Trading.
"""

from typing import List, Dict, Any, Optional
import numpy as np


class ExecutionMetricsAnalyzer:
    """Calcula estadísticas descriptivas y distribuciones de microestructura."""

    @staticmethod
    def calculate_slippage_distribution(slippage_bps_list: List[float]) -> Dict[str, Any]:
        if not slippage_bps_list:
            return {
                "count": 0,
                "mean_bps": 0.0,
                "median_bps": 0.0,
                "p75_bps": 0.0,
                "p90_bps": 0.0,
                "p95_bps": 0.0,
                "worst_bps": 0.0,
                "favorable_count": 0,
                "adverse_count": 0
            }

        arr = np.array(slippage_bps_list)
        return {
            "count": len(slippage_bps_list),
            "mean_bps": round(float(np.mean(arr)), 2),
            "median_bps": round(float(np.median(arr)), 2),
            "p75_bps": round(float(np.percentile(arr, 75)), 2),
            "p90_bps": round(float(np.percentile(arr, 90)), 2),
            "p95_bps": round(float(np.percentile(arr, 95)), 2),
            "worst_bps": round(float(np.max(arr)), 2),
            "favorable_count": int(np.sum(arr < 0)),
            "adverse_count": int(np.sum(arr > 0))
        }

    @staticmethod
    def calculate_latency_distribution(latency_ms_list: List[float]) -> Dict[str, Any]:
        if not latency_ms_list:
            return {
                "count": 0,
                "mean_ms": 0.0,
                "median_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "max_ms": 0.0
            }

        arr = np.array(latency_ms_list)
        return {
            "count": len(latency_ms_list),
            "mean_ms": round(float(np.mean(arr)), 2),
            "median_ms": round(float(np.median(arr)), 2),
            "p90_ms": round(float(np.percentile(arr, 90)), 2),
            "p95_ms": round(float(np.percentile(arr, 95)), 2),
            "max_ms": round(float(np.max(arr)), 2)
        }

    @staticmethod
    def compare_performance_cohorts(
        backtest_metrics: Dict[str, Any],
        oos_metrics: Dict[str, Any],
        paper_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compara degradación entre Backtest, OOS y Paper Trading."""
        bt_pf = float(backtest_metrics.get("profit_factor", 1.0))
        oos_pf = float(oos_metrics.get("profit_factor", 1.0))
        paper_pf = float(paper_metrics.get("profit_factor", 1.0))

        degradation_vs_bt_pct = round(((bt_pf - paper_pf) / max(0.01, bt_pf)) * 100.0, 2)
        degradation_vs_oos_pct = round(((oos_pf - paper_pf) / max(0.01, oos_pf)) * 100.0, 2)

        # Clasificación de degradación
        if degradation_vs_oos_pct <= 5.0:
            classification = "NORMAL"
        elif degradation_vs_oos_pct <= 15.0:
            classification = "WATCH"
        elif degradation_vs_oos_pct <= 30.0:
            classification = "MATERIAL"
        else:
            classification = "SEVERE"

        return {
            "backtest_profit_factor": bt_pf,
            "oos_profit_factor": oos_pf,
            "paper_profit_factor": paper_pf,
            "degradation_vs_backtest_pct": degradation_vs_bt_pct,
            "degradation_vs_oos_pct": degradation_vs_oos_pct,
            "degradation_classification": classification
        }
