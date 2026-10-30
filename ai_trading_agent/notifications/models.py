"""
ai_trading_agent.notifications.models
=====================================
Modelos de datos estrictos para el canal de observabilidad de Telegram.
Unidireccional: Solo salida (Outbound Observability).
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationType(str, Enum):
    DAILY_REPORT = "DAILY_REPORT"
    IMPORTANT_EVENT = "IMPORTANT_EVENT"
    CRITICAL_ALERT = "CRITICAL_ALERT"
    EVIDENCE_STATUS_CHANGE = "EVIDENCE_STATUS_CHANGE"
    SUFFICIENT_FOR_REVIEW = "SUFFICIENT_FOR_REVIEW"
    SYSTEM_ONLINE = "SYSTEM_ONLINE"
    SYSTEM_OFFLINE = "SYSTEM_OFFLINE"


class ObservabilityEvent(BaseModel):
    """Evento estructurado para emisión por Telegram."""
    event_id: str
    event_type: NotificationType
    severity: NotificationSeverity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    strategy_id: str = "D21_RangeCompress_5d"
    strategy_version: str = "1.0"
    trading_mode: str = "PAPER_TRADING"
    signal_id: Optional[str] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    title: str
    details: Dict[str, Any] = Field(default_factory=dict)
    hard_fail_status: bool = False
    evidence_status: Optional[str] = None
