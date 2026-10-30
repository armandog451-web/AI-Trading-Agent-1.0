"""
ai_trading_agent.notifications.formatter
========================================
Formateador institucional de mensajes para Telegram.
Genera mensajes concisos, legibles en dispositivos móviles y con separación estricta
entre P&L y fidelidad de ejecución.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from ai_trading_agent.notifications.models import ObservabilityEvent, NotificationType, NotificationSeverity


class TelegramMessageFormatter:
    """Convierte eventos de observabilidad en mensajes Markdown limpios para Telegram."""

    @staticmethod
    def format_daily_report(event: ObservabilityEvent) -> str:
        d = event.details
        date_str = d.get("date", datetime.utcnow().strftime("%Y-%m-%d"))
        status = d.get("status", "PAPER_COLLECTING_EVIDENCE")
        signals = d.get("signals_generated", 0)
        trades_completed = d.get("trades_completed", 0)
        open_positions = d.get("open_positions", 0)

        exec_fidelity = d.get("execution_fidelity", 100.0)
        risk_fidelity = d.get("risk_fidelity", 100.0)

        mean_slip = d.get("mean_slippage_bps", 0.0)
        p95_slip = d.get("p95_slippage_bps", 0.0)

        pnl_today = d.get("pnl_today", 0.0)
        cum_pnl = d.get("cum_paper_pnl", 0.0)
        dd = d.get("drawdown_pct", 0.0)

        disc = d.get("discrepancies", {})
        low_d = disc.get("LOW", 0)
        med_d = disc.get("MEDIUM", 0)
        high_d = disc.get("HIGH", 0)
        crit_d = disc.get("CRITICAL", 0)

        hard_fail = "YES" if event.hard_fail_status or crit_d > 0 else "NO"
        evidence_status = event.evidence_status or d.get("evidence_status", "INSUFFICIENT")

        return (
            f"📋 *D21 — PAPER DAILY REPORT*\n\n"
            f"*Date:* {date_str}\n"
            f"*Status:* `{status}`\n\n"
            f"*Signals:* {signals}\n"
            f"*Trades Completed:* {trades_completed}\n"
            f"*Open Positions:* {open_positions}\n\n"
            f"*Execution Fidelity:* {exec_fidelity:.1f} / 100\n"
            f"*Risk Fidelity:* {risk_fidelity:.1f} / 100\n\n"
            f"*Mean Slippage:* {mean_slip:.1f} bps\n"
            f"*P95 Slippage:* {p95_slip:.1f} bps\n\n"
            f"*PnL Today:* ${pnl_today:,.2f}\n"
            f"*Cumulative Paper PnL:* ${cum_pnl:,.2f}\n"
            f"*Drawdown:* {dd:.2f}%\n\n"
            f"*Discrepancies:*\n"
            f"  LOW: {low_d}\n"
            f"  MEDIUM: {med_d}\n"
            f"  HIGH: {high_d}\n"
            f"  CRITICAL: {crit_d}\n\n"
            f"*Hard Fail:* {hard_fail}\n"
            f"*Evidence Status:* `{evidence_status}`\n\n"
            f"*LIVE:* `BLOCKED`"
        )

    @staticmethod
    def format_important_event(event: ObservabilityEvent) -> str:
        d = event.details
        event_name = d.get("type", "IMPORTANT_EVENT")
        sig = event.signal_id or d.get("signal_id", "N/A")
        sym = event.symbol or d.get("symbol", "N/A")
        action = d.get("action", "LOGGED FOR REVIEW")
        reason = d.get("reason", "Anomalía o evento de ejecución detectado.")

        return (
            f"⚠️ *D21 PAPER ALERT*\n\n"
            f"*Type:* `{event_name}`\n"
            f"*Signal:* `{sig}`\n"
            f"*Symbol:* `{sym}`\n"
            f"*Severity:* `{event.severity.value}`\n"
            f"*Trading Mode:* `{event.trading_mode}`\n\n"
            f"*Detail:* {reason}\n"
            f"*Action:* `{action}`\n\n"
            f"*LIVE:* `BLOCKED`"
        )

    @staticmethod
    def format_critical_alert(event: ObservabilityEvent) -> str:
        d = event.details
        strat = event.strategy_id
        reason = d.get("reason", "Violación crítica o Hard Safety Gate activado.")
        sig = event.signal_id or d.get("signal_id", "N/A")
        ord_id = event.order_id or d.get("order_id", "N/A")
        action = d.get("safety_action", "HALT SESSION & BLOCK TRADES")

        return (
            f"🚨 *D21 CRITICAL PAPER ALERT*\n\n"
            f"*STATUS:* `HARD_FAIL`\n"
            f"*Strategy:* `{strat}`\n"
            f"*Reason:* {reason}\n\n"
            f"*Signal ID:* `{sig}`\n"
            f"*Order ID:* `{ord_id}`\n"
            f"*Trading Mode:* `{event.trading_mode}`\n\n"
            f"*Automatic Safety Action:* `{action}`\n\n"
            f"*LIVE TRADING:* `BLOCKED`"
        )

    @staticmethod
    def format_evidence_update(event: ObservabilityEvent) -> str:
        ev_status = event.evidence_status or event.details.get("evidence_status", "DEVELOPING")
        prev = event.details.get("previous_status", "INSUFFICIENT")

        if ev_status == "SUFFICIENT_FOR_REVIEW":
            return (
                f"🎯 *D21 PAPER EVIDENCE READY FOR REVIEW*\n\n"
                f"*Evidence Status:* `{ev_status}`\n"
                f"Cohort has accumulated sufficient observational evidence.\n\n"
                f"Artifact generated:\n"
                f"`D21_PAPER_EVIDENCE_REVIEW_PACKAGE.md`\n\n"
                f"No lifecycle promotion has occurred.\n"
                f"*D21 remains:* `PAPER`\n"
                f"*Human review required.*\n\n"
                f"*LIVE:* `BLOCKED`"
            )
        else:
            return (
                f"📊 *D21 EVIDENCE UPDATE*\n\n"
                f"*Transition:* `{prev}` ➔ `{ev_status}`\n"
                f"*Evidence Status:* `{ev_status}`\n\n"
                f"No lifecycle promotion has occurred.\n\n"
                f"*D21 remains:* `PAPER`\n"
                f"*Human review required.*\n\n"
                f"*LIVE:* `BLOCKED`"
            )

    @staticmethod
    def format_system_online(event: ObservabilityEvent) -> str:
        return (
            f"✅ *AI TRADING AGENT ONLINE*\n\n"
            f"*Strategy:* `{event.strategy_id}`\n"
            f"*Mode:* `{event.trading_mode}`\n"
            f"*Fidelity Engine:* `ACTIVE`\n"
            f"*Evidence Collection:* `ACTIVE`\n\n"
            f"*LIVE:* `BLOCKED`"
        )

    @staticmethod
    def format_system_offline(event: ObservabilityEvent) -> str:
        return (
            f"⚠️ *AI TRADING AGENT OFFLINE*\n\n"
            f"D21 paper runtime has stopped.\n"
            f"No new orders can be generated until restart.\n\n"
            f"*LIVE:* `BLOCKED`"
        )

    @classmethod
    def format_event(cls, event: ObservabilityEvent) -> str:
        """Enruta el evento al formateador adecuado."""
        if event.event_type == NotificationType.DAILY_REPORT:
            return cls.format_daily_report(event)
        elif event.event_type == NotificationType.CRITICAL_ALERT:
            return cls.format_critical_alert(event)
        elif event.event_type == NotificationType.IMPORTANT_EVENT:
            return cls.format_important_event(event)
        elif event.event_type in (NotificationType.EVIDENCE_STATUS_CHANGE, NotificationType.SUFFICIENT_FOR_REVIEW):
            return cls.format_evidence_update(event)
        elif event.event_type == NotificationType.SYSTEM_ONLINE:
            return cls.format_system_online(event)
        elif event.event_type == NotificationType.SYSTEM_OFFLINE:
            return cls.format_system_offline(event)
        else:
            return (
                f"ℹ️ *D21 NOTIFICATION*\n\n"
                f"*{event.title}*\n"
                f"{event.details.get('message', '')}\n\n"
                f"*LIVE:* `BLOCKED`"
            )
