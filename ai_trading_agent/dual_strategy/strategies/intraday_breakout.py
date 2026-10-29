"""
ai_trading_agent.dual_strategy.strategies.intraday_breakout
===========================================================
Implementación estricta y determinista de la Estrategia A:
ORB_INTRADAY_BREAKOUT_V1 (OracleBot v2).

Especificaciones Cuantitativas:
- Contexto: 1 hora (EMA20 > EMA50 y último cierre 1H > EMA20).
- Señal: 15 minutos (Ruptura de Donchian High 20p con RVOL >= 1.5, cuerpo >= 50% y cierre top 25%).
- Ventana operativa: 10:00 a 15:00 America/New_York (sesión regular).
- Stop inicial: Mínimo 5 velas de 15m - 0.1 * ATR14.
- Target: Entrada + 2 * (Entrada - Stop) [R:R >= 2:1].
- Salida forzosa: 15:50 ET (Square-off intradía absoluto).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, time, date
import hashlib
import math
import bisect
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.dual_strategy.models import ReproducibleSignal
from ai_trading_agent.dual_strategy.data_provider import MarketDataProvider
from ai_trading_agent.dual_strategy.features import FeatureEngine


class Precomputed1HContext:
    """Caché optimizado O(log N) para contexto de 1H en simulaciones."""
    def __init__(self, bars_1h: List[OHLCVBar]):
        closes = [b.close for b in bars_1h]
        self.ema20 = FeatureEngine.calculate_ema(closes, 20)
        self.ema50 = FeatureEngine.calculate_ema(closes, 50)
        self.closes = closes
        self.timestamps = [b.timestamp for b in bars_1h]

    def get_latest_confirmed(self, dt: datetime) -> Optional[Tuple[float, float, float]]:
        idx = bisect.bisect_right(self.timestamps, dt) - 1
        if idx < 50:
            return None
        return (self.ema20[idx], self.ema50[idx], self.closes[idx])


class OrbIntradayBreakoutV1:
    """Motor de señal para ORB_INTRADAY_BREAKOUT_V1."""

    STRATEGY_ID = "ORB_INTRADAY_BREAKOUT_V1"
    VERSION = "1.0.0"

    def __init__(
        self,
        donchian_period: int = 20,
        rvol_threshold: float = 1.5,
        min_body_ratio: float = 0.50,
        min_close_loc: float = 0.75,
        atr_stop_buffer_mult: float = 0.10,
        target_rr_ratio: float = 2.0,
        max_daily_entries_per_symbol: int = 2,
        max_daily_portfolio_entries: int = 4
    ):
        self.donchian_period = donchian_period
        self.rvol_threshold = rvol_threshold
        self.min_body_ratio = min_body_ratio
        self.min_close_loc = min_close_loc
        self.atr_stop_buffer_mult = atr_stop_buffer_mult
        self.target_rr_ratio = target_rr_ratio
        self.max_daily_entries_per_symbol = max_daily_entries_per_symbol
        self.max_daily_portfolio_entries = max_daily_portfolio_entries

        # Seguimiento de ejecuciones por día y símbolo
        self._daily_symbol_entries: Dict[str, int] = {}
        self._daily_total_entries: int = 0
        self._current_tracking_date: Optional[date] = None

    @property
    def configuration_hash(self) -> str:
        params = {
            "strategy_id": self.STRATEGY_ID,
            "version": self.VERSION,
            "donchian_period": self.donchian_period,
            "rvol_threshold": self.rvol_threshold,
            "min_body_ratio": self.min_body_ratio,
            "min_close_loc": self.min_close_loc,
            "atr_stop_buffer_mult": self.atr_stop_buffer_mult,
            "target_rr_ratio": self.target_rr_ratio
        }
        return hashlib.sha256(json_str := str(sorted(params.items())).encode("utf-8")).hexdigest()[:16]

    def reset_daily_counters_if_new_day(self, current_date: date):
        if self._current_tracking_date != current_date:
            self._current_tracking_date = current_date
            self._daily_symbol_entries.clear()
            self._daily_total_entries = 0

    def evaluate(
        self,
        symbol: str,
        bars_15m: List[OHLCVBar],
        confirmed_bars_1h: List[OHLCVBar],
        observed_spread_pct: float = 0.0005,
        adv_20d: float = 2500000.0,
        current_daily_entries_count: int = 0,
        precomputed_1h: Optional[Precomputed1HContext] = None
    ) -> Optional[ReproducibleSignal]:
        """
        Evalúa si la última barra cerrada de 15m genera una señal de compra válida.
        Zero Look-Ahead: Solo accede a confirmed_bars_1h cerradas estrictamente antes de bars_15m[-1].timestamp.
        """
        if len(bars_15m) < self.donchian_period + 6:
            return None

        signal_bar = bars_15m[-1]
        eval_dt = signal_bar.timestamp
        self.reset_daily_counters_if_new_day(eval_dt.date())

        # 0. Verificación de ventana operativa intradía (10:00 - 15:00 ET)
        if not MarketDataProvider.is_regular_intraday_window(eval_dt):
            return None

        # 1. Filtros de admisibilidad de universo
        provider = MarketDataProvider()
        is_valid_universe, rej_reasons = provider.validate_universe_filters(
            symbol=symbol,
            current_price=signal_bar.close,
            adv_20d=adv_20d,
            observed_spread_pct=observed_spread_pct
        )
        if not is_valid_universe:
            return None

        # 2. Control de frecuencia
        sym_entries = self._daily_symbol_entries.get(symbol, 0)
        if sym_entries >= self.max_daily_entries_per_symbol:
            return None
        if self._daily_total_entries >= self.max_daily_portfolio_entries:
            return None

        # 3. Tendencia en Contexto 1H (Barras cerradas exclusivamente)
        if precomputed_1h is not None:
            ctx_1h = precomputed_1h.get_latest_confirmed(eval_dt)
            if ctx_1h is None:
                return None
            ema20_1h, ema50_1h, last_confirmed_1h_close = ctx_1h
        else:
            valid_1h_bars = [b for b in confirmed_bars_1h if b.timestamp <= eval_dt]
            if len(valid_1h_bars) < 51:
                return None
            close_1h_prices = [b.close for b in valid_1h_bars]
            ema20_1h = FeatureEngine.calculate_ema(close_1h_prices, 20)[-1]
            ema50_1h = FeatureEngine.calculate_ema(close_1h_prices, 50)[-1]
            last_confirmed_1h_close = close_1h_prices[-1]

        if not (ema20_1h > ema50_1h and last_confirmed_1h_close > ema20_1h):
            return None

        # 4. Condiciones de Ruptura en 15m
        prior_20_high = FeatureEngine.calculate_donchian_high_previous(bars_15m, self.donchian_period)
        if signal_bar.close <= prior_20_high:
            return None

        # Volumen de señal >= 1.5 * media de volumen de las 20 velas anteriores
        vol_sma_20 = FeatureEngine.calculate_volume_sma_previous(bars_15m, self.donchian_period)
        if vol_sma_20 <= 0 or (signal_bar.volume < self.rvol_threshold * vol_sma_20):
            return None

        # Geometría de la vela (cuerpo >= 50%, cierre en 25% superior)
        geom = FeatureEngine.extract_candle_geometry(signal_bar)
        if geom["body_ratio"] < self.min_body_ratio or geom["close_location"] < self.min_close_loc:
            return None

        # 5. Stop Loss Inicial
        # Mínimo de las últimas 5 velas de 15m (incluyendo señal) - 0.1 * ATR14
        atr_15m_series = FeatureEngine.calculate_atr(bars_15m, 14)
        atr_14 = atr_15m_series[-1]
        if np.isnan(atr_14) or atr_14 <= 0:
            return None

        recent_5_bars = bars_15m[-5:]
        min_5_low = min(b.low for b in recent_5_bars)
        initial_stop = round(min_5_low - (self.atr_stop_buffer_mult * atr_14), 2)

        entry_ref = signal_bar.close
        if initial_stop >= entry_ref:
            return None

        risk_dist = entry_ref - initial_stop
        if risk_dist <= 0.05:  # Prevenir divisiones por cero o paradas irrealistamente ceñidas
            return None

        target_ref = round(entry_ref + (self.target_rr_ratio * risk_dist), 2)

        # 6. Construcción inmutable de la señal reproducible
        data_hash = MarketDataProvider.compute_data_snapshot_hash(bars_15m)

        reasons = [
            f"1H_Trend_Aligned (EMA20={ema20_1h:.2f} > EMA50={ema50_1h:.2f})",
            f"15M_Breakout_Above_20High ({signal_bar.close:.2f} > {prior_20_high:.2f})",
            f"RVOL_Confirmed ({signal_bar.volume/vol_sma_20:.2f}x >= {self.rvol_threshold}x)",
            f"Candle_Geometry_Valid (Body={geom['body_ratio']*100:.1f}%, CloseLoc={geom['close_location']*100:.1f}%)",
            f"RiskReward_Proportion_Valid (2.0R, Stop={initial_stop:.2f}, Target={target_ref:.2f})"
        ]

        # Calcular score normalizado (0 a 100)
        score = min(95.0, 70.0 + (signal_bar.volume / vol_sma_20) * 8.0 + geom["close_location"] * 10.0)

        return ReproducibleSignal(
            strategy_id=self.STRATEGY_ID,
            version=self.VERSION,
            configuration_hash=self.configuration_hash,
            symbol=symbol,
            market_timestamp=eval_dt,
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=entry_ref,
            stop_reference=initial_stop,
            target_reference=target_ref,
            estimated_risk=round(risk_dist, 2),
            reason_codes=reasons,
            data_snapshot_hash=data_hash,
            score=round(score, 1),
            context_timeframe="1h",
            signal_timeframe="15m",
            market_regime=MarketRegime.BULL_TREND,
            metadata={
                "prior_20_high": prior_20_high,
                "vol_ratio": round(signal_bar.volume / vol_sma_20, 2),
                "atr14": round(atr_14, 2),
                "geom": geom
            }
        )

    def record_entry_executed(self, symbol: str):
        self._daily_symbol_entries[symbol] = self._daily_symbol_entries.get(symbol, 0) + 1
        self._daily_total_entries += 1
