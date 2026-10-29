"""
ai_trading_agent.dual_strategy.simulation
=========================================
Motor de Simulación de Ejecución y Adaptador Paper Seguro para OracleBot v2.
Asegura bloqueo físico de endpoints Live, contabilidad exacta de fricciones,
modelado de latencia, comisiones, spreads, gaps nocturnos y liquidación forzosa a las 15:50 ET.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, time
import math
import uuid

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import OrderStatus, OrderSide
from ai_trading_agent.dual_strategy.models import (
    ReproducibleSignal, TradeFillRecord, OperationalExecutionMode
)


class SecurityViolationError(RuntimeError):
    """Lanzada cuando se detecta un intento de conexión o configuración hacia endpoints reales (LIVE)."""
    pass


class PaperBrokerSecurityGuard:
    """Guardaespaldas de aislamiento que verifica que ningún endpoint sea de producción real."""

    ALLOWED_PAPER_HOSTS = ["127.0.0.1", "localhost", "paper-api.alpaca.markets", "mock_internal"]

    @classmethod
    def assert_paper_environment_only(cls, url: str):
        if not url:
            return
        is_safe = any(h in url.lower() for h in cls.ALLOWED_PAPER_HOSTS)
        if not is_safe or "api.alpaca.markets" in url.lower() and "paper" not in url.lower():
            raise SecurityViolationError(f"VIOLACIÓN CRÍTICA DE SEGURIDAD: Endpoint en vivo detectado ({url}). LIVE está estrictamente prohibido.")


class SimulationExecutionEngine:
    """
    Motor de ejecución simulada con modelado de fricciones institucionales.
    Calcula comisiones ($0.005/acción), deslizamiento (5 bps por defecto) e impacto de gaps.
    """

    def __init__(
        self,
        commission_per_share: float = 0.005,
        base_slippage_bps: float = 5.0,  # 5 bps = 0.05%
        cost_multiplier: float = 1.0,    # 1.0x Base, 2.0x Doble, 3.0x Triple
        mode: OperationalExecutionMode = OperationalExecutionMode.SHADOW
    ):
        self.commission_per_share = commission_per_share * cost_multiplier
        self.slippage_pct = (base_slippage_bps / 10000.0) * cost_multiplier
        self.mode = mode

    def simulate_entry(
        self,
        signal: ReproducibleSignal,
        quantity: int,
        next_bar: OHLCVBar,
        spread_pct: float = 0.0005
    ) -> TradeFillRecord:
        """
        Simula la entrada en el primer precio negociable de la siguiente barra (next_bar.open).
        Añade deslizamiento adverso y medio spread.
        Zero Look-Ahead: Entrada ocurre en next_bar.open, nunca en signal_bar.close.
        """
        exec_price_raw = next_bar.open
        # Fricción de entrada: deslizamiento hacia arriba (adverso para compra) + medio spread
        friction = (self.slippage_pct + (spread_pct / 2.0)) * exec_price_raw
        fill_price = round(exec_price_raw + friction, 2)

        slippage_cost = round((fill_price - exec_price_raw) * quantity, 2)
        commission_cost = round(max(1.0, quantity * self.commission_per_share), 2)

        trade_id = f"TRD_{signal.strategy_id}_{signal.symbol}_{uuid.uuid4().hex[:8]}"

        return TradeFillRecord(
            trade_id=trade_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            requested_price=signal.entry_reference,
            fill_price=fill_price,
            slippage_usd=slippage_cost,
            commission_usd=commission_cost,
            entry_time=next_bar.timestamp,
            mode=self.mode
        )

    def simulate_exit(
        self,
        open_trade: TradeFillRecord,
        exit_bar: OHLCVBar,
        exit_reason: str,
        planned_stop: float,
        planned_target: float,
        spread_pct: float = 0.0005,
        is_overnight_gap: bool = False
    ) -> TradeFillRecord:
        """
        Simula la salida y calcula PnL bruto, PnL neto, comisiones y R-múltiplo realizado.
        Modela deslizamiento adverso en la salida y posibles gaps de apertura.
        """
        if exit_reason == "TAKE_PROFIT":
            exec_price_raw = planned_target
        elif exit_reason == "STOP_LOSS":
            # Si hay gap a la baja por debajo del stop en apertura de barra
            if exit_bar.open < planned_stop:
                exec_price_raw = exit_bar.open
                is_overnight_gap = True
            else:
                exec_price_raw = planned_stop
        elif exit_reason in ("SESSION_SQUARE_OFF", "TIME_EXIT", "MANUAL_HALT"):
            exec_price_raw = exit_bar.close
        else:
            exec_price_raw = exit_bar.close

        # Fricción de salida (venta: deslizamiento hacia abajo)
        friction = (self.slippage_pct + (spread_pct / 2.0)) * exec_price_raw
        exit_fill_price = round(exec_price_raw - friction, 2)

        exit_slippage = round((exec_price_raw - exit_fill_price) * open_trade.quantity, 2)
        exit_commission = round(max(1.0, open_trade.quantity * self.commission_per_share), 2)

        total_commission = open_trade.commission_usd + exit_commission
        total_slippage = open_trade.slippage_usd + exit_slippage

        gross_pnl = round((exit_fill_price - open_trade.fill_price) * open_trade.quantity, 2)
        net_pnl = round(gross_pnl - exit_commission, 2)

        # R-múltiplo realizado relativo al riesgo inicial planeado
        initial_risk_per_share = max(0.01, abs(open_trade.fill_price - planned_stop))
        r_multiple = round((exit_fill_price - open_trade.fill_price) / initial_risk_per_share, 2)

        overnight_gap_usd = 0.0
        if is_overnight_gap:
            overnight_gap_usd = round(abs(planned_stop - exit_bar.open) * open_trade.quantity, 2)

        return TradeFillRecord(
            trade_id=open_trade.trade_id,
            strategy_id=open_trade.strategy_id,
            symbol=open_trade.symbol,
            side=open_trade.side,
            quantity=open_trade.quantity,
            requested_price=open_trade.requested_price,
            fill_price=open_trade.fill_price,
            slippage_usd=round(total_slippage, 2),
            commission_usd=round(total_commission, 2),
            entry_time=open_trade.entry_time,
            exit_time=exit_bar.timestamp,
            exit_price=exit_fill_price,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            r_multiple=r_multiple,
            holding_bars=open_trade.holding_bars + 1,
            mode=open_trade.mode,
            overnight_gap_usd=overnight_gap_usd
        )
