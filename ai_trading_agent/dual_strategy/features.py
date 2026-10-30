"""
ai_trading_agent.dual_strategy.features
=======================================
Motor de características técnicas e indicadores deterministas para OracleBot v2.
Calcula EMA, ATR, Donchian High, RVOL y métricas geométricas de velas (Closed-Bar Only).
"""

from typing import List, Dict, Any, Optional
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar


class FeatureEngine:
    """Motor matemático de indicadores sin sesgo de anticipación."""

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calcula Exponential Moving Average con suavizado estándar 2 / (period + 1)."""
        if len(prices) < period:
            return [float("nan")] * len(prices)

        multiplier = 2.0 / (period + 1.0)
        ema_values: List[float] = [float("nan")] * len(prices)

        # Semilla con SMA inicial
        sma_seed = sum(prices[:period]) / period
        ema_values[period - 1] = sma_seed

        curr_ema = sma_seed
        for i in range(period, len(prices)):
            curr_ema = (prices[i] - curr_ema) * multiplier + curr_ema
            ema_values[i] = curr_ema

        return ema_values

    @staticmethod
    def calculate_atr(bars: List[OHLCVBar], period: int = 14) -> List[float]:
        """Calcula Average True Range (Wilder / EMA smoothing)."""
        if len(bars) < period + 1:
            return [float("nan")] * len(bars)

        tr_values: List[float] = [bars[0].high - bars[0].low]
        for i in range(1, len(bars)):
            h_l = bars[i].high - bars[i].low
            h_cp = abs(bars[i].high - bars[i - 1].close)
            l_cp = abs(bars[i].low - bars[i - 1].close)
            tr = max(h_l, h_cp, l_cp)
            tr_values.append(tr)

        atr_values: List[float] = [float("nan")] * len(bars)
        initial_atr = sum(tr_values[:period]) / period
        atr_values[period - 1] = initial_atr

        curr_atr = initial_atr
        for i in range(period, len(bars)):
            curr_atr = (curr_atr * (period - 1) + tr_values[i]) / period
            atr_values[i] = curr_atr

        return atr_values

    @staticmethod
    def calculate_donchian_high_previous(bars: List[OHLCVBar], period: int = 20) -> float:
        """
        Calcula el máximo de las 20 velas anteriores, EXCLUYENDO estrictamente la vela de señal actual.
        Zero Look-Ahead Bias.
        """
        if len(bars) < period + 1:
            return float("nan")
        # Excluir la última barra (barra de señal en evaluación)
        window = bars[-(period + 1):-1]
        return max(b.high for b in window)

    @staticmethod
    def calculate_volume_sma_previous(bars: List[OHLCVBar], period: int = 20) -> float:
        """Calcula la media del volumen de las 20 velas anteriores, excluyendo la actual."""
        if len(bars) < period + 1:
            return float("nan")
        window = bars[-(period + 1):-1]
        return sum(b.volume for b in window) / period

    @staticmethod
    def extract_candle_geometry(bar: OHLCVBar) -> Dict[str, float]:
        """
        Calcula proporciones geométricas de la vela:
        - candle_range: high - low
        - body_size: |close - open|
        - body_ratio: body_size / candle_range (debe ser >= 0.50 para breakout)
        - close_location: (close - low) / candle_range (debe ser >= 0.75 para top 25%)
        """
        c_range = max(0.001, bar.high - bar.low)
        body = abs(bar.close - bar.open)
        body_ratio = body / c_range
        close_loc = (bar.close - bar.low) / c_range

        return {
            "range": round(c_range, 4),
            "body": round(body, 4),
            "body_ratio": round(body_ratio, 4),
            "close_location": round(close_loc, 4),
            "is_bullish_close": bar.close > bar.open
        }
