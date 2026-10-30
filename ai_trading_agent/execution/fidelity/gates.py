"""
ai_trading_agent.execution.fidelity.gates
========================================
Puertas de seguridad absolutas (Hard Safety Gates) para Paper Trading.
Independientes de los scores numéricos.
"""

from typing import List, Tuple
from ai_trading_agent.domain.fidelity_models import ExecutionDiscrepancy, DiscrepancySeverity


class HardSafetyGates:
    """Evalúa condiciones de fallo crítico absoluto que invalidan la sesión."""

    @staticmethod
    def evaluate(
        discrepancies: List[ExecutionDiscrepancy],
        is_live_order_detected: bool = False,
        unauthorized_strategy_detected: bool = False
    ) -> Tuple[bool, List[str]]:
        failures = []

        if is_live_order_detected:
            failures.append("EMERGENCY_FAIL: Orden de broker LIVE detectada en entorno protegido.")

        if unauthorized_strategy_detected:
            failures.append("HARD_FAIL: Ejecución de estrategia no autorizada detectada (Solo D21 permitida).")

        for d in discrepancies:
            if d.hard_fail or d.severity == DiscrepancySeverity.CRITICAL:
                failures.append(f"HARD_FAIL: [{d.category.value}] {d.resolution_note}")

        is_passed = len(failures) == 0
        return is_passed, failures
