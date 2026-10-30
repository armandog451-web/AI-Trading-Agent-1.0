"""
ai_trading_agent.execution.fidelity.scoring
===========================================
Calculador de métricas de fidelidad determinísticas y auditables (0 a 100).
Asegura que un buen score nunca compense una violación crítica (Hard Safety Gate).
"""

from typing import List, Dict, Any
from ai_trading_agent.domain.fidelity_models import (
    FidelityScores,
    ExecutionDiscrepancy,
    DiscrepancySeverity,
    DiscrepancyCategory
)


class FidelityScorer:
    """Calcula puntajes de fidelidad segmentados e independientes del rendimiento económico."""

    @staticmethod
    def calculate(discrepancies: List[ExecutionDiscrepancy]) -> FidelityScores:
        scores = FidelityScores()

        # 1. Comprobación de Hard Fails inmediatos
        has_critical = any(d.severity == DiscrepancySeverity.CRITICAL or d.hard_fail for d in discrepancies)
        if has_critical:
            scores.hard_fail_active = True

        # Penalizaciones por severidad:
        # INFO: 0 pts, LOW: 5 pts, MEDIUM: 15 pts, HIGH: 35 pts, CRITICAL: 100 pts
        def get_penalty(d: ExecutionDiscrepancy) -> float:
            if d.severity == DiscrepancySeverity.CRITICAL or d.hard_fail:
                return 100.0
            elif d.severity == DiscrepancySeverity.HIGH:
                return 35.0
            elif d.severity == DiscrepancySeverity.MEDIUM:
                return 15.0
            elif d.severity == DiscrepancySeverity.LOW:
                return 5.0
            return 0.0

        # Segmentación por componentes
        signal_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.SIGNAL_MISMATCH,
            DiscrepancyCategory.MISSED_SIGNAL,
            DiscrepancyCategory.DUPLICATE_SIGNAL
        )]
        order_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.ORDER_NOT_CREATED,
            DiscrepancyCategory.DUPLICATE_ORDER,
            DiscrepancyCategory.BROKER_REJECTION,
            DiscrepancyCategory.BROKER_CANCELLATION
        )]
        entry_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.ENTRY_PRICE_DEVIATION,
            DiscrepancyCategory.SLIPPAGE_DEVIATION,
            DiscrepancyCategory.SPREAD_DEVIATION
        )]
        size_penalties = [get_penalty(d) for d in discrepancies if d.category == DiscrepancyCategory.POSITION_SIZE_DEVIATION]
        risk_penalties = [get_penalty(d) for d in discrepancies if d.category == DiscrepancyCategory.RISK_DEVIATION]
        stop_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.STOP_MISMATCH,
            DiscrepancyCategory.TAKE_PROFIT_MISMATCH
        )]
        exit_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.EXIT_RULE_MISMATCH,
            DiscrepancyCategory.EXIT_PRICE_DEVIATION,
            DiscrepancyCategory.EXIT_TIME_DEVIATION
        )]
        timing_penalties = [get_penalty(d) for d in discrepancies if d.category in (
            DiscrepancyCategory.ENTRY_TIME_DEVIATION,
            DiscrepancyCategory.LATENCY_DEVIATION
        )]

        scores.signal_fidelity_score = max(0.0, round(100.0 - sum(signal_penalties), 2))
        scores.order_fidelity_score = max(0.0, round(100.0 - sum(order_penalties), 2))
        scores.entry_fidelity_score = max(0.0, round(100.0 - sum(entry_penalties), 2))
        scores.position_size_fidelity_score = max(0.0, round(100.0 - sum(size_penalties), 2))
        scores.risk_fidelity_score = max(0.0, round(100.0 - sum(risk_penalties), 2))
        scores.stop_fidelity_score = max(0.0, round(100.0 - sum(stop_penalties), 2))
        scores.exit_fidelity_score = max(0.0, round(100.0 - sum(exit_penalties), 2))
        scores.execution_timing_fidelity_score = max(0.0, round(100.0 - sum(timing_penalties), 2))

        # Overall Fidelity: promedio ponderado, salvo que exista HARD FAIL
        if scores.hard_fail_active:
            scores.overall_execution_fidelity_score = 0.0
        else:
            weights = {
                "signal": 0.15,
                "order": 0.15,
                "entry": 0.10,
                "size": 0.15,
                "risk": 0.20,
                "stop": 0.15,
                "exit": 0.10
            }
            weighted_sum = (
                scores.signal_fidelity_score * weights["signal"] +
                scores.order_fidelity_score * weights["order"] +
                scores.entry_fidelity_score * weights["entry"] +
                scores.position_size_fidelity_score * weights["size"] +
                scores.risk_fidelity_score * weights["risk"] +
                scores.stop_fidelity_score * weights["stop"] +
                scores.exit_fidelity_score * weights["exit"]
            )
            scores.overall_execution_fidelity_score = round(max(0.0, min(100.0, weighted_sum)), 2)

        return scores
