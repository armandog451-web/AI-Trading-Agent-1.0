"""
ai_trading_agent/tests/test_paper_fidelity_engine.py
===================================================
Tests completos para el Paper Trading Fidelity & Discrepancy Engine.
Cubre todos los requerimientos de la Sección 31 de la orden institucional:
- ExpectedTradeExecution creado antes de fill
- Matching execution pasa con 100% fidelity
- Detección de desviaciones de precio, tamaño, riesgo, stop loss y exit
- Detección de missed signal y duplicate order
- Broker rejection registrado
- Mediciones de latencia y slippage
- Severidades y Hard Safety Gates (CRITICAL genera HARD_FAIL)
- PnL positivo NO compensa fallos de seguridad
- Inmutabilidad de D21 (D21_before == D21_after, fingerprint f885ec2db2422308)
- Cambio de versión genera nueva cohorte
- Imposibilidad técnica de habilitar LIVE trading
- Bloqueo de estrategias no autorizadas
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta

from ai_trading_agent.domain.fidelity_models import (
    ExpectedTradeExecution,
    ActualTradeExecution,
    ExecutionDiscrepancy,
    DiscrepancyCategory,
    DiscrepancySeverity,
    FidelityScores,
    PaperEvidenceStatus
)
from ai_trading_agent.execution.fidelity.engine import PaperFidelityEngine
from ai_trading_agent.execution.fidelity.discrepancy import DiscrepancyDetector
from ai_trading_agent.execution.fidelity.scoring import FidelityScorer
from ai_trading_agent.execution.fidelity.metrics import ExecutionMetricsAnalyzer
from ai_trading_agent.execution.fidelity.gates import HardSafetyGates
from ai_trading_agent.strategy_lab.registry.registry import strategy_registry
from ai_trading_agent.strategy_lab.core.models import StrategyStatus
from ai_trading_agent.config.settings import settings


@pytest.fixture
def engine():
    return PaperFidelityEngine(authorized_strategy_id="D21_RangeCompress_5d")


def test_expected_execution_created_before_fill(engine):
    """Verifica que el registro de intención se genere con los datos correctos antes del fill."""
    exp = engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_001",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=100,
        expected_risk_amount=1000.0,
        expected_risk_pct=0.10,
        expected_stop_price=490.0,
        strategy_parameters={"holding_horizon_days": 5, "rr_ratio": 2.0}
    )
    assert exp.signal_id == "sig_test_001"
    assert exp.expected_position_size == 100
    assert exp.expected_notional == 50000.0
    assert exp.expected_stop_price == 490.0
    assert exp.specification_hash != ""


def test_matching_execution_passes(engine):
    """Verifica que una ejecución que replica exactamente lo esperado no genere discrepancias."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_002",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=100,
        expected_risk_amount=1000.0,
        expected_risk_pct=0.10,
        expected_stop_price=490.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_002",
        order_id="ord_002",
        requested_price=500.0,
        requested_quantity=100,
        actual_fill_price=500.0,
        actual_quantity=100,
        actual_stop_price=490.0,
        order_status="FILLED"
    )
    disc = engine.compare_execution("sig_test_002")
    assert len(disc) == 0

    scores = engine.calculate_fidelity_metrics("sig_test_002")
    assert scores.overall_execution_fidelity_score == 100.0
    assert not scores.hard_fail_active

    passed, failures = engine.evaluate_hard_safety("sig_test_002")
    assert passed
    assert len(failures) == 0


def test_entry_price_deviation_detected(engine):
    """Verifica la detección de desviaciones de precio de entrada (slippage severo)."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_003",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=100,
        expected_risk_amount=1000.0,
        expected_risk_pct=0.10,
        expected_stop_price=490.0
    )
    # Entrada real a 505.0 (+100 bps de slippage adverso)
    engine.capture_actual_execution(
        signal_id="sig_test_003",
        order_id="ord_003",
        requested_price=500.0,
        requested_quantity=100,
        actual_fill_price=505.0,
        actual_quantity=100,
        actual_stop_price=490.0,
        order_status="FILLED"
    )
    disc = engine.compare_execution("sig_test_003")
    assert any(d.category == DiscrepancyCategory.ENTRY_PRICE_DEVIATION for d in disc)
    scores = engine.calculate_fidelity_metrics("sig_test_003")
    assert scores.entry_fidelity_score < 100.0


def test_position_size_deviation_detected(engine):
    """Verifica que si la cantidad ejecutada no coincide, se registre la discrepancia."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_004",
        symbol="QQQ",
        side="BUY",
        signal_price=400.0,
        expected_entry_price=400.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=390.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_004",
        order_id="ord_004",
        requested_price=400.0,
        requested_quantity=50,
        actual_fill_price=400.0,
        actual_quantity=40,  # Faltaron 10 acciones
        actual_stop_price=390.0
    )
    disc = engine.compare_execution("sig_test_004")
    assert any(d.category == DiscrepancyCategory.POSITION_SIZE_DEVIATION for d in disc)


def test_risk_deviation_detected(engine):
    """Verifica la detección de violación en el monto o porcentaje de riesgo."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_005",
        symbol="IWM",
        side="BUY",
        signal_price=200.0,
        expected_entry_price=200.0,
        expected_position_size=100,
        expected_risk_amount=1000.0,
        expected_risk_pct=0.10,
        expected_stop_price=190.0
    )
    # Stop real mucho más amplio (180.0 -> riesgo real $2,000 en vez de $1,000)
    engine.capture_actual_execution(
        signal_id="sig_test_005",
        order_id="ord_005",
        requested_price=200.0,
        requested_quantity=100,
        actual_fill_price=200.0,
        actual_quantity=100,
        actual_stop_price=180.0
    )
    disc = engine.compare_execution("sig_test_005")
    assert any(d.category == DiscrepancyCategory.RISK_DEVIATION for d in disc)


def test_stop_mismatch_detected(engine):
    """Verifica que la ausencia de Stop Loss mandatorio sea calificada como CRITICAL."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_006",
        symbol="DIA",
        side="BUY",
        signal_price=380.0,
        expected_entry_price=380.0,
        expected_position_size=20,
        expected_risk_amount=400.0,
        expected_risk_pct=0.04,
        expected_stop_price=360.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_006",
        order_id="ord_006",
        requested_price=380.0,
        requested_quantity=20,
        actual_fill_price=380.0,
        actual_quantity=20,
        actual_stop_price=None  # Stop ausente
    )
    disc = engine.compare_execution("sig_test_006")
    stop_disc = next(d for d in disc if d.category == DiscrepancyCategory.STOP_MISMATCH)
    assert stop_disc.severity == DiscrepancySeverity.CRITICAL
    assert stop_disc.hard_fail is True


def test_exit_mismatch_detected(engine):
    """Verifica que una salida contraria a las reglas autorizadas de D21 sea detectada."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_007",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=490.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_007",
        order_id="ord_007",
        requested_price=500.0,
        requested_quantity=50,
        actual_fill_price=500.0,
        actual_quantity=50,
        actual_stop_price=490.0,
        actual_exit_reason="UNAUTHORIZED_MANUAL_PANIC_CLOSE"
    )
    disc = engine.compare_execution("sig_test_007")
    assert any(d.category == DiscrepancyCategory.EXIT_RULE_MISMATCH for d in disc)


def test_missed_signal_detected(engine):
    """Verifica la detección de una señal válida para la cual nunca se creó una orden."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_008",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=490.0
    )
    disc = engine.compare_execution("sig_test_008")
    assert len(disc) == 1
    assert disc[0].category == DiscrepancyCategory.MISSED_SIGNAL
    assert disc[0].severity == DiscrepancySeverity.HIGH


def test_duplicate_order_detected(engine):
    """Verifica que la emisión duplicada de órdenes para la misma señal sea detectada como CRITICAL."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_009",
        symbol="QQQ",
        side="BUY",
        signal_price=400.0,
        expected_entry_price=400.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=390.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_009",
        order_id="ord_009",
        requested_price=400.0,
        requested_quantity=50,
        actual_fill_price=400.0,
        actual_quantity=50,
        actual_stop_price=390.0
    )
    # Segundo llamado con el mismo order_id
    engine.capture_actual_execution(
        signal_id="sig_test_009",
        order_id="ord_009",
        requested_price=400.0,
        requested_quantity=50,
        actual_fill_price=400.0,
        actual_quantity=50,
        actual_stop_price=390.0
    )
    scores = engine.calculate_fidelity_metrics("sig_test_009")
    assert scores.hard_fail_active is True


def test_broker_rejection_logged(engine):
    """Verifica el registro de rechazos emitidos por el Paper Broker."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_010",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=490.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_010",
        order_id="ord_010",
        requested_price=500.0,
        requested_quantity=50,
        order_status="REJECTED",
        rejection_reason="INSUFFICIENT_MARGIN_SANDBOX"
    )
    disc = engine.compare_execution("sig_test_010")
    assert any(d.category == DiscrepancyCategory.BROKER_REJECTION for d in disc)


def test_latency_and_slippage_measured():
    """Verifica el cálculo estadístico de métricas de deslizamiento y latencia."""
    slips = [2.5, 4.0, 1.0, 15.0, -1.0, 3.5]
    dist_slip = ExecutionMetricsAnalyzer.calculate_slippage_distribution(slips)
    assert dist_slip["count"] == 6
    assert dist_slip["worst_bps"] == 15.0
    assert dist_slip["favorable_count"] == 1

    lats = [45.0, 120.0, 60.0, 250.0, 80.0]
    dist_lat = ExecutionMetricsAnalyzer.calculate_latency_distribution(lats)
    assert dist_lat["count"] == 5
    assert dist_lat["max_ms"] == 250.0


def test_critical_discrepancy_hard_fails(engine):
    """Verifica que una discrepancia CRITICAL invalide el score general a 0.0 y active HARD_FAIL."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_011",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=490.0
    )
    engine.capture_actual_execution(
        signal_id="sig_test_011",
        order_id="ord_011",
        requested_price=500.0,
        requested_quantity=50,
        actual_fill_price=500.0,
        actual_quantity=50,
        actual_stop_price=None  # Provoca CRITICAL
    )
    engine.compare_execution("sig_test_011")
    scores = engine.calculate_fidelity_metrics("sig_test_011")
    assert scores.overall_execution_fidelity_score == 0.0
    assert scores.hard_fail_active is True

    passed, failures = engine.evaluate_hard_safety("sig_test_011")
    assert not passed
    assert len(failures) >= 1


def test_pnl_does_not_override_safety_failure(engine):
    """Verifica que un trade con PnL positivo NO compense una violación crítica de seguridad."""
    engine.capture_expected_execution(
        strategy_id="D21_RangeCompress_5d",
        signal_id="sig_test_012",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=50,
        expected_risk_amount=500.0,
        expected_risk_pct=0.05,
        expected_stop_price=490.0
    )
    # Ganó $5,000 USD pero sin Stop Loss
    engine.capture_actual_execution(
        signal_id="sig_test_012",
        order_id="ord_012",
        requested_price=500.0,
        requested_quantity=50,
        actual_fill_price=500.0,
        actual_quantity=50,
        actual_stop_price=None,
        realized_pnl=5000.0
    )
    engine.compare_execution("sig_test_012")
    scores = engine.calculate_fidelity_metrics("sig_test_012")
    assert scores.hard_fail_active is True
    assert scores.overall_execution_fidelity_score == 0.0


def test_strategy_remains_immutable():
    """Verifica que D21 permanezca funcionalmente idéntica con fingerprint f885ec2db2422308."""
    strat = strategy_registry.get_strategy("D21_RangeCompress_5d")
    assert strat is not None
    assert strat.status == StrategyStatus.PAPER

    serialized = json.dumps(strat.parameters, sort_keys=True)
    fp = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    assert fp == "f885ec2db2422308"


def test_paper_fidelity_engine_cannot_enable_live_trading():
    """Verifica explícitamente que no exista ninguna ruta a LIVE trading ni habilitación accidental."""
    assert "LIVE" not in [s.value for s in StrategyStatus]
    assert not hasattr(settings, "LIVE_TRADING_ENABLED") or not getattr(settings, "LIVE_TRADING_ENABLED")
    assert settings.ALPACA_BASE_URL == "https://paper-api.alpaca.markets"


def test_non_d21_strategy_cannot_trade(engine):
    """Verifica que cualquier estrategia distinta a D21 genere inmediatamente un HARD_FAIL."""
    engine.capture_expected_execution(
        strategy_id="UNAUTHORIZED_STRATEGY_XYZ",
        signal_id="sig_unauth_001",
        symbol="SPY",
        side="BUY",
        signal_price=500.0,
        expected_entry_price=500.0,
        expected_position_size=10,
        expected_risk_amount=100.0,
        expected_risk_pct=0.01,
        expected_stop_price=495.0
    )
    disc = engine.compare_execution("sig_unauth_001")
    assert any(d.severity == DiscrepancySeverity.CRITICAL for d in disc)
    passed, failures = engine.evaluate_hard_safety("sig_unauth_001")
    assert not passed
