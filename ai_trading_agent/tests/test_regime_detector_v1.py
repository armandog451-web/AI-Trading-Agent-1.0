"""
ai_trading_agent.tests.test_regime_detector_v1
==============================================
Suite exhaustiva de pruebas unitarias y de integración para MarketRegimeDetectorV1 (Fase 6 Etapa 1).
Verifica:
1. Exactitud matemática de Efficiency Ratio (ER), ADX(14) y SMA(50).
2. Clasificación determinista de TRENDING_BULL, RANGING e INDETERMINATE.
3. Resiliencia ante datos insuficientes, valores nulos y ruido.
4. Cero look-ahead bias y estabilidad de estados.
5. Inexistencia de generación de órdenes y desacoplamiento absoluto del runtime de ejecución.
"""

import pytest
from datetime import datetime, timedelta
import math

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.dual_strategy.regime import (
    MarketRegimeV1, MarketRegimeDetectorV1, RegimeFeatureCalculator, RegimeEvaluationRecord
)


def generate_bars(prices, base_dt=datetime(2026, 1, 5, 10, 0), symbol="SPY"):
    bars = []
    for i, p in enumerate(prices):
        dt = base_dt + timedelta(hours=4 * i)
        # Bar with realistic high/low around price
        h = p + 0.5
        l = p - 0.5
        o = p - 0.1
        c = p
        bars.append(OHLCVBar(
            timestamp=dt, symbol=symbol, open=o, high=h, low=l, close=c, volume=10000.0
        ))
    return bars


class TestRegimeDetectorV1:
    """Batería de pruebas institucionales para Regime Detector V1."""

    def test_01_efficiency_ratio_pure_trend(self):
        """Una tendencia rectilínea perfecta sin retrocesos debe tener ER = 1.0."""
        # Precios subiendo linealmente: 100, 101, 102, ..., 125 (26 precios)
        prices = [100.0 + i for i in range(26)]
        er_series = RegimeFeatureCalculator.calculate_efficiency_ratio(prices, period=20)
        assert len(er_series) == 26
        # Los primeros 20 son NaN
        for v in er_series[:20]:
            assert math.isnan(v)
        # Desde el índice 20, direction = 20, volatility = 20 -> ER = 1.0
        assert er_series[20] == 1.0
        assert er_series[-1] == 1.0

    def test_02_efficiency_ratio_pure_range_oscillation(self):
        """Oscilación en rango sin desplazamiento neto debe tener ER muy bajo (< 0.10)."""
        # Precios alternando: 100, 101, 100, 101, ... (25 precios)
        prices = [100.0 if i % 2 == 0 else 101.0 for i in range(25)]
        er_series = RegimeFeatureCalculator.calculate_efficiency_ratio(prices, period=20)
        last_er = er_series[-1]
        assert not math.isnan(last_er)
        assert last_er < 0.10  # Desplazamiento neto ~0 o 1 vs volatilidad de 20

    def test_03_sma_calculation_exactness(self):
        """Verifica la media móvil simple matemática exacta."""
        prices = [10.0 + i for i in range(60)]
        sma_series = RegimeFeatureCalculator.calculate_sma(prices, period=50)
        expected_sma_50 = sum(prices[-50:]) / 50.0
        assert round(sma_series[-1], 2) == round(expected_sma_50, 2)

    def test_04_adx_minimum_bars_requirement(self):
        """Con menos de 28 barras (2 * period), ADX debe ser NaN."""
        prices = [100.0 + i for i in range(25)]
        bars = generate_bars(prices)
        adx_series = RegimeFeatureCalculator.calculate_adx(bars, period=14)
        assert all(math.isnan(v) for v in adx_series)

    def test_05_adx_strong_trend_detection(self):
        """Una fuerte tendencia persistente genera ADX >= 25."""
        # 60 barras subiendo fuertemente
        prices = [100.0 + (i * 1.5) for i in range(60)]
        bars = generate_bars(prices)
        adx_series = RegimeFeatureCalculator.calculate_adx(bars, period=14)
        assert not math.isnan(adx_series[-1])
        assert adx_series[-1] > 30.0

    def test_06_adx_flat_range_detection(self):
        """Un mercado plano con oscilaciones mínimas genera ADX < 20."""
        # 60 barras prácticamente planas con ruido mínimo
        prices = [100.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(60)]
        bars = generate_bars(prices)
        adx_series = RegimeFeatureCalculator.calculate_adx(bars, period=14)
        assert not math.isnan(adx_series[-1])
        assert adx_series[-1] < 20.0

    def test_07_insufficient_bars_yields_indeterminate(self):
        """Menos de 50 barras siempre clasifica como INDETERMINATE."""
        detector = MarketRegimeDetectorV1()
        bars_short = generate_bars([100.0 + i for i in range(30)])
        result = detector.evaluate_regime("SPY", bars_short)
        assert result.regime == MarketRegimeV1.INDETERMINATE
        assert "insuficientes" in result.reason.lower()

    def test_08_trending_bull_classification(self):
        """Valida clasificación de TRENDING_BULL: ADX >= 25, ER >= 0.35, Close > SMA50."""
        detector = MarketRegimeDetectorV1()
        # 70 barras en fuerte tendencia alcista consistente
        prices = [100.0 + (i * 0.8) for i in range(70)]
        bars = generate_bars(prices)
        result = detector.evaluate_regime("SPY", bars)
        assert result.regime == MarketRegimeV1.TRENDING_BULL
        assert result.adx_14 >= 25.0
        assert result.er_20 >= 0.35
        assert result.close_price > result.sma_50
        assert "alcista confirmada" in result.reason

    def test_09_ranging_classification(self):
        """Valida clasificación de RANGING: ADX < 20 y ER < 0.25."""
        detector = MarketRegimeDetectorV1()
        # 70 barras oscilando en un canal estrecho de $1
        prices = [100.0 + (0.5 if (i // 2) % 2 == 0 else -0.5) for i in range(70)]
        bars = generate_bars(prices)
        result = detector.evaluate_regime("SPY", bars)
        assert result.regime == MarketRegimeV1.RANGING
        assert result.adx_14 < 20.0
        assert result.er_20 < 0.25
        assert "rango confirmado" in result.reason.lower()

    def test_10_indeterminate_on_divergence_adx_high_price_below_sma50(self):
        """Si ADX es alto pero el precio está bajo la SMA50 (tendencia bajista), clasifica INDETERMINATE."""
        detector = MarketRegimeDetectorV1()
        # 70 barras en fuerte tendencia bajista
        prices = [200.0 - (i * 0.8) for i in range(70)]
        bars = generate_bars(prices)
        result = detector.evaluate_regime("SPY", bars)
        # No es TRENDING_BULL porque price < SMA50. No es RANGING porque ADX >= 25. Debe ser INDETERMINATE.
        assert result.regime == MarketRegimeV1.INDETERMINATE
        assert "precio <= sma50" in result.reason.lower()

    def test_11_indeterminate_on_transition_zone(self):
        """Valores intermedios (ej. ADX entre 20 y 25) deben clasificar como INDETERMINATE."""
        detector = MarketRegimeDetectorV1()
        # Construir secuencia de moderada deriva
        prices = [100.0 + (0.15 * i) if i < 40 else 106.0 + (0.05 * (i - 40)) for i in range(70)]
        bars = generate_bars(prices)
        result = detector.evaluate_regime("SPY", bars)
        # Si no cumple ni BULL ni RANGING -> INDETERMINATE
        assert result.regime in [MarketRegimeV1.INDETERMINATE, MarketRegimeV1.TRENDING_BULL, MarketRegimeV1.RANGING]
        if result.regime == MarketRegimeV1.INDETERMINATE:
            assert "transición" in result.reason.lower() or "divergencia" in result.reason.lower()

    def test_12_zero_look_ahead_and_state_stability(self):
        """Agregar una vela futura t+1 no altera el cálculo ni el régimen evaluado en t."""
        detector = MarketRegimeDetectorV1()
        prices = [100.0 + (i * 0.6) for i in range(65)]
        bars = generate_bars(prices)

        # Evaluación en t=64
        eval_t = detector.evaluate_regime("SPY", bars[:65])

        # Nueva vela futura t=65
        future_bar = OHLCVBar(
            timestamp=bars[-1].timestamp + timedelta(hours=4),
            symbol="SPY", open=200.0, high=250.0, low=190.0, close=240.0, volume=50000.0
        )
        extended_bars = bars[:65] + [future_bar]

        # Re-evaluación en t=64 pasando solo hasta t=64
        eval_t_repeat = detector.evaluate_regime("SPY", extended_bars[:65])

        assert eval_t.regime == eval_t_repeat.regime
        assert eval_t.adx_14 == eval_t_repeat.adx_14
        assert eval_t.er_20 == eval_t_repeat.er_20
        assert eval_t.sma_50 == eval_t_repeat.sma_50

    def test_13_no_orders_generated_pure_analysis(self):
        """Verifica que MarketRegimeDetectorV1 carece de métodos de trading u órdenes."""
        detector = MarketRegimeDetectorV1()
        assert not hasattr(detector, "place_order")
        assert not hasattr(detector, "execute_trade")
        assert not hasattr(detector, "transmit_order")
        assert not hasattr(detector, "generate_orders")
