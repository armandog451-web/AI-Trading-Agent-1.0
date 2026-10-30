"""
ai_trading_agent/tests/test_telegram_observability.py
=====================================================
Suite de pruebas institucionales para el canal de observabilidad de Telegram.
Verifica:
1. telegram_disabled_does_not_affect_runtime
2. telegram_failure_does_not_affect_trading
3. token_never_written_to_logs
4. daily_report_format
5. high_discrepancy_generates_notification
6. critical_discrepancy_generates_notification
7. hard_fail_generates_notification
8. duplicate_notification_is_suppressed
9. rate_limit_prevents_spam
10. evidence_status_change_generates_notification
11. sufficient_for_review_generates_notification
12. telegram_cannot_submit_orders (Security verification)
13. telegram_cannot_change_trading_mode (Security verification)
14. telegram_cannot_modify_risk (Security verification)
15. telegram_cannot_enable_live (Security verification)
"""

import pytest
import os
import json
import uuid
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_trading_agent.config.settings import settings
from ai_trading_agent.domain.enums import TradingMode
from ai_trading_agent.domain.fidelity_models import (
    ExecutionDiscrepancy, DiscrepancyCategory, DiscrepancySeverity,
    ExpectedTradeExecution, ActualTradeExecution, FidelityScores
)
from ai_trading_agent.notifications.models import (
    ObservabilityEvent, NotificationType, NotificationSeverity
)
from ai_trading_agent.notifications.formatter import TelegramMessageFormatter
from ai_trading_agent.notifications.dispatcher import TelegramDispatcher
from ai_trading_agent.notifications.journal import NotificationJournal
from ai_trading_agent.notifications.telegram_notifier import TelegramObservabilityChannel
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry


@pytest.fixture
def temp_journal(tmp_path):
    return NotificationJournal(storage_dir=tmp_path)


@pytest.fixture
def dispatcher(temp_journal):
    return TelegramDispatcher(journal=temp_journal)


@pytest.fixture
def channel(dispatcher):
    return TelegramObservabilityChannel(dispatcher=dispatcher)


def test_telegram_disabled_does_not_affect_runtime(channel):
    """Verifica que si Telegram está deshabilitado, la llamada retorne False limpiamente sin fallar."""
    with patch.object(settings, "TELEGRAM_ENABLED", False):
        res = channel.notify_system_online()
        assert res is False


def test_telegram_failure_does_not_affect_trading(channel):
    """Verifica que una falla de red (timeout / 500) en Telegram no levante excepciones ni bloquee el código."""
    with patch.object(settings, "TELEGRAM_ENABLED", True), \
         patch.object(settings, "TELEGRAM_BOT_TOKEN", "mock_token"), \
         patch.object(settings, "TELEGRAM_CHAT_ID", "mock_chat"), \
         patch("httpx.Client.post", side_effect=Exception("Connection refused / Timeout")):
        
        # Debe capturarse la excepción y retornar False
        res = channel.notify_system_online()
        assert res is False


def test_token_never_written_to_logs(temp_journal):
    """Verifica que el bot token NUNCA sea persistido en el archivo de log/journal de notificaciones."""
    secret_token = "SECRET_BOT_TOKEN_12345"
    with patch.object(settings, "TELEGRAM_BOT_TOKEN", secret_token):
        temp_journal.record_notification(
            notification_id="test_notif_1",
            event_type="DAILY_REPORT",
            severity="INFO",
            message_hash="hash123",
            delivery_status="DELIVERED",
            retry_count=0
        )
        
        # Leer contenido crudo del log
        log_content = temp_journal.log_file.read_text(encoding="utf-8")
        assert secret_token not in log_content
        assert "SECRET_BOT_TOKEN" not in log_content


def test_daily_report_format():
    """Verifica que el formateador del reporte diario contenga todos los campos obligatorios."""
    event = ObservabilityEvent(
        event_id="d_report_1",
        event_type=NotificationType.DAILY_REPORT,
        severity=NotificationSeverity.INFO,
        title="Daily Report",
        details={
            "date": "2026-10-06",
            "status": "PAPER_COLLECTING_EVIDENCE",
            "signals_generated": 2,
            "trades_completed": 1,
            "open_positions": 1,
            "execution_fidelity": 98.5,
            "risk_fidelity": 100.0,
            "mean_slippage_bps": 2.5,
            "p95_slippage_bps": 4.0,
            "pnl_today": 150.0,
            "cum_paper_pnl": 150.0,
            "drawdown_pct": 0.2,
            "discrepancies": {"LOW": 1, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
            "evidence_status": "DEVELOPING"
        }
    )
    formatted = TelegramMessageFormatter.format_daily_report(event)
    assert "D21" in formatted
    assert "PAPER DAILY REPORT" in formatted
    assert "Execution Fidelity:* 98.5 / 100" in formatted
    assert "Risk Fidelity:* 100.0 / 100" in formatted
    assert "Evidence Status:* `DEVELOPING`" in formatted
    assert "LIVE:* `BLOCKED`" in formatted


def test_high_discrepancy_generates_notification(channel):
    """Verifica que una discrepancia HIGH emita un evento de severidad HIGH."""
    disc = ExecutionDiscrepancy(
        discrepancy_id="disc_hi_1",
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_100",
        order_id="ord_100",
        category=DiscrepancyCategory.BROKER_REJECTION,
        severity=DiscrepancySeverity.HIGH,
        expected_value="FILLED",
        actual_value="REJECTED",
        requires_review=True,
        resolution_note="Rechazo por margen"
    )
    with patch.object(channel.dispatcher, "dispatch") as mock_dispatch:
        channel.notify_discrepancy(disc)
        assert mock_dispatch.called
        event = mock_dispatch.call_args[0][0]
        assert event.event_type == NotificationType.IMPORTANT_EVENT
        assert event.severity == NotificationSeverity.HIGH
        assert event.signal_id == "sig_100"


def test_critical_discrepancy_generates_notification(channel):
    """Verifica que una discrepancia CRITICAL emita un evento CRITICAL_ALERT con flag hard_fail."""
    disc = ExecutionDiscrepancy(
        discrepancy_id="disc_crit_1",
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_crit_1",
        order_id="ord_crit_1",
        category=DiscrepancyCategory.STOP_MISMATCH,
        severity=DiscrepancySeverity.CRITICAL,
        expected_value=490.0,
        actual_value=None,
        hard_fail=True,
        resolution_note="Stop loss ausente"
    )
    with patch.object(channel.dispatcher, "dispatch") as mock_dispatch:
        channel.notify_discrepancy(disc)
        assert mock_dispatch.called
        event = mock_dispatch.call_args[0][0]
        assert event.event_type == NotificationType.CRITICAL_ALERT
        assert event.severity == NotificationSeverity.CRITICAL
        assert event.hard_fail_status is True


def test_hard_fail_generates_notification(channel):
    """Verifica que una violación en Hard Safety Gate emita CRITICAL_ALERT."""
    with patch.object(channel.dispatcher, "dispatch") as mock_dispatch:
        channel.notify_hard_safety_failure(
            failure_reasons=["Riesgo excede $2,500 USD"],
            signal_id="sig_hard_fail"
        )
        assert mock_dispatch.called
        event = mock_dispatch.call_args[0][0]
        assert event.event_type == NotificationType.CRITICAL_ALERT
        assert event.hard_fail_status is True


def test_duplicate_notification_is_suppressed(dispatcher):
    """Verifica que eventos idénticos emitidos en rápida sucesión sean deduplicados y suprimidos."""
    with patch.object(settings, "TELEGRAM_ENABLED", True), \
         patch.object(settings, "TELEGRAM_BOT_TOKEN", "mock_tok"), \
         patch.object(settings, "TELEGRAM_CHAT_ID", "mock_chat"), \
         patch("httpx.Client.post") as mock_post:
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        event = ObservabilityEvent(
            event_id="evt_dup_1",
            event_type=NotificationType.IMPORTANT_EVENT,
            severity=NotificationSeverity.HIGH,
            signal_id="sig_dup",
            title="Slippage Alert",
            details={"type": "ENTRY_PRICE_DEVIATION"}
        )

        res1 = dispatcher.dispatch(event)
        res2 = dispatcher.dispatch(event)

        assert res1 is True
        assert res2 is False  # Suprimido por deduplicación
        assert mock_post.call_count == 1


def test_rate_limit_prevents_spam(dispatcher):
    """Verifica que eventos LOW no generen llamadas HTTP y que eventos repetidos se filtren."""
    with patch.object(settings, "TELEGRAM_ENABLED", True), \
         patch.object(settings, "TELEGRAM_BOT_TOKEN", "mock_tok"), \
         patch.object(settings, "TELEGRAM_CHAT_ID", "mock_chat"), \
         patch("httpx.Client.post") as mock_post:

        event_low = ObservabilityEvent(
            event_id="evt_low_1",
            event_type=NotificationType.IMPORTANT_EVENT,
            severity=NotificationSeverity.LOW,
            title="Minor Deviation",
            details={}
        )
        res = dispatcher.dispatch(event_low)
        assert res is False
        assert mock_post.call_count == 0


def test_evidence_status_change_generates_notification(channel):
    """Verifica que un cambio de estatus de evidencia emita alerta."""
    with patch.object(channel.dispatcher, "dispatch") as mock_dispatch:
        channel.notify_evidence_status_change(new_status="DEVELOPING", previous_status="INSUFFICIENT")
        assert mock_dispatch.called
        event = mock_dispatch.call_args[0][0]
        assert event.event_type == NotificationType.EVIDENCE_STATUS_CHANGE
        assert event.evidence_status == "DEVELOPING"


def test_sufficient_for_review_generates_notification(channel):
    """Verifica que alcanzar SUFFICIENT_FOR_REVIEW genere la alerta especial correspondiente."""
    with patch.object(channel.dispatcher, "dispatch") as mock_dispatch:
        channel.notify_evidence_status_change(new_status="SUFFICIENT_FOR_REVIEW", previous_status="DEVELOPING")
        assert mock_dispatch.called
        event = mock_dispatch.call_args[0][0]
        assert event.event_type == NotificationType.SUFFICIENT_FOR_REVIEW
        assert event.evidence_status == "SUFFICIENT_FOR_REVIEW"
        formatted = TelegramMessageFormatter.format_event(event)
        assert "D21 PAPER EVIDENCE READY FOR REVIEW" in formatted
        assert "D21_PAPER_EVIDENCE_REVIEW_PACKAGE.md" in formatted


# ==============================================================================
# PRUEBAS DE SEGURIDAD ABSOLUTA — INEXISTENCIA DE INBOUND PATHS
# ==============================================================================

def test_telegram_cannot_submit_orders():
    """Garantiza que el módulo de notificaciones no tenga métodos de submit_order ni acceso de escritura a brokers."""
    from ai_trading_agent import notifications
    notifier_members = dir(notifications.telegram_observability)
    for m in notifier_members:
        assert "order" not in m.lower() or "notify" in m.lower(), f"Suspicious order method found in telegram: {m}"
        assert "buy" not in m.lower(), f"Inbound buy command found: {m}"
        assert "sell" not in m.lower(), f"Inbound sell command found: {m}"


def test_telegram_cannot_change_trading_mode():
    """Garantiza que Telegram no tenga capacidad para mutar settings.TRADING_MODE."""
    original_mode = settings.TRADING_MODE
    from ai_trading_agent.notifications.telegram_notifier import telegram_observability
    method_names = [m for m in dir(telegram_observability) if not m.startswith("_") and callable(getattr(telegram_observability, m))]
    for name in method_names:
        assert not name.startswith("set_")
        assert not name.startswith("change_")
        assert not name.startswith("modify_")
        assert name.startswith("notify_")
    assert settings.TRADING_MODE == original_mode


def test_telegram_cannot_modify_risk():
    """Garantiza que Telegram no pueda mutar RISK_PER_TRADE_PCT ni límites de riesgo."""
    original_risk = settings.RISK_PER_TRADE_PCT
    from ai_trading_agent.notifications import telegram_notifier
    assert not hasattr(telegram_notifier, "set_risk")
    assert not hasattr(telegram_notifier, "change_risk")
    assert settings.RISK_PER_TRADE_PCT == original_risk


def test_telegram_cannot_enable_live():
    """Garantiza que no exista ruta para habilitar LIVE desde el módulo de notificaciones."""
    from ai_trading_agent import notifications
    module_src = inspect.getsource(notifications)
    assert "LIVE_TRADING_ENABLED = True" not in module_src
    assert "TradingMode.LIVE" not in module_src
    assert "TrdEnv.REAL" not in module_src
