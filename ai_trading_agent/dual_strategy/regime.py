"""
ai_trading_agent.dual_strategy.regime
=====================================
Detector Determinista de Régimen de Mercado V1 (OracleBot v2 - Fase 6 Etapa 1).
Clasifica de forma desacoplada y sin sesgo de anticipación los regímenes de mercado:
- TRENDING_BULL: ADX(14) >= 25, ER(20) >= 0.35 y Precio > SMA(50)
- RANGING: ADX(14) < 20 y ER(20) < 0.25
- INDETERMINATE: Cualquier otra combinación o datos insuficientes/inválidos

Módulo puramente analítico y defensivo. NO GENERA ÓRDENES.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
import math
import numpy as np
from pydantic import BaseModel, Field

from ai_trading_agent.domain.models import OHLCVBar


class MarketRegimeV1(str, Enum):
    TRENDING_BULL = "TRENDING_BULL"
    RANGING = "RANGING"
    INDETERMINATE = "INDETERMINATE"


class RegimeEvaluationRecord(BaseModel):
    """Registro inmutable de la evaluación de régimen."""
    symbol: str
    bar_timestamp: datetime
    evaluation_timestamp: datetime
    regime: MarketRegimeV1
    adx_14: float
    er_20: float
    sma_50: float
    close_price: float
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)


class RegimeFeatureCalculator:
    """Cálculos matemáticos deterministas de indicadores de régimen con cero look-ahead."""

    @staticmethod
    def calculate_efficiency_ratio(prices: List[float], period: int = 20) -> List[float]:
        """
        Calcula el Efficiency Ratio (ER) de Perry Kaufman.
        ER = |Close_t - Close_{t-period}| / Sum_{i=0}^{period-1} |Close_{t-i} - Close_{t-i-1}|
        Rango estricto: [0.0, 1.0].
        1.0 = Movimiento en línea recta sin ruido (tendencia pura).
        0.0 = Máximo ruido / consolidación caótica sin desplazamiento neto.
        """
        n = len(prices)
        if n < period + 1:
            return [float("nan")] * n

        er_values: List[float] = [float("nan")] * n

        for i in range(period, n):
            direction = abs(prices[i] - prices[i - period])
            volatility = sum(abs(prices[j] - prices[j - 1]) for j in range(i - period + 1, i + 1))
            if volatility > 1e-9:
                er = direction / volatility
                # Acotar por estabilidad numérica
                er_values[i] = round(min(1.0, max(0.0, er)), 4)
            else:
                er_values[i] = 0.0

        return er_values

    @staticmethod
    def calculate_sma(prices: List[float], period: int = 50) -> List[float]:
        """Calcula Media Móvil Simple (SMA) de N períodos."""
        n = len(prices)
        if n < period:
            return [float("nan")] * n

        sma_values: List[float] = [float("nan")] * n
        curr_sum = sum(prices[:period])
        sma_values[period - 1] = round(curr_sum / period, 4)

        for i in range(period, n):
            curr_sum += prices[i] - prices[i - period]
            sma_values[i] = round(curr_sum / period, 4)

        return sma_values

    @staticmethod
    def calculate_adx(bars: List[OHLCVBar], period: int = 14) -> List[float]:
        """
        Calcula Average Directional Index (ADX) con el suavizado canónico de J. Welles Wilder.
        Requiere al menos 2 * period barras para producir el primer valor válido.
        """
        n = len(bars)
        min_required = 2 * period
        if n < min_required:
            return [float("nan")] * n

        tr_list = []
        plus_dm_list = []
        minus_dm_list = []

        for i in range(1, n):
            h = bars[i].high
            l = bars[i].low
            prev_c = bars[i - 1].close
            prev_h = bars[i - 1].high
            prev_l = bars[i - 1].low

            # True Range
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)

            # Directional Movement
            up_move = h - prev_h
            down_move = prev_l - l

            if up_move > down_move and up_move > 0:
                plus_dm_list.append(up_move)
            else:
                plus_dm_list.append(0.0)

            if down_move > up_move and down_move > 0:
                minus_dm_list.append(down_move)
            else:
                minus_dm_list.append(0.0)

        # Suavizado de Wilder para TR, +DM y -DM
        smoothed_tr = sum(tr_list[:period])
        smoothed_plus_dm = sum(plus_dm_list[:period])
        smoothed_minus_dm = sum(minus_dm_list[:period])

        dx_list = []
        # Calcular primer DX en i = period - 1 (de listas de deltas, que corresponde a barra period)
        if smoothed_tr > 1e-9:
            p_di = 100.0 * (smoothed_plus_dm / smoothed_tr)
            m_di = 100.0 * (smoothed_minus_dm / smoothed_tr)
            di_sum = p_di + m_di
            dx0 = 100.0 * (abs(p_di - m_di) / di_sum) if di_sum > 1e-9 else 0.0
        else:
            dx0 = 0.0
        dx_list.append(dx0)

        for j in range(period, len(tr_list)):
            smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[j]
            smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[j]
            smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[j]

            if smoothed_tr > 1e-9:
                p_di = 100.0 * (smoothed_plus_dm / smoothed_tr)
                m_di = 100.0 * (smoothed_minus_dm / smoothed_tr)
                di_sum = p_di + m_di
                dx = 100.0 * (abs(p_di - m_di) / di_sum) if di_sum > 1e-9 else 0.0
            else:
                dx = 0.0
            dx_list.append(dx)

        adx_values: List[float] = [float("nan")] * n
        if len(dx_list) < period:
            return adx_values

        # Primer ADX es el promedio simple de los primeros period valores de DX
        first_adx = sum(dx_list[:period]) / period
        first_adx_bar_idx = 2 * period - 1
        adx_values[first_adx_bar_idx] = round(first_adx, 2)

        curr_adx = first_adx
        for k in range(period, len(dx_list)):
            curr_adx = (curr_adx * (period - 1) + dx_list[k]) / period
            bar_idx = first_adx_bar_idx + (k - period + 1)
            if bar_idx < n:
                adx_values[bar_idx] = round(curr_adx, 2)

        return adx_values


class MarketRegimeDetectorV1:
    """
    Detector de Régimen de Mercado V1 desacoplado e independiente.
    Aplica reglas matemáticas estrictas sobre velas cerradas y confirmadas.
    """

    def __init__(
        self,
        adx_trending_min: float = 25.0,
        er_trending_min: float = 0.35,
        adx_ranging_max: float = 20.0,
        er_ranging_max: float = 0.25,
        adx_period: int = 14,
        er_period: int = 20,
        sma_period: int = 50
    ):
        self.adx_trending_min = adx_trending_min
        self.er_trending_min = er_trending_min
        self.adx_ranging_max = adx_ranging_max
        self.er_ranging_max = er_ranging_max
        self.adx_period = adx_period
        self.er_period = er_period
        self.sma_period = sma_period

    def evaluate_regime(
        self,
        symbol: str,
        confirmed_bars: List[OHLCVBar]
    ) -> RegimeEvaluationRecord:
        """
        Evalúa el régimen de mercado para el símbolo dado sobre velas cerradas.
        Garantiza Cero Look-Ahead: Solo usa las barras provistas en confirmed_bars.
        """
        now_utc = datetime.utcnow()
        min_bars_needed = max(self.sma_period, 2 * self.adx_period, self.er_period + 1)

        if not confirmed_bars or len(confirmed_bars) < min_bars_needed:
            last_ts = confirmed_bars[-1].timestamp if confirmed_bars else now_utc
            last_c = confirmed_bars[-1].close if confirmed_bars else 0.0
            return RegimeEvaluationRecord(
                symbol=symbol,
                bar_timestamp=last_ts,
                evaluation_timestamp=now_utc,
                regime=MarketRegimeV1.INDETERMINATE,
                adx_14=float("nan"),
                er_20=float("nan"),
                sma_50=float("nan"),
                close_price=last_c,
                reason=f"Barras insuficientes ({len(confirmed_bars)} < {min_bars_needed} requeridas)"
            )

        last_bar = confirmed_bars[-1]
        closes = [b.close for b in confirmed_bars]

        adx_series = RegimeFeatureCalculator.calculate_adx(confirmed_bars, self.adx_period)
        er_series = RegimeFeatureCalculator.calculate_efficiency_ratio(closes, self.er_period)
        sma_series = RegimeFeatureCalculator.calculate_sma(closes, self.sma_period)

        adx_val = adx_series[-1]
        er_val = er_series[-1]
        sma_val = sma_series[-1]
        c_val = last_bar.close

        # Si algún valor es NaN o inválido -> INDETERMINATE
        if math.isnan(adx_val) or math.isnan(er_val) or math.isnan(sma_val):
            return RegimeEvaluationRecord(
                symbol=symbol,
                bar_timestamp=last_bar.timestamp,
                evaluation_timestamp=now_utc,
                regime=MarketRegimeV1.INDETERMINATE,
                adx_14=adx_val,
                er_20=er_val,
                sma_50=sma_val,
                close_price=c_val,
                reason="Indicadores contienen valores no computables (NaN)"
            )

        # Regla 1: TRENDING_BULL
        if adx_val >= self.adx_trending_min and er_val >= self.er_trending_min and c_val > sma_val:
            regime = MarketRegimeV1.TRENDING_BULL
            reason = (
                f"Tendencia alcista confirmada: ADX(14)={adx_val:.2f} >= {self.adx_trending_min}, "
                f"ER(20)={er_val:.4f} >= {self.er_trending_min}, Close={c_val:.2f} > SMA(50)={sma_val:.2f}"
            )
        # Regla 2: RANGING
        elif adx_val < self.adx_ranging_max and er_val < self.er_ranging_max:
            regime = MarketRegimeV1.RANGING
            reason = (
                f"Consolidación/Rango confirmado: ADX(14)={adx_val:.2f} < {self.adx_ranging_max}, "
                f"ER(20)={er_val:.4f} < {self.er_ranging_max}"
            )
        # Regla 3: INDETERMINATE (Zona de transición o señales divergentes)
        else:
            regime = MarketRegimeV1.INDETERMINATE
            reasons = []
            if adx_val >= self.adx_trending_min and c_val <= sma_val:
                reasons.append(f"ADX alto ({adx_val:.2f}) pero precio <= SMA50 ({sma_val:.2f})")
            if adx_val >= self.adx_trending_min and er_val < self.er_trending_min:
                reasons.append(f"ADX alto ({adx_val:.2f}) pero ER bajo ({er_val:.4f} < {self.er_trending_min})")
            if not reasons:
                reasons.append(f"Valores en zona de transición intermedia (ADX={adx_val:.2f}, ER={er_val:.4f})")
            reason = f"Transición o divergencia: {'; '.join(reasons)}"

        return RegimeEvaluationRecord(
            symbol=symbol,
            bar_timestamp=last_bar.timestamp,
            evaluation_timestamp=now_utc,
            regime=regime,
            adx_14=adx_val,
            er_20=er_val,
            sma_50=sma_val,
            close_price=c_val,
            reason=reason,
            details={
                "adx_threshold_bull": self.adx_trending_min,
                "er_threshold_bull": self.er_trending_min,
                "adx_threshold_ranging": self.adx_ranging_max,
                "er_threshold_ranging": self.er_ranging_max
            }
        )
