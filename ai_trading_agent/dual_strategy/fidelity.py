"""
ai_trading_agent.dual_strategy.fidelity
=======================================
Motor de Fidelidad y Detección de Discrepancias (Fidelity & Discrepancy Engine).
Compara la ejecución teórica simulada frente a las ejecuciones observadas en Paper Trading.
Cuantifica deslizamiento real, retrasos de latencia y derivas de ejecución.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from ai_trading_agent.dual_strategy.models import TradeFillRecord


class FidelityEngine:
    """Motor de auditoría de fidelidad de ejecución entre Simulación y Paper."""

    def __init__(self, max_allowed_slippage_discrepancy_bps: float = 10.0):
        self.max_allowed_slippage_discrepancy_bps = max_allowed_slippage_discrepancy_bps
        self._discrepancy_records: List[Dict[str, Any]] = []

    def evaluate_fill_fidelity(
        self,
        simulated_fill: TradeFillRecord,
        observed_paper_fill_price: float,
        observed_paper_fill_time: datetime
    ) -> Dict[str, Any]:
        """
        Evalúa la discrepancia entre el precio simulado y el fill real del paper broker.
        """
        price_diff = abs(observed_paper_fill_price - simulated_fill.fill_price)
        diff_bps = (price_diff / simulated_fill.fill_price) * 10000.0

        time_delta_seconds = abs((observed_paper_fill_time - simulated_fill.entry_time).total_seconds())

        is_anomalous = diff_bps > self.max_allowed_slippage_discrepancy_bps

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "trade_id": simulated_fill.trade_id,
            "strategy_id": simulated_fill.strategy_id,
            "symbol": simulated_fill.symbol,
            "simulated_price": simulated_fill.fill_price,
            "observed_price": observed_paper_fill_price,
            "diff_dollars": round(price_diff, 4),
            "diff_bps": round(diff_bps, 2),
            "latency_seconds": round(time_delta_seconds, 2),
            "status": "ANOMALY" if is_anomalous else "CONFIRMED_FIDELITY"
        }
        self._discrepancy_records.append(record)
        return record

    def compute_summary_fidelity_score(self) -> float:
        """Score de Fidelidad (0 a 100%). Penaliza discrepancias altas en bps."""
        if not self._discrepancy_records:
            return 100.0
        anomalies = sum(1 for r in self._discrepancy_records if r["status"] == "ANOMALY")
        penalty = (anomalies / len(self._discrepancy_records)) * 40.0
        avg_bps = np.mean([r["diff_bps"] for r in self._discrepancy_records])
        bps_penalty = min(60.0, avg_bps * 2.0)
        return max(0.0, round(100.0 - penalty - bps_penalty, 2))
