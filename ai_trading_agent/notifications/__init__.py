"""
ai_trading_agent.notifications
==============================
Módulo de notificaciones externas.
"""
from ai_trading_agent.notifications.telegram_service import telegram_notifier, TelegramAlertService
from ai_trading_agent.notifications.telegram_notifier import telegram_observability, TelegramObservabilityChannel
from ai_trading_agent.notifications.models import ObservabilityEvent, NotificationType, NotificationSeverity
from ai_trading_agent.notifications.dispatcher import telegram_dispatcher, TelegramDispatcher
from ai_trading_agent.notifications.journal import NotificationJournal

__all__ = [
    "telegram_notifier",
    "TelegramAlertService",
    "telegram_observability",
    "TelegramObservabilityChannel",
    "ObservabilityEvent",
    "NotificationType",
    "NotificationSeverity",
    "telegram_dispatcher",
    "TelegramDispatcher",
    "NotificationJournal"
]
