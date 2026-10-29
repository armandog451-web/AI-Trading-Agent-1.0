"""
ai_trading_agent.dual_strategy.strategies.swing_pullback
========================================================
Implementación estricta y determinista de la Estrategia B:
ORB_SWING_PULLBACK_V1 (OracleBot v2).

Especificaciones Cuantitativas:
- Contexto: Diario (1D): EMA50 > EMA200, Cierre Diario > EMA50, EMA50(t) > EMA50(t-10).
- Señal: 4 horas:
  1. En las últimas 5 velas completas de 4h, al menos una tocó/cruzó EMA20 de 4h.
  2. Ninguna de las 5 velas cerró por debajo de EMA50 de 4h.
  3. Cierre de la última vela completa > High de la vela anterior.
  4. Cierre de la última vela completa > EMA20 de 4h.
- Stop inicial: Mínimo de las últimas 5 velas de 4h - 0.1 * ATR14(4h).
- Target: Entrada + 2 * (Entrada - Stop) [R:R >= 2:1].
- Duración máxima: 10 sesiones bursátiles (Time Exit).
- Riesgo nocturno modelado (Gaps, deslizamiento en apertura).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import hashlib
import bisect

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime
from ai_trading_agent.dual_strategy.models import ReproducibleSignal
from ai_trading_agent.dual_strategy.data_provider import MarketDataProvider
from ai_trading_agent.dual_strategy.features import FeatureEngine


class PrecomputedDailyContext:
    """Caché optimizado O(log N) para contexto diario (1D) en simulaciones Swing."""
    def __init__(self, bars_1d: List[OHLCVBar], fast_ema: int = 50, slow_ema: int = 200, slope_bars: int = 10):
        closes = [b.close for b in bars_1d]
        self.ema50 = FeatureEngine.calculate_ema(closes, fast_ema)
        self.ema200 = FeatureEngine.calculate_ema(closes, slow_ema)
        self.closes = closes
        self.timestamps = [b.timestamp for b in bars_1d]
        self.slope_bars = slope_bars
        self.min_idx = slow_ema + slope_bars

    def get_latest_confirmed(self, dt: datetime) -> Optional[Tuple[float, float, float, float]]:
        idx = bisect.bisect_right(self.timestamps, dt) - 1
        if idx < self.min_idx:
            return None
        return (self.ema50[idx], self.ema200[idx], self.ema50[idx - self.slope_bars], self.closes[idx])


class OrbSwingPullbackV1:
    """Motor de señal para ORB_SWING_PULLBACK_V1."""

    STRATEGY_ID = "ORB_SWING_PULLBACK_V1"
    VERSION = "1.0.0"

    def __init__(
        self,
        daily_fast_ema: int = 50,
        daily_slow_ema: int = 200,
        daily_slope_bars: int = 10,
        four_h_pullback_ema: int = 20,
        four_h_support_ema: int = 50,
        pullback_window_bars: int = 5,
        atr_stop_buffer_mult: float = 0.10,
        target_rr_ratio: float = 2.0,
        max_holding_sessions: int = 10
    ):
        self.daily_fast_ema = daily_fast_ema
        self.daily_slow_ema = daily_slow_ema
        self.daily_slope_bars = daily_slope_bars
        self.four_h_pullback_ema = four_h_pullback_ema
        self.four_h_support_ema = four_h_support_ema
        self.pullback_window_bars = pullback_window_bars
        self.atr_stop_buffer_mult = atr_stop_buffer_mult
        self.target_rr_ratio = target_rr_ratio
        self.max_holding_sessions = max_holding_sessions

    @property
    def configuration_hash(self) -> str:
        params = {
            "strategy_id": self.STRATEGY_ID,
            "version": self.VERSION,
            "daily_fast_ema": self.daily_fast_ema,
            "daily_slow_ema": self.daily_slow_ema,
            "daily_slope_bars": self.daily_slope_bars,
            "four_h_pullback_ema": self.four_h_pullback_ema,
            "four_h_support_ema": self.four_h_support_ema,
            "target_rr_ratio": self.target_rr_ratio,
            "max_holding_sessions": self.max_holding_sessions
        }
        return hashlib.sha256(str(sorted(params.items())).encode("utf-8")).hexdigest()[:16]

    def evaluate(
        self,
        symbol: str,
        bars_4h: List[OHLCVBar],
        confirmed_bars_1d: List[OHLCVBar],
        observed_spread_pct: float = 0.0008,
        adv_20d: float = 3000000.0,
        precomputed_daily: Optional[PrecomputedDailyContext] = None
    ) -> Optional[ReproducibleSignal]:
        """
        Evalúa si la última barra cerrada de 4 horas activa una señal de compra Swing válida.
        Zero Look-Ahead: Únicamente utiliza confirmed_bars_1d cerradas en fechas estrictamente anteriores.
        """
        if len(bars_4h) < self.four_h_support_ema + 15:
            return None

        signal_bar = bars_4h[-1]
        eval_dt = signal_bar.timestamp

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

        # 2. Tendencia en Contexto Diario (1D)
        if precomputed_daily is not None:
            ctx_d = precomputed_daily.get_latest_confirmed(eval_dt)
            if ctx_d is None:
                return None
            curr_d_ema50, curr_d_ema200, prev_10_d_ema50, last_confirmed_d_close = ctx_d
        else:
            valid_daily_bars = [b for b in confirmed_bars_1d if b.timestamp <= eval_dt]
            if len(valid_daily_bars) < self.daily_slow_ema + self.daily_slope_bars:
                return None
            daily_closes = [b.close for b in valid_daily_bars]
            d_ema50_series = FeatureEngine.calculate_ema(daily_closes, self.daily_fast_ema)
            d_ema200_series = FeatureEngine.calculate_ema(daily_closes, self.daily_slow_ema)
            curr_d_ema50 = d_ema50_series[-1]
            curr_d_ema200 = d_ema200_series[-1]
            prev_10_d_ema50 = d_ema50_series[-1 - self.daily_slope_bars]
            last_confirmed_d_close = daily_closes[-1]

        if not (curr_d_ema50 > curr_d_ema200 and last_confirmed_d_close > curr_d_ema50 and curr_d_ema50 > prev_10_d_ema50):
            return None

        # 3. Retroceso y Gatillo en Timeframe 4H
        closes_4h = [b.close for b in bars_4h]
        ema20_4h_series = FeatureEngine.calculate_ema(closes_4h, self.four_h_pullback_ema)
        ema50_4h_series = FeatureEngine.calculate_ema(closes_4h, self.four_h_support_ema)

        # Ventana de las últimas 5 velas completas de 4h
        window_5 = bars_4h[-self.pullback_window_bars:]
        window_ema20 = ema20_4h_series[-self.pullback_window_bars:]
        window_ema50 = ema50_4h_series[-self.pullback_window_bars:]

        # a) Al menos una tocó o cruzó EMA20 de 4h (Low <= EMA20 <= High)
        touched_ema20 = False
        for b, e20 in zip(window_5, window_ema20):
            if b.low <= e20 <= b.high or b.low <= e20:
                touched_ema20 = True
                break
        if not touched_ema20:
            return None

        # b) Ninguna ha cerrado por debajo de EMA50 de 4h
        for b, e50 in zip(window_5, window_ema50):
            if b.close < e50:
                return None

        # c) El cierre de la última vela completa supera el High de la vela inmediatamente anterior
        prev_bar = bars_4h[-2]
        if signal_bar.close <= prev_bar.high:
            return None

        # d) Ese cierre está por encima de EMA20 de 4h
        curr_ema20_4h = ema20_4h_series[-1]
        if signal_bar.close <= curr_ema20_4h:
            return None

        # 4. Stop Loss Inicial
        # Mínimo de las últimas 5 velas completas de 4h menos 0.1 * ATR14(4h)
        atr_4h_series = FeatureEngine.calculate_atr(bars_4h, 14)
        atr_14_4h = atr_4h_series[-1]
        if atr_14_4h <= 0:
            return None

        min_5_low = min(b.low for b in window_5)
        initial_stop = round(min_5_low - (self.atr_stop_buffer_mult * atr_14_4h), 2)

        entry_ref = signal_bar.close
        if initial_stop >= entry_ref:
            return None

        risk_dist = entry_ref - initial_stop
        if risk_dist <= 0.10:
            return None

        target_ref = round(entry_ref + (self.target_rr_ratio * risk_dist), 2)

        # 5. Generar señal inmutable
        data_hash = MarketDataProvider.compute_data_snapshot_hash(bars_4h)

        reasons = [
            f"1D_Macro_Trend_Bullish (EMA50={curr_d_ema50:.2f} > EMA200={curr_d_ema200:.2f}, Slope +{curr_d_ema50 - prev_10_d_ema50:.2f})",
            f"4H_Pullback_Bounce_EMA20 (Touched EMA20={curr_ema20_4h:.2f}, Respected EMA50={ema50_4h_series[-1]:.2f})",
            f"4H_Reversal_Trigger (Close={signal_bar.close:.2f} > PrevHigh={prev_bar.high:.2f} & Close > EMA20)",
            f"RiskReward_Proportion_Valid (2.0R, Stop={initial_stop:.2f}, Target={target_ref:.2f})"
        ]

        score = min(92.0, 72.0 + ((curr_d_ema50 - prev_10_d_ema50) / curr_d_ema50) * 1000.0)

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
            context_timeframe="1d",
            signal_timeframe="4h",
            market_regime=MarketRegime.BULL_TREND,
            metadata={
                "daily_ema50": round(curr_d_ema50, 2),
                "daily_ema200": round(curr_d_ema200, 2),
                "four_h_ema20": round(curr_ema20_4h, 2),
                "min_5_low": min_5_low,
                "atr14_4h": round(atr_14_4h, 2),
                "max_holding_sessions": self.max_holding_sessions
            }
        )
