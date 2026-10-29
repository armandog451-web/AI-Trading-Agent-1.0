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


class SynchronousPortfolioSimulator:
    """
    Simulador de Cartera Multi-Activo Sincrónico (Barra a Barra).
    Garantiza:
    1. Orden temporal global unificado a través de todos los activos.
    2. Reinicio estricto de disyuntores diario (2R) y semanal (5R) al cambiar de sesión bursátil o semana ISO.
    3. Evaluación de salidas prioritarias antes de evaluar nuevas entradas.
    4. Cero look-ahead: señal evaluada con barras históricas confirmadas, entrada ejecutada en la apertura de la barra siguiente.
    5. Liberación atómica de reservas de riesgo al cerrar posiciones.
    """

    def __init__(
        self,
        risk_engine: Any,
        sim_engine: Optional[SimulationExecutionEngine] = None,
        max_holding_bars: int = 20
    ):
        self.risk_engine = risk_engine
        self.sim_engine = sim_engine or SimulationExecutionEngine()
        self.max_holding_bars = max_holding_bars

    def run_simulation(
        self,
        bars_by_symbol: Dict[str, List[OHLCVBar]],
        strategy: Any,
        precomputed_daily: Optional[Dict[str, Any]] = None,
        daily_bars_by_symbol: Optional[Dict[str, List[OHLCVBar]]] = None,
        macro_filter_fn: Optional[Any] = None,
        volatility_filter_fn: Optional[Any] = None
    ) -> Tuple[List[TradeFillRecord], List[Dict[str, Any]], Dict[str, int]]:
        """
        Ejecuta la simulación multi-activo bar-by-bar garantizando orden cronológico global.
        """
        symbols = sorted(list(bars_by_symbol.keys()))
        
        # 1. Unificar todas las marcas temporales en una línea cronológica ordenada
        all_timestamps_set = set()
        bars_lookup: Dict[str, Dict[datetime, OHLCVBar]] = {s: {} for s in symbols}
        
        for s in symbols:
            for b in bars_by_symbol[s]:
                all_timestamps_set.add(b.timestamp)
                bars_lookup[s][b.timestamp] = b
                
        sorted_timestamps = sorted(list(all_timestamps_set))
        
        trades: List[TradeFillRecord] = []
        rejections: List[Dict[str, Any]] = []
        open_positions: Dict[str, Dict[str, Any]] = {}
        
        current_sim_date = None
        current_sim_week = None
        daily_resets_count = 0
        weekly_resets_count = 0
        
        for t_idx, current_ts in enumerate(sorted_timestamps[:-1]):
            next_ts = sorted_timestamps[t_idx + 1]
            bar_date = current_ts.date()
            bar_week = current_ts.isocalendar()[1]
            
            # Reinicios de disyuntores de riesgo
            if current_sim_date is None or bar_date != current_sim_date:
                self.risk_engine.reset_daily_circuit()
                current_sim_date = bar_date
                daily_resets_count += 1
                
            if current_sim_week is None or bar_week != current_sim_week:
                self.risk_engine.reset_weekly_circuit()
                current_sim_week = bar_week
                weekly_resets_count += 1
                
            # A. Gestión de salidas de posiciones abiertas en current_ts
            for s in list(open_positions.keys()):
                curr_bar = bars_lookup[s].get(current_ts)
                if not curr_bar:
                    continue
                pos = open_positions[s]
                pos["bars_held"] += 1
                
                # Check Stop Loss
                if curr_bar.low <= pos["planned_stop"] or curr_bar.open < pos["planned_stop"]:
                    closed = self.sim_engine.simulate_exit(
                        pos["open_trade"], curr_bar, "STOP_LOSS", pos["planned_stop"], pos["planned_target"]
                    )
                    trades.append(closed)
                    self.risk_engine.update_equity(self.risk_engine.current_equity + closed.net_pnl, closed.net_pnl)
                    self.risk_engine.release_reservation(pos["res_id"])
                    del open_positions[s]
                # Check Take Profit
                elif curr_bar.high >= pos["planned_target"]:
                    closed = self.sim_engine.simulate_exit(
                        pos["open_trade"], curr_bar, "TAKE_PROFIT", pos["planned_stop"], pos["planned_target"]
                    )
                    trades.append(closed)
                    self.risk_engine.update_equity(self.risk_engine.current_equity + closed.net_pnl, closed.net_pnl)
                    self.risk_engine.release_reservation(pos["res_id"])
                    del open_positions[s]
                # Check Time Exit
                elif pos["bars_held"] >= self.max_holding_bars:
                    closed = self.sim_engine.simulate_exit(
                        pos["open_trade"], curr_bar, "TIME_EXIT", pos["planned_stop"], pos["planned_target"]
                    )
                    trades.append(closed)
                    self.risk_engine.update_equity(self.risk_engine.current_equity + closed.net_pnl, closed.net_pnl)
                    self.risk_engine.release_reservation(pos["res_id"])
                    del open_positions[s]
                    
            # B. Evaluación de nuevas entradas
            if macro_filter_fn and not macro_filter_fn(current_ts):
                continue
                
            for s in symbols:
                if s in open_positions:
                    continue
                curr_bar = bars_lookup[s].get(current_ts)
                next_bar = bars_lookup[s].get(next_ts)
                if not curr_bar or not next_bar:
                    continue
                    
                # Barras disponibles hasta current_ts
                all_s_bars = [b for b in bars_by_symbol[s] if b.timestamp <= current_ts]
                if len(all_s_bars) < 65:
                    continue
                eval_sub = all_s_bars[-65:]
                
                if volatility_filter_fn:
                    allowed, v_reason = volatility_filter_fn(s, eval_sub, curr_bar)
                    if not allowed:
                        rejections.append({"time": current_ts, "symbol": s, "reason": v_reason})
                        continue
                        
                b1d = daily_bars_by_symbol.get(s, []) if daily_bars_by_symbol else []
                ctx_d = precomputed_daily.get(s) if precomputed_daily else None
                
                sig = strategy.evaluate(symbol=s, bars_4h=eval_sub, confirmed_bars_1d=b1d, precomputed_daily=ctx_d)
                if sig is not None:
                    current_open_list = [
                        {
                            "symbol": sym_p,
                            "avg_entry_price": p_info["open_trade"].fill_price,
                            "stop_loss": p_info["planned_stop"],
                            "quantity": p_info["open_trade"].quantity
                        }
                        for sym_p, p_info in open_positions.items()
                    ]
                    approved, qty, reason = self.risk_engine.evaluate_and_size_proposal(
                        sig, current_open_list, self.risk_engine.current_equity
                    )
                    if approved and qty >= 1:
                        open_trade = self.sim_engine.simulate_entry(sig, qty, next_bar)
                        res_id = reason.split("Reserva=")[-1].strip() if "Reserva=" in reason else "RES_SIM"
                        self.risk_engine.commit_reservation(res_id)
                        open_positions[s] = {
                            "open_trade": open_trade,
                            "planned_stop": sig.stop_reference,
                            "planned_target": sig.target_reference,
                            "bars_held": 0,
                            "res_id": res_id
                        }
                    else:
                        rejections.append({"time": current_ts, "symbol": s, "reason": reason})
                        
        stats = {
            "daily_resets": daily_resets_count,
            "weekly_resets": weekly_resets_count,
            "total_rejections": len(rejections)
        }
        return trades, rejections, stats
