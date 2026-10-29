"""
ai_trading_agent.dual_strategy.models
=====================================
Contratos inmutables fuertemente tipados para OracleBot v2 Dual Strategy Framework.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json
from pydantic import BaseModel, Field, ConfigDict, model_validator

from ai_trading_agent.domain.enums import SignalDirection, MarketRegime, OrderStatus, OrderSide


class DualStrategyLifecycleStatus(str, Enum):
    RESEARCH = "RESEARCH"
    BACKTESTED = "BACKTESTED"
    CANDIDATE = "CANDIDATE"
    SHADOW_PAPER = "SHADOW_PAPER"
    PAPER_EVIDENCE = "PAPER_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECTED = "REJECTED"


class OperationalExecutionMode(str, Enum):
    SHADOW = "SHADOW"              # Señales y órdenes virtuales sin transmisión externa
    PAPER_BROKER = "PAPER_BROKER"  # Transmisión a endpoints de paper autorizados exclusivamente


class ReproducibleSignal(BaseModel):
    """
    Señal inmutable, reproducible y trazable con hash criptográfico del snapshot de datos.
    No ejecuta órdenes directamente: debe ser evaluada por el PortfolioRiskEngine.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_id: str
    version: str
    configuration_hash: str
    symbol: str
    market_timestamp: datetime
    evaluation_timestamp: datetime
    direction: SignalDirection
    entry_reference: float = Field(..., gt=0.0)
    stop_reference: float = Field(..., gt=0.0)
    target_reference: float = Field(..., gt=0.0)
    estimated_risk: float = Field(..., gt=0.0)
    reason_codes: List[str] = Field(default_factory=list)
    data_snapshot_hash: str
    score: float = Field(default=50.0, ge=0.0, le=100.0)
    context_timeframe: str = "1h"
    signal_timeframe: str = "15m"
    market_regime: MarketRegime = MarketRegime.BULL_TREND
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rr_geometry(self):
        if self.direction == SignalDirection.BUY:
            if self.stop_reference >= self.entry_reference:
                raise ValueError("Stop loss must be strictly below entry price for BUY signals")
            if self.target_reference <= self.entry_reference:
                raise ValueError("Target reference must be strictly above entry price for BUY signals")
            risk = self.entry_reference - self.stop_reference
            reward = self.target_reference - self.entry_reference
            if reward < 1.99 * risk:  # Allow minimal floating point leeway for 2:1 ratio
                raise ValueError(f"Projected Risk:Reward ratio {reward/risk:.2f} is below minimum requirement 2:1")
        elif self.direction == SignalDirection.SELL:
            # OracleBot v2 is strictly long-only for cash equity paper accounts
            raise ValueError("Short/SELL direction is prohibited in OracleBot v2 Cash Equity Architecture")
        return self

    @property
    def signal_id(self) -> str:
        """Identificador determinista derivado del contenido de la señal."""
        raw = f"{self.strategy_id}:{self.version}:{self.symbol}:{self.market_timestamp.isoformat()}:{self.direction.value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class RiskReservation(BaseModel):
    """Reserva centralizada de riesgo de cartera para evitar condiciones de carrera."""
    model_config = ConfigDict(frozen=True)

    reservation_id: str
    strategy_id: str
    symbol: str
    sector: str
    reserved_risk_usd: float
    reserved_notional_usd: float
    timestamp: datetime
    status: str = "ACTIVE"  # ACTIVE, COMMITTED, RELEASED


class TradeFillRecord(BaseModel):
    """Registro inmutable de ejecución simulada o en broker paper."""
    model_config = ConfigDict(frozen=True)

    trade_id: str
    strategy_id: str
    symbol: str
    side: OrderSide
    quantity: int
    requested_price: float
    fill_price: float
    slippage_usd: float
    commission_usd: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    r_multiple: float = 0.0
    holding_bars: int = 0
    mode: OperationalExecutionMode = OperationalExecutionMode.SHADOW
    overnight_gap_usd: float = 0.0
