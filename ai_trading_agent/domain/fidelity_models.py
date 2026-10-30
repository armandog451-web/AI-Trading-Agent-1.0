"""
ai_trading_agent.domain.fidelity_models
=======================================
Modelos de datos y enumeraciones para el Paper Trading Fidelity & Discrepancy Engine.
Permite comparar la intención esperada contra la ejecución real en Paper Trading.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DiscrepancyCategory(str, Enum):
    SIGNAL_MISMATCH = "SIGNAL_MISMATCH"
    MISSED_SIGNAL = "MISSED_SIGNAL"
    DUPLICATE_SIGNAL = "DUPLICATE_SIGNAL"
    ORDER_NOT_CREATED = "ORDER_NOT_CREATED"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    ENTRY_PRICE_DEVIATION = "ENTRY_PRICE_DEVIATION"
    ENTRY_TIME_DEVIATION = "ENTRY_TIME_DEVIATION"
    POSITION_SIZE_DEVIATION = "POSITION_SIZE_DEVIATION"
    RISK_DEVIATION = "RISK_DEVIATION"
    STOP_MISMATCH = "STOP_MISMATCH"
    TAKE_PROFIT_MISMATCH = "TAKE_PROFIT_MISMATCH"
    EXIT_RULE_MISMATCH = "EXIT_RULE_MISMATCH"
    EXIT_PRICE_DEVIATION = "EXIT_PRICE_DEVIATION"
    EXIT_TIME_DEVIATION = "EXIT_TIME_DEVIATION"
    SLIPPAGE_DEVIATION = "SLIPPAGE_DEVIATION"
    SPREAD_DEVIATION = "SPREAD_DEVIATION"
    LATENCY_DEVIATION = "LATENCY_DEVIATION"
    BROKER_REJECTION = "BROKER_REJECTION"
    BROKER_CANCELLATION = "BROKER_CANCELLATION"
    DATA_MISMATCH = "DATA_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    UNKNOWN_EXECUTION_ANOMALY = "UNKNOWN_EXECUTION_ANOMALY"


class DiscrepancySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PaperEvidenceStatus(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"
    DEVELOPING = "DEVELOPING"
    SUFFICIENT_FOR_REVIEW = "SUFFICIENT_FOR_REVIEW"


class PaperValidationLifecycleStatus(str, Enum):
    PAPER_COLLECTING_EVIDENCE = "PAPER_COLLECTING_EVIDENCE"
    PAPER_EXECUTION_VALIDATED = "PAPER_EXECUTION_VALIDATED"
    PAPER_PERFORMANCE_UNDER_REVIEW = "PAPER_PERFORMANCE_UNDER_REVIEW"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    PAPER_REJECTED = "PAPER_REJECTED"


class ExpectedTradeExecution(BaseModel):
    """
    Registro inmutable de la intención de ejecución generado ANTES del fill.
    Captura lo que D21 y el RiskEngine ordenaron realizar.
    """
    strategy_id: str
    strategy_version: str = "1.0"
    signal_id: str
    symbol: str
    side: str  # BUY / SELL

    signal_timestamp: datetime
    signal_price: float

    expected_entry_type: str = "MARKET"
    expected_entry_price: float
    expected_entry_window: str = "NEXT_SESSION_OPEN"

    expected_position_size: int
    expected_notional: float
    expected_risk_amount: float
    expected_risk_pct: float

    expected_stop_price: float
    expected_take_profit_price: Optional[float] = None

    expected_exit_rules: Dict[str, Any] = Field(default_factory=dict)
    expected_max_holding_period: int = 5  # días

    expected_commission: float = 0.0
    expected_slippage: float = 0.0
    expected_spread: float = 0.0

    market_regime: str = "UNKNOWN"
    market_session: str = "REGULAR"

    specification_hash: str = ""
    strategy_config_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActualTradeExecution(BaseModel):
    """
    Registro de lo que realmente ocurrió durante la ejecución y resolución de la orden en Paper.
    """
    signal_id: str
    order_id: str
    broker_order_id: Optional[str] = None

    order_created_at: datetime
    order_submitted_at: Optional[datetime] = None
    order_acknowledged_at: Optional[datetime] = None
    fill_timestamp: Optional[datetime] = None

    requested_price: float
    actual_fill_price: Optional[float] = None

    requested_quantity: int
    actual_quantity: int = 0
    actual_notional: float = 0.0

    actual_stop_price: Optional[float] = None
    actual_take_profit_price: Optional[float] = None

    actual_commission: float = 0.0
    actual_slippage: float = 0.0
    actual_spread: float = 0.0

    order_status: str = "PENDING"
    broker_status: str = "SUBMITTED"

    exit_timestamp: Optional[datetime] = None
    actual_exit_price: Optional[float] = None
    actual_exit_reason: Optional[str] = None

    realized_pnl: float = 0.0
    realized_return: float = 0.0

    rejection_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None


class ExecutionDiscrepancy(BaseModel):
    """
    Registro de cualquier discrepancia detectada entre Expected y Actual.
    """
    discrepancy_id: str
    strategy_id: str
    signal_id: str
    order_id: Optional[str] = None

    category: DiscrepancyCategory
    severity: DiscrepancySeverity

    expected_value: Any
    actual_value: Any

    absolute_deviation: float = 0.0
    relative_deviation: float = 0.0
    deviation_bps: float = 0.0

    detected_at: datetime = Field(default_factory=datetime.utcnow)
    market_context: Dict[str, Any] = Field(default_factory=dict)

    requires_review: bool = False
    hard_fail: bool = False
    resolved: bool = False
    resolution_note: Optional[str] = None


class FidelityScores(BaseModel):
    """
    Puntajes determinísticos y desacoplados de fidelidad (0-100).
    """
    signal_fidelity_score: float = 100.0
    order_fidelity_score: float = 100.0
    entry_fidelity_score: float = 100.0
    position_size_fidelity_score: float = 100.0
    risk_fidelity_score: float = 100.0
    stop_fidelity_score: float = 100.0
    exit_fidelity_score: float = 100.0
    execution_timing_fidelity_score: float = 100.0
    overall_execution_fidelity_score: float = 100.0
    hard_fail_active: bool = False
