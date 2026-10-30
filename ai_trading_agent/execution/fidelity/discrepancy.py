"""
ai_trading_agent.execution.fidelity.discrepancy
==============================================
Detector y clasificador formal de discrepancias de ejecución en Paper Trading.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ai_trading_agent.domain.fidelity_models import (
    ExpectedTradeExecution,
    ActualTradeExecution,
    ExecutionDiscrepancy,
    DiscrepancyCategory,
    DiscrepancySeverity
)


class DiscrepancyDetector:
    """Detecta y clasifica desviaciones entre la intención esperada y la ejecución real."""

    def __init__(
        self,
        entry_price_tolerance_bps: float = 15.0,
        risk_deviation_tolerance_pct: float = 5.0,
        max_allowed_position_risk: float = 2500.0,
        max_allowed_position_notional: float = 100000.0,
        authorized_strategy_id: str = "D21_RangeCompress_5d"
    ):
        self.entry_price_tolerance_bps = entry_price_tolerance_bps
        self.risk_deviation_tolerance_pct = risk_deviation_tolerance_pct
        self.max_allowed_position_risk = max_allowed_position_risk
        self.max_allowed_position_notional = max_allowed_position_notional
        self.authorized_strategy_id = authorized_strategy_id

    def evaluate(
        self,
        expected: ExpectedTradeExecution,
        actual: Optional[ActualTradeExecution]
    ) -> List[ExecutionDiscrepancy]:
        """Compara una ejecución esperada contra la real y genera lista de discrepancias."""
        discrepancies: List[ExecutionDiscrepancy] = []

        # 0. Verificación de estrategia autorizada
        if expected.strategy_id != self.authorized_strategy_id:
            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=actual.order_id if actual else None,
                category=DiscrepancyCategory.UNKNOWN_EXECUTION_ANOMALY,
                severity=DiscrepancySeverity.CRITICAL,
                expected_value=self.authorized_strategy_id,
                actual_value=expected.strategy_id,
                requires_review=True,
                hard_fail=True,
                resolution_note="Estrategia no autorizada intentó ejecutar en Paper Trading."
            ))

        # 1. Caso de señal perdida (Missed Signal) / Orden no creada
        if actual is None or actual.order_status in ("NOT_CREATED", "DROPPED"):
            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=None,
                category=DiscrepancyCategory.MISSED_SIGNAL,
                severity=DiscrepancySeverity.HIGH,
                expected_value="ORDER_CREATED",
                actual_value="NO_ORDER",
                requires_review=True,
                hard_fail=False,
                resolution_note="Señal válida producida sin orden correspondiente en broker."
            ))
            return discrepancies

        # 2. Broker Rejection o Cancellation
        if actual.order_status == "REJECTED":
            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=actual.order_id,
                category=DiscrepancyCategory.BROKER_REJECTION,
                severity=DiscrepancySeverity.HIGH,
                expected_value="FILLED",
                actual_value="REJECTED",
                requires_review=True,
                hard_fail=False,
                resolution_note=actual.rejection_reason or "Orden rechazada por el broker."
            ))
            return discrepancies

        if actual.order_status == "CANCELLED":
            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=actual.order_id,
                category=DiscrepancyCategory.BROKER_CANCELLATION,
                severity=DiscrepancySeverity.MEDIUM,
                expected_value="FILLED",
                actual_value="CANCELLED",
                requires_review=True,
                resolution_note=actual.cancellation_reason or "Orden cancelada antes del fill."
            ))
            return discrepancies

        # 3. Desviación de Precio de Entrada y Slippage
        if actual.actual_fill_price is not None and expected.expected_entry_price > 0:
            diff = actual.actual_fill_price - expected.expected_entry_price
            abs_diff = abs(diff)
            bps = (abs_diff / expected.expected_entry_price) * 10000.0

            if bps > self.entry_price_tolerance_bps:
                severity = DiscrepancySeverity.MEDIUM if bps < 50.0 else DiscrepancySeverity.HIGH
                discrepancies.append(ExecutionDiscrepancy(
                    discrepancy_id=str(uuid.uuid4()),
                    strategy_id=expected.strategy_id,
                    signal_id=expected.signal_id,
                    order_id=actual.order_id,
                    category=DiscrepancyCategory.ENTRY_PRICE_DEVIATION,
                    severity=severity,
                    expected_value=expected.expected_entry_price,
                    actual_value=actual.actual_fill_price,
                    absolute_deviation=abs_diff,
                    relative_deviation=abs_diff / expected.expected_entry_price,
                    deviation_bps=bps,
                    requires_review=bps >= 50.0,
                    resolution_note=f"Desviación de precio de entrada de {bps:.1f} bps supera tolerancia ({self.entry_price_tolerance_bps} bps)."
                ))

        # 4. Desviación de Tamaño de Posición (Position Size)
        if actual.actual_quantity != expected.expected_position_size:
            abs_qty_diff = abs(actual.actual_quantity - expected.expected_position_size)
            rel_qty_diff = abs_qty_diff / max(1, expected.expected_position_size)
            severity = DiscrepancySeverity.LOW if abs_qty_diff <= 2 else DiscrepancySeverity.HIGH
            
            # Si el tamaño supera el límite institucional, es CRITICAL
            is_critical = actual.actual_notional > self.max_allowed_position_notional
            if is_critical:
                severity = DiscrepancySeverity.CRITICAL

            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=actual.order_id,
                category=DiscrepancyCategory.POSITION_SIZE_DEVIATION,
                severity=severity,
                expected_value=expected.expected_position_size,
                actual_value=actual.actual_quantity,
                absolute_deviation=float(abs_qty_diff),
                relative_deviation=rel_qty_diff,
                requires_review=is_critical or rel_qty_diff > 0.10,
                hard_fail=is_critical,
                resolution_note=f"Cantidad ejecutada ({actual.actual_quantity}) difiere de la esperada ({expected.expected_position_size})."
            ))

        # 5. Desviación de Riesgo (Risk Fidelity)
        if actual.actual_fill_price and actual.actual_stop_price:
            actual_risk_per_share = abs(actual.actual_fill_price - actual.actual_stop_price)
            actual_risk_dollars = actual_risk_per_share * actual.actual_quantity

            if expected.expected_risk_amount > 0:
                risk_diff = abs(actual_risk_dollars - expected.expected_risk_amount)
                risk_pct_dev = (risk_diff / expected.expected_risk_amount) * 100.0

                is_risk_violation = actual_risk_dollars > self.max_allowed_position_risk
                severity = DiscrepancySeverity.CRITICAL if is_risk_violation else (
                    DiscrepancySeverity.HIGH if risk_pct_dev > self.risk_deviation_tolerance_pct else DiscrepancySeverity.LOW
                )

                if risk_pct_dev > self.risk_deviation_tolerance_pct or is_risk_violation:
                    discrepancies.append(ExecutionDiscrepancy(
                        discrepancy_id=str(uuid.uuid4()),
                        strategy_id=expected.strategy_id,
                        signal_id=expected.signal_id,
                        order_id=actual.order_id,
                        category=DiscrepancyCategory.RISK_DEVIATION,
                        severity=severity,
                        expected_value=expected.expected_risk_amount,
                        actual_value=actual_risk_dollars,
                        absolute_deviation=risk_diff,
                        relative_deviation=risk_pct_dev / 100.0,
                        requires_review=is_risk_violation or severity in (DiscrepancySeverity.HIGH, DiscrepancySeverity.CRITICAL),
                        hard_fail=is_risk_violation,
                        resolution_note=f"Riesgo real (${actual_risk_dollars:,.2f}) se desvía {risk_pct_dev:.1f}% de lo esperado (${expected.expected_risk_amount:,.2f})."
                    ))

        # 6. Stop Loss Mismatch
        if expected.expected_stop_price > 0 and (actual.actual_stop_price is None or actual.actual_stop_price <= 0):
            discrepancies.append(ExecutionDiscrepancy(
                discrepancy_id=str(uuid.uuid4()),
                strategy_id=expected.strategy_id,
                signal_id=expected.signal_id,
                order_id=actual.order_id,
                category=DiscrepancyCategory.STOP_MISMATCH,
                severity=DiscrepancySeverity.CRITICAL,
                expected_value=expected.expected_stop_price,
                actual_value=actual.actual_stop_price,
                requires_review=True,
                hard_fail=True,
                resolution_note="Stop Loss mandatorio ausente o no configurado en la ejecución real."
            ))
        elif expected.expected_stop_price > 0 and actual.actual_stop_price is not None:
            stop_diff = abs(actual.actual_stop_price - expected.expected_stop_price)
            if stop_diff > 0.05:  # Desviación mayor a 5 centavos
                discrepancies.append(ExecutionDiscrepancy(
                    discrepancy_id=str(uuid.uuid4()),
                    strategy_id=expected.strategy_id,
                    signal_id=expected.signal_id,
                    order_id=actual.order_id,
                    category=DiscrepancyCategory.STOP_MISMATCH,
                    severity=DiscrepancySeverity.HIGH,
                    expected_value=expected.expected_stop_price,
                    actual_value=actual.actual_stop_price,
                    absolute_deviation=stop_diff,
                    requires_review=True,
                    resolution_note=f"Stop Loss real (${actual.actual_stop_price:.2f}) difiere del esperado (${expected.expected_stop_price:.2f})."
                ))

        # 7. Exit Rule Mismatch (cuando la posición ya cerró)
        if actual.actual_exit_reason:
            expected_reasons = expected.expected_exit_rules.get("allowed_exit_reasons", ["TIME_EXIT", "STOP_LOSS"])
            if actual.actual_exit_reason not in expected_reasons:
                discrepancies.append(ExecutionDiscrepancy(
                    discrepancy_id=str(uuid.uuid4()),
                    strategy_id=expected.strategy_id,
                    signal_id=expected.signal_id,
                    order_id=actual.order_id,
                    category=DiscrepancyCategory.EXIT_RULE_MISMATCH,
                    severity=DiscrepancySeverity.HIGH,
                    expected_value=expected_reasons,
                    actual_value=actual.actual_exit_reason,
                    requires_review=True,
                    resolution_note=f"Razón de salida real ('{actual.actual_exit_reason}') no coincide con las reglas esperadas de D21."
                ))

        return discrepancies
