"""
ai_trading_agent.execution.fidelity.engine
=========================================
Motor principal institucional PaperFidelityEngine.
Observa, registra la intención, compara contra la ejecución real, detecta anomalías
y evalúa las puertas de seguridad en Paper Trading sin modificar las estrategias.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import hashlib

from ai_trading_agent.domain.fidelity_models import (
    ExpectedTradeExecution,
    ActualTradeExecution,
    ExecutionDiscrepancy,
    FidelityScores,
    DiscrepancySeverity,
    DiscrepancyCategory,
    PaperEvidenceStatus,
    PaperValidationLifecycleStatus
)
from ai_trading_agent.execution.fidelity.discrepancy import DiscrepancyDetector
from ai_trading_agent.execution.fidelity.scoring import FidelityScorer
from ai_trading_agent.execution.fidelity.metrics import ExecutionMetricsAnalyzer
from ai_trading_agent.execution.fidelity.gates import HardSafetyGates
from ai_trading_agent.execution.fidelity.journal import PaperFidelityJournal
from ai_trading_agent.execution.fidelity.reporter import PaperFidelityReporter


class PaperFidelityEngine:
    """Motor observacional y de auditoría de fidelidad en Paper Trading."""

    def __init__(
        self,
        authorized_strategy_id: str = "D21_RangeCompress_5d",
        journal: Optional[PaperFidelityJournal] = None
    ):
        self.authorized_strategy_id = authorized_strategy_id
        self.journal = journal or PaperFidelityJournal()
        self.detector = DiscrepancyDetector(authorized_strategy_id=authorized_strategy_id)
        self.scorer = FidelityScorer()
        self.metrics_analyzer = ExecutionMetricsAnalyzer()
        self.gates = HardSafetyGates()
        self.reporter = PaperFidelityReporter()

        self._expected_executions: Dict[str, ExpectedTradeExecution] = {}
        self._actual_executions: Dict[str, ActualTradeExecution] = {}
        self._discrepancies: Dict[str, List[ExecutionDiscrepancy]] = {}
        self._processed_orders: set = set()
        self._evidence_status = PaperEvidenceStatus.INSUFFICIENT
        self._lifecycle_status = PaperValidationLifecycleStatus.PAPER_COLLECTING_EVIDENCE

    def capture_expected_execution(
        self,
        strategy_id: str,
        signal_id: str,
        symbol: str,
        side: str,
        signal_price: float,
        expected_entry_price: float,
        expected_position_size: int,
        expected_risk_amount: float,
        expected_risk_pct: float,
        expected_stop_price: float,
        expected_take_profit_price: Optional[float] = None,
        strategy_parameters: Optional[Dict[str, Any]] = None,
        market_regime: str = "BULL_TREND",
        market_session: str = "REGULAR"
    ) -> ExpectedTradeExecution:
        """
        Captura el estado de intención ANTES de enviar la orden al broker.
        Inmutable y determinista.
        """
        params = strategy_parameters or {}
        spec_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]

        expected = ExpectedTradeExecution(
            strategy_id=strategy_id,
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            signal_timestamp=datetime.utcnow(),
            signal_price=signal_price,
            expected_entry_price=expected_entry_price,
            expected_position_size=expected_position_size,
            expected_notional=expected_entry_price * expected_position_size,
            expected_risk_amount=expected_risk_amount,
            expected_risk_pct=expected_risk_pct,
            expected_stop_price=expected_stop_price,
            expected_take_profit_price=expected_take_profit_price,
            expected_exit_rules={
                "max_holding_days": 5,
                "allowed_exit_reasons": ["TIME_EXIT", "STOP_LOSS"]
            },
            market_regime=market_regime,
            market_session=market_session,
            specification_hash=spec_hash,
            strategy_config_hash=spec_hash
        )

        self._expected_executions[signal_id] = expected
        return expected

    def capture_actual_execution(
        self,
        signal_id: str,
        order_id: str,
        requested_price: float,
        requested_quantity: int,
        actual_fill_price: Optional[float] = None,
        actual_quantity: int = 0,
        actual_stop_price: Optional[float] = None,
        actual_take_profit_price: Optional[float] = None,
        order_status: str = "FILLED",
        rejection_reason: Optional[str] = None,
        exit_timestamp: Optional[datetime] = None,
        actual_exit_price: Optional[float] = None,
        actual_exit_reason: Optional[str] = None,
        realized_pnl: float = 0.0,
        order_created_at: Optional[datetime] = None,
        fill_timestamp: Optional[datetime] = None
    ) -> ActualTradeExecution:
        """Captura la ejecución observada en el Paper Broker."""
        now = datetime.utcnow()
        created_at = order_created_at or now
        fill_time = fill_timestamp or now

        # Detección de órdenes duplicadas por señal
        if order_id in self._processed_orders:
            # Orden duplicada detectada
            dup_disc = ExecutionDiscrepancy(
                discrepancy_id=f"dup_{order_id}",
                strategy_id=self.authorized_strategy_id,
                signal_id=signal_id,
                order_id=order_id,
                category=DiscrepancyCategory.DUPLICATE_ORDER,
                severity=DiscrepancySeverity.CRITICAL,
                expected_value=1,
                actual_value=2,
                requires_review=True,
                hard_fail=True,
                resolution_note=f"Orden duplicada detectada para la misma señal {signal_id}."
            )
            self.journal.record_discrepancy(dup_disc)
            if signal_id not in self._discrepancies:
                self._discrepancies[signal_id] = []
            self._discrepancies[signal_id].append(dup_disc)

        self._processed_orders.add(order_id)

        slippage = 0.0
        if actual_fill_price is not None and requested_price > 0:
            slippage = round(actual_fill_price - requested_price, 4)

        actual = ActualTradeExecution(
            signal_id=signal_id,
            order_id=order_id,
            order_created_at=created_at,
            fill_timestamp=fill_time,
            requested_price=requested_price,
            actual_fill_price=actual_fill_price,
            requested_quantity=requested_quantity,
            actual_quantity=actual_quantity,
            actual_notional=(actual_fill_price or 0.0) * actual_quantity,
            actual_stop_price=actual_stop_price,
            actual_take_profit_price=actual_take_profit_price,
            actual_slippage=slippage,
            order_status=order_status,
            rejection_reason=rejection_reason,
            exit_timestamp=exit_timestamp,
            actual_exit_price=actual_exit_price,
            actual_exit_reason=actual_exit_reason,
            realized_pnl=realized_pnl
        )

        self._actual_executions[signal_id] = actual
        return actual

    def compare_execution(self, signal_id: str) -> List[ExecutionDiscrepancy]:
        """Compara la pareja Expected vs Actual para un signal_id dado."""
        expected = self._expected_executions.get(signal_id)
        if not expected:
            raise KeyError(f"ExpectedTradeExecution not found for signal_id {signal_id}")

        actual = self._actual_executions.get(signal_id)
        discrepancies = self.detector.evaluate(expected=expected, actual=actual)

        # Persistir pareja en Journal
        self.journal.record_execution_pair(expected=expected, actual=actual)

        # Persistir discrepancias detectadas y notificar de forma fail-safe
        for d in discrepancies:
            self.journal.record_discrepancy(d)
            try:
                from ai_trading_agent.notifications.telegram_notifier import telegram_observability
                telegram_observability.notify_discrepancy(d)
            except Exception:
                pass

        self._discrepancies[signal_id] = discrepancies
        return discrepancies

    def calculate_fidelity_metrics(self, signal_id: Optional[str] = None) -> FidelityScores:
        """Calcula los puntajes de fidelidad ya sea para una señal o para el acumulado."""
        if signal_id:
            disc_list = self._discrepancies.get(signal_id, [])
        else:
            disc_list = [d for sublist in self._discrepancies.values() for d in sublist]

        return self.scorer.calculate(disc_list)

    def evaluate_hard_safety(self, signal_id: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Evalúa los Hard Safety Gates garantizando que ningún score compense fallos críticos."""
        if signal_id:
            disc_list = self._discrepancies.get(signal_id, [])
        else:
            disc_list = [d for sublist in self._discrepancies.values() for d in sublist]

        return self.gates.evaluate(disc_list)

    def get_observability_status(self) -> Dict[str, Any]:
        """Retorna el estado del motor para endpoints de observabilidad/health."""
        all_disc = [d for sublist in self._discrepancies.values() for d in sublist]
        critical_count = sum(1 for d in all_disc if d.severity == DiscrepancySeverity.CRITICAL or d.hard_fail)
        scores = self.scorer.calculate(all_disc)

        from ai_trading_agent.execution.fidelity.campaign import d21_campaign_tracker
        campaign_info = d21_campaign_tracker.calculate_metrics()

        return {
            "paper_fidelity_engine": "ACTIVE",
            "strategy": self.authorized_strategy_id,
            "evidence_status": self._evidence_status.value,
            "lifecycle_status": self._lifecycle_status.value,
            "execution_fidelity_score": scores.overall_execution_fidelity_score if len(self._expected_executions) > 0 else None,
            "critical_discrepancies": critical_count,
            "live_trading": "BLOCKED",
            "paper_validation_active": True,
            "campaign_clock": {
                "original_campaign_start": campaign_info["original_campaign_start"],
                "paper_observation_gap": campaign_info["paper_observation_gap"],
                "canonical_runtime_restored": campaign_info["canonical_runtime_restored"],
                "calendar_days_since_original_start": campaign_info["calendar_days_since_original_start"],
                "verified_paper_observation_days": campaign_info["verified_paper_observation_days"],
                "target_verified_observation_days": campaign_info["target_verified_observation_days"],
                "closed_paper_trades_count": campaign_info["closed_paper_trades_count"],
                "target_closed_paper_trades": campaign_info["target_closed_paper_trades"]
            }
        }


paper_fidelity_engine = PaperFidelityEngine()
