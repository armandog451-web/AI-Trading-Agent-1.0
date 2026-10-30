"""
ai_trading_agent.notifications.telegram_notifier
=================================================
Módulo centralizado de alto nivel para emisión de eventos por Telegram.
Interfaz pasiva invocada por el Trading Core, Fidelity Engine y Orquestador.
PROHIBICIÓN ABSOLUTA: No recibe mensajes del exterior, no expone endpoints de control.
"""

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from ai_trading_agent.notifications.models import (
    ObservabilityEvent, NotificationType, NotificationSeverity
)
from ai_trading_agent.notifications.dispatcher import telegram_dispatcher, TelegramDispatcher
from ai_trading_agent.domain.fidelity_models import ExecutionDiscrepancy, FidelityScores


class TelegramObservabilityChannel:
    """Canal institucional de observabilidad outbound para Telegram."""

    def __init__(self, dispatcher: Optional[TelegramDispatcher] = None):
        self.dispatcher = dispatcher or telegram_dispatcher

    def notify_system_online(self, strategy_id: str = "D21_RangeCompress_5d", mode: str = "PAPER_TRADING") -> bool:
        """Emite notificación única de inicio del daemon."""
        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=NotificationType.SYSTEM_ONLINE,
            severity=NotificationSeverity.INFO,
            strategy_id=strategy_id,
            trading_mode=mode,
            title="AI Trading Agent Online",
            details={}
        )
        return self.dispatcher.dispatch(event)

    def notify_system_offline(self, strategy_id: str = "D21_RangeCompress_5d", mode: str = "PAPER_TRADING") -> bool:
        """Emite notificación de apagado ordenado del daemon."""
        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=NotificationType.SYSTEM_OFFLINE,
            severity=NotificationSeverity.MEDIUM,
            strategy_id=strategy_id,
            trading_mode=mode,
            title="AI Trading Agent Offline",
            details={}
        )
        return self.dispatcher.dispatch(event)

    def notify_daily_report(
        self,
        daily_metrics: Dict[str, Any],
        scores: Optional[FidelityScores] = None,
        hard_safety_passed: bool = True
    ) -> bool:
        """Envía el resumen diario compacto de Paper Trading."""
        details = dict(daily_metrics)
        if scores:
            details["execution_fidelity"] = scores.overall_execution_fidelity_score
            details["risk_fidelity"] = scores.risk_fidelity_score

        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=NotificationType.DAILY_REPORT,
            severity=NotificationSeverity.INFO,
            strategy_id="D21_RangeCompress_5d",
            title="D21 Paper Daily Report",
            details=details,
            hard_fail_status=not hard_safety_passed,
            evidence_status=details.get("evidence_status", "INSUFFICIENT")
        )
        return self.dispatcher.dispatch(event)

    def notify_discrepancy(self, discrepancy: ExecutionDiscrepancy) -> bool:
        """Enruta discrepancias de ejecución según su nivel de severidad."""
        is_critical = (discrepancy.severity.value == "CRITICAL" or discrepancy.hard_fail)
        
        if is_critical:
            event = ObservabilityEvent(
                event_id=str(uuid.uuid4()),
                event_type=NotificationType.CRITICAL_ALERT,
                severity=NotificationSeverity.CRITICAL,
                strategy_id=discrepancy.strategy_id,
                signal_id=discrepancy.signal_id,
                order_id=discrepancy.order_id,
                title=f"CRITICAL: {discrepancy.category.value}",
                hard_fail_status=True,
                details={
                    "reason": discrepancy.resolution_note or f"Infracción crítica en {discrepancy.category.value}",
                    "safety_action": "HALT SESSION & FORBID NEW PAPER ORDERS"
                }
            )
        else:
            # Evento importante (HIGH / MEDIUM)
            event = ObservabilityEvent(
                event_id=str(uuid.uuid4()),
                event_type=NotificationType.IMPORTANT_EVENT,
                severity=NotificationSeverity(discrepancy.severity.value),
                strategy_id=discrepancy.strategy_id,
                signal_id=discrepancy.signal_id,
                order_id=discrepancy.order_id,
                title=f"ALERT: {discrepancy.category.value}",
                hard_fail_status=False,
                details={
                    "type": discrepancy.category.value,
                    "reason": discrepancy.resolution_note or f"Desviación detectada: {discrepancy.category.value}",
                    "action": "LOGGED IN JOURNAL FOR FIDELITY AUDIT"
                }
            )
        return self.dispatcher.dispatch(event)

    def notify_evidence_status_change(
        self,
        new_status: str,
        previous_status: str = "INSUFFICIENT"
    ) -> bool:
        """Emite alerta de cambio de madurez en la recolección de evidencia."""
        ev_type = (
            NotificationType.SUFFICIENT_FOR_REVIEW 
            if new_status == "SUFFICIENT_FOR_REVIEW" 
            else NotificationType.EVIDENCE_STATUS_CHANGE
        )
        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=ev_type,
            severity=NotificationSeverity.HIGH,
            strategy_id="D21_RangeCompress_5d",
            title=f"D21 Evidence Status: {new_status}",
            evidence_status=new_status,
            details={
                "previous_status": previous_status,
                "evidence_status": new_status
            }
        )
        return self.dispatcher.dispatch(event)

    def notify_hard_safety_failure(self, failure_reasons: list, signal_id: Optional[str] = None) -> bool:
        """Emite alerta de fallo en Hard Safety Gates."""
        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=NotificationType.CRITICAL_ALERT,
            severity=NotificationSeverity.CRITICAL,
            strategy_id="D21_RangeCompress_5d",
            signal_id=signal_id,
            title="CRITICAL HARD SAFETY GATE BREACH",
            hard_fail_status=True,
            details={
                "reason": " | ".join(failure_reasons),
                "safety_action": "HALT SESSION & BLOCK TRADES"
            }
        )
        return self.dispatcher.dispatch(event)


# Instancia singleton del canal de observabilidad
telegram_observability = TelegramObservabilityChannel()
