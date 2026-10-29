"""
ai_trading_agent.dual_strategy.risk
===================================
Motor de Riesgo de Cartera Compartido y Dimensionamiento Determinista (OracleBot v2).
Gobierna conjuntamente las estrategias ORB_INTRADAY_BREAKOUT_V1 y ORB_SWING_PULLBACK_V1.
Garantiza aislamiento estricto de D21, límites agregados infranqueables y prevención de condiciones de carrera.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import math
import threading
import logging

from ai_trading_agent.domain.models import Position
from ai_trading_agent.dual_strategy.models import (
    ReproducibleSignal, RiskReservation, TradeFillRecord
)
from ai_trading_agent.dual_strategy.data_provider import MarketDataProvider

logger = logging.getLogger(__name__)


class PortfolioRiskEngine:
    """
    Motor centralizado de gobernanza de riesgo multi-estrategia.
    Aplica controles sobre el equity total consolidado.
    """

    def __init__(
        self,
        reference_equity: float = 1000000.0,
        risk_per_trade_pct: float = 0.0025,        # 0.25% ($2,500 en $1M)
        max_aggregate_open_risk_pct: float = 0.0050, # 0.50% ($5,000 en $1M)
        max_stock_notional_pct: float = 0.05,       # 5.0% ($50,000 en $1M)
        max_sector_notional_pct: float = 0.20,      # 20.0% ($200,000 en $1M)
        daily_loss_limit_r: float = 2.0,            # 2R ($5,000)
        weekly_loss_limit_r: float = 5.0,           # 5R ($12,500)
        max_campaign_drawdown_pct: float = 0.05,    # 5.0% Drawdown
        conservative_cost_buffer_per_share: float = 0.05  # $0.05/acc buffer deslizamiento/comisión
    ):
        self.reference_equity = reference_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_aggregate_open_risk_pct = max_aggregate_open_risk_pct
        self.max_stock_notional_pct = max_stock_notional_pct
        self.max_sector_notional_pct = max_sector_notional_pct
        self.daily_loss_limit_r = daily_loss_limit_r
        self.weekly_loss_limit_r = weekly_loss_limit_r
        self.max_campaign_drawdown_pct = max_campaign_drawdown_pct
        self.conservative_cost_buffer_per_share = conservative_cost_buffer_per_share

        # R de referencia fijada al inicio de sesión ($2,500 para $1M)
        self.session_r_usd = self.reference_equity * self.risk_per_trade_pct

        # Estado del circuito de protección
        self.is_trading_halted: bool = False
        self.halt_reason: str = ""
        self.incident_log: List[Dict[str, Any]] = []

        # Registro centralizado de reservas de riesgo activas (evita race conditions)
        self._reservations: Dict[str, RiskReservation] = {}
        self._lock = threading.Lock()

        # Métricas de pérdidas
        self.daily_realized_pnl: float = 0.0
        self.weekly_realized_pnl: float = 0.0
        self.peak_equity: float = self.reference_equity
        self.current_equity: float = self.reference_equity

        self.data_provider = MarketDataProvider()

    def update_equity(self, current_equity: float, realized_pnl_delta: float = 0.0):
        with self._lock:
            self.current_equity = current_equity
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
            self.daily_realized_pnl += realized_pnl_delta
            self.weekly_realized_pnl += realized_pnl_delta

            # Verificar Drawdown de campaña
            dd_pct = (self.peak_equity - self.current_equity) / self.peak_equity
            if dd_pct >= self.max_campaign_drawdown_pct:
                self._trigger_halt(f"Drawdown de campaña {dd_pct*100:.2f}% superó el límite de {self.max_campaign_drawdown_pct*100:.2f}%")

            # Verificar pérdida diaria (2R)
            if self.daily_realized_pnl <= -(self.daily_loss_limit_r * self.session_r_usd):
                self._trigger_halt(f"Pérdida diaria acumulada ${abs(self.daily_realized_pnl):,.2f} superó límite de {self.daily_loss_limit_r}R (${self.daily_loss_limit_r * self.session_r_usd:,.2f})")

            # Verificar pérdida semanal (5R)
            if self.weekly_realized_pnl <= -(self.weekly_loss_limit_r * self.session_r_usd):
                self._trigger_halt(f"Pérdida semanal acumulada ${abs(self.weekly_realized_pnl):,.2f} superó límite de {self.weekly_loss_limit_r}R (${self.weekly_loss_limit_r * self.session_r_usd:,.2f})")

    def _trigger_halt(self, reason: str):
        self.is_trading_halted = True
        self.halt_reason = reason
        incident = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "CIRCUIT_BREAKER_TRIGGERED",
            "reason": reason,
            "daily_pnl": self.daily_realized_pnl,
            "weekly_pnl": self.weekly_realized_pnl,
            "current_equity": self.current_equity
        }
        self.incident_log.append(incident)
        logger.critical(f"SEGURIDAD ACTIVADA: {reason}. Todas las nuevas entradas quedan bloqueadas.")

    def reset_daily_circuit(self):
        with self._lock:
            self.daily_realized_pnl = 0.0
            if "Pérdida diaria" in self.halt_reason:
                self.is_trading_halted = False
                self.halt_reason = ""

    def reset_weekly_circuit(self):
        with self._lock:
            self.weekly_realized_pnl = 0.0
            if "Pérdida semanal" in self.halt_reason:
                self.is_trading_halted = False
                self.halt_reason = ""

    def evaluate_and_size_proposal(
        self,
        signal: ReproducibleSignal,
        open_positions: List[Dict[str, Any]],
        available_cash: float,
        adv_20d: float = 2500000.0,
        unreconciled_orders_exist: bool = False
    ) -> Tuple[bool, int, str]:
        """
        Calcula el tamaño determinista de la posición y verifica los 6 filtros de riesgo compartido.
        Devuelve (aprobado: bool, cantidad: int, motivo: str).
        """
        with self._lock:
            # 1. Chequeo de Halt de Emergencia
            if self.is_trading_halted:
                return (False, 0, f"Trading bloqueado por circuito de protección: {self.halt_reason}")

            # 2. Chequeo de inconsistencias y órdenes no reconciliadas
            if unreconciled_orders_exist:
                return (False, 0, "Rechazado: Existen órdenes pendientes sin reconciliar en cartera")

            sym = signal.symbol.upper()
            sector = self.data_provider.get_sector(sym)

            # 3. Resolución de Conflictos entre Estrategias: No permitir entradas concurrentes en el mismo activo
            for pos in open_positions:
                if pos.get("symbol", "").upper() == sym:
                    return (False, 0, f"Conflicto de cartera: Ya existe una posición abierta en {sym}")

            # Chequear reservas activas pendientes de asignación
            for res_id, res in self._reservations.items():
                if res.status == "ACTIVE" and res.symbol.upper() == sym:
                    return (False, 0, f"Conflicto de concurrencia: Existe una reserva activa en curso para {sym}")

            # 4. Cálculo de Riesgo Unitario Estimado
            dist_stop = abs(signal.entry_reference - signal.stop_reference)
            if dist_stop <= 0.01:
                return (False, 0, "Distancia de stop loss inválida o nula")

            unit_risk_est = dist_stop + self.conservative_cost_buffer_per_share
            risk_budget = self.reference_equity * self.risk_per_trade_pct  # $2,500 en $1M

            # Cantidad por riesgo: floor(presupuesto / riesgo_unitario)
            qty_risk = math.floor(risk_budget / unit_risk_est)
            if qty_risk < 1:
                return (False, 0, f"Riesgo unitario ${unit_risk_est:.2f} excede presupuesto de riesgo ${risk_budget:.2f}")

            # 5. Límite de exposición nocional por acción (5.0% de equity)
            max_notional_stock = self.reference_equity * self.max_stock_notional_pct  # $50,000 en $1M
            qty_stock_limit = math.floor(max_notional_stock / signal.entry_reference)

            # 6. Límite de exposición sectorial (20.0% de equity)
            current_sector_notional = sum(
                p.get("quantity", 0) * p.get("current_price", p.get("avg_entry_price", 0.0))
                for p in open_positions
                if self.data_provider.get_sector(p.get("symbol", "")) == sector
            )
            # Sumar reservas activas del sector
            sector_reserved_notional = sum(
                r.reserved_notional_usd for r in self._reservations.values()
                if r.status == "ACTIVE" and r.sector == sector
            )
            max_sector_notional = self.reference_equity * self.max_sector_notional_pct  # $200,000 en $1M
            remaining_sector_notional = max(0.0, max_sector_notional - current_sector_notional - sector_reserved_notional)
            qty_sector_limit = math.floor(remaining_sector_notional / signal.entry_reference)

            # 7. Límite por liquidez (máximo 1.0% del volumen medio diario en la entrada)
            qty_liquidity = math.floor(adv_20d * 0.01)

            # 8. Límite por efectivo disponible
            qty_cash = math.floor(available_cash / signal.entry_reference)

            # Cantidad final: mínimo entre todos los límites deterministas
            qty_final = min(qty_risk, qty_stock_limit, qty_sector_limit, qty_liquidity, qty_cash)

            if qty_final < 1:
                return (False, 0, f"Cantidad final permitida ({qty_final}) < 1 acc tras aplicar límites nocionales y sectoriales")

            # 9. Verificación de Riesgo Abierto Agregado (0.50% de equity = $5,000)
            current_open_risk = sum(
                abs(p.get("avg_entry_price", 0.0) - p.get("stop_loss", 0.0)) * p.get("quantity", 0)
                for p in open_positions
            )
            reserved_open_risk = sum(
                r.reserved_risk_usd for r in self._reservations.values() if r.status == "ACTIVE"
            )
            new_proposal_risk = qty_final * unit_risk_est
            max_allowed_aggregate_risk = self.reference_equity * self.max_aggregate_open_risk_pct

            if (current_open_risk + reserved_open_risk + new_proposal_risk) > max_allowed_aggregate_risk:
                return (False, 0, f"Riesgo agregado propuesto ${current_open_risk + reserved_open_risk + new_proposal_risk:,.2f} superaría el límite de 0.50% (${max_allowed_aggregate_risk:,.2f})")

            # Registrar reserva central de riesgo
            res_id = f"RES_{signal.strategy_id}_{sym}_{int(datetime.utcnow().timestamp())}"
            reservation = RiskReservation(
                reservation_id=res_id,
                strategy_id=signal.strategy_id,
                symbol=sym,
                sector=sector,
                reserved_risk_usd=round(new_proposal_risk, 2),
                reserved_notional_usd=round(qty_final * signal.entry_reference, 2),
                timestamp=datetime.utcnow(),
                status="ACTIVE"
            )
            self._reservations[res_id] = reservation

            return (True, qty_final, f"Aprobado: Qty={qty_final} acc | Riesgo=${new_proposal_risk:.2f} | Notional=${qty_final * signal.entry_reference:.2f} | Reserva={res_id}")

    def commit_reservation(self, reservation_id: str):
        with self._lock:
            if reservation_id in self._reservations:
                res = self._reservations[reservation_id]
                self._reservations[reservation_id] = RiskReservation(
                    reservation_id=res.reservation_id,
                    strategy_id=res.strategy_id,
                    symbol=res.symbol,
                    sector=res.sector,
                    reserved_risk_usd=res.reserved_risk_usd,
                    reserved_notional_usd=res.reserved_notional_usd,
                    timestamp=res.timestamp,
                    status="COMMITTED"
                )

    def release_reservation(self, reservation_id: str):
        with self._lock:
            if reservation_id in self._reservations:
                self._reservations.pop(reservation_id, None)
