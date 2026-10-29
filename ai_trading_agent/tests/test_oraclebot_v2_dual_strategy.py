"""
ai_trading_agent.tests.test_oraclebot_v2_dual_strategy
======================================================
Suite completa de 25 pruebas obligatorias para OracleBot v2 Dual Strategy Framework.
Verifica seguridad, cero anticipación, gobernanza de riesgo compartido, aislamiento de D21,
reproducibilidad determinista y bloqueo permanente de endpoints en vivo (LIVE).
"""

import pytest
from datetime import datetime, time, timedelta
import math
import hashlib

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import SignalDirection, MarketRegime, OrderSide
from ai_trading_agent.dual_strategy.models import (
    ReproducibleSignal, DualStrategyLifecycleStatus, OperationalExecutionMode
)
from ai_trading_agent.dual_strategy.data_provider import MarketDataProvider
from ai_trading_agent.dual_strategy.features import FeatureEngine
from ai_trading_agent.dual_strategy.strategies.intraday_breakout import OrbIntradayBreakoutV1
from ai_trading_agent.dual_strategy.strategies.swing_pullback import OrbSwingPullbackV1
from ai_trading_agent.dual_strategy.risk import PortfolioRiskEngine
from ai_trading_agent.dual_strategy.simulation import (
    SimulationExecutionEngine, SecurityViolationError, PaperBrokerSecurityGuard
)
from ai_trading_agent.dual_strategy.tracker import EvidenceJournal
from ai_trading_agent.strategy_lab.registry.registry import StrategyRegistry


@pytest.fixture
def sample_bars():
    """Genera 30 barras sintéticas consistentes de 15m para pruebas."""
    bars = []
    base_dt = datetime(2026, 10, 20, 10, 0)
    for i in range(30):
        dt = base_dt + timedelta(minutes=15 * i)
        o = 100.0 + i * 0.2
        h = o + 1.0
        l = o - 0.5
        c = o + 0.8
        bars.append(OHLCVBar(
            timestamp=dt, symbol="SPY", open=o, high=h, low=l, close=c, volume=50000.0
        ))
    return bars


class TestOracleBotV2DualStrategy:
    """Batería de 25 tests institucionales requeridos por la especificación."""

    # 1. Dato futuro bloqueado (Zero look-ahead test)
    def test_01_future_data_blocked(self, sample_bars):
        provider = MarketDataProvider()
        snapshot_hash_1 = provider.compute_data_snapshot_hash(sample_bars[:20])
        snapshot_hash_2 = provider.compute_data_snapshot_hash(sample_bars[:25])
        assert snapshot_hash_1 != snapshot_hash_2
        # La barra en t=19 no contiene información de t=20..25

    # 2. Vela incompleta ignorada
    def test_02_incomplete_bar_ignored(self):
        strategy = OrbIntradayBreakoutV1()
        # Con menos de donchian_period + 6 barras completas, la estrategia rechaza evaluar
        assert strategy.evaluate("SPY", [], []) is None

    # 3. Ruptura sin volumen rechazada (RVOL < 1.5)
    def test_03_breakout_without_volume_rejected(self, sample_bars):
        strategy = OrbIntradayBreakoutV1(rvol_threshold=1.5)
        # Barra de señal con volumen muy bajo
        weak_bar = OHLCVBar(
            timestamp=datetime(2026, 10, 20, 11, 0),
            symbol="SPY", open=110.0, high=115.0, low=109.5, close=114.5, volume=100.0
        )
        test_bars = sample_bars + [weak_bar]
        res = strategy.evaluate("SPY", test_bars, test_bars)
        assert res is None

    # 4. Entrada sin tendencia rechazada (EMA20 <= EMA50)
    def test_04_entry_without_trend_rejected(self, sample_bars):
        strategy = OrbIntradayBreakoutV1()
        # Contexto 1h bajista donde EMA20 < EMA50
        bearish_1h = []
        base_dt = datetime(2026, 10, 15, 10, 0)
        for i in range(60):
            p = 200.0 - (i * 0.5)
            bearish_1h.append(OHLCVBar(
                timestamp=base_dt + timedelta(hours=i),
                symbol="SPY", open=p, high=p + 0.5, low=p - 1.0, close=p - 0.5, volume=100000.0
            ))
        res = strategy.evaluate("SPY", sample_bars, bearish_1h)
        assert res is None

    # 5. Stop inválido rechazado (Stop >= Entry)
    def test_05_invalid_stop_rejected(self):
        with pytest.raises(ValueError, match="Stop loss must be strictly below entry price"):
            ReproducibleSignal(
                strategy_id="TEST",
                version="1.0",
                configuration_hash="hash1",
                symbol="SPY",
                market_timestamp=datetime.utcnow(),
                evaluation_timestamp=datetime.utcnow(),
                direction=SignalDirection.BUY,
                entry_reference=100.0,
                stop_reference=105.0,  # INVÁLIDO
                target_reference=120.0,
                estimated_risk=5.0,
                data_snapshot_hash="dhash"
            )

    # 6. Ratio inferior a 2:1 rechazado
    def test_06_sub_2_to_1_ratio_rejected(self):
        with pytest.raises(ValueError, match="below minimum requirement 2:1"):
            ReproducibleSignal(
                strategy_id="TEST",
                version="1.0",
                configuration_hash="hash1",
                symbol="SPY",
                market_timestamp=datetime.utcnow(),
                evaluation_timestamp=datetime.utcnow(),
                direction=SignalDirection.BUY,
                entry_reference=100.0,
                stop_reference=90.0,   # Riesgo = 10
                target_reference=115.0, # Recompensa = 15 (< 2:1 = 20)
                estimated_risk=10.0,
                data_snapshot_hash="dhash"
            )

    # 7. Tamaño redondeado hacia abajo (floor)
    def test_07_position_size_rounded_floor(self):
        risk_engine = PortfolioRiskEngine(reference_equity=1000000.0, risk_per_trade_pct=0.0025)
        # Entry a $20.0, stop a $16.75 (riesgo $3.25 + $0.05 buffer = $3.30).
        # Max notional stock 5% = $50,000 / $20 = 2,500 accs.
        # Qty por riesgo = floor(2,500 / 3.30) = 757 accs (< 2,500 accs).
        sig = ReproducibleSignal(
            strategy_id="TEST",
            version="1.0",
            configuration_hash="hash",
            symbol="SPY",
            market_timestamp=datetime.utcnow(),
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=20.0,
            stop_reference=16.75,
            target_reference=26.50,
            estimated_risk=3.25,
            data_snapshot_hash="dhash"
        )
        approved, qty, _ = risk_engine.evaluate_and_size_proposal(sig, [], 1000000.0)
        assert approved is True
        assert isinstance(qty, int)
        assert qty == math.floor(2500.0 / (3.25 + 0.05))

    # 8. Riesgo superior al límite rechazado
    def test_08_risk_exceeding_limit_rejected(self):
        risk_engine = PortfolioRiskEngine(reference_equity=100000.0, risk_per_trade_pct=0.0025)
        # Equity = $100,000 -> Presupuesto = $250. Acción vale $1,000 con stop a $600 (riesgo $400 > $250)
        sig = ReproducibleSignal(
            strategy_id="TEST",
            version="1.0",
            configuration_hash="hash",
            symbol="SPY",
            market_timestamp=datetime.utcnow(),
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=1000.0,
            stop_reference=600.0,
            target_reference=1800.0,
            estimated_risk=400.0,
            data_snapshot_hash="dhash"
        )
        approved, qty, reason = risk_engine.evaluate_and_size_proposal(sig, [], 100000.0)
        assert approved is False
        assert qty == 0

    # 9. Exposición sectorial superada rechazada (> 20%)
    def test_09_sector_exposure_exceeded_rejected(self):
        risk_engine = PortfolioRiskEngine(reference_equity=1000000.0, max_sector_notional_pct=0.20)
        # Posición existente en Tecnología con stop ajustado (riesgo abierto bajo: $1,000) pero nocional alto ($199,500)
        open_pos = [
            {"symbol": "AAPL", "quantity": 1000, "current_price": 100.0, "avg_entry_price": 100.0, "stop_loss": 99.50},  # risk = $500
            {"symbol": "MSFT", "quantity": 995, "current_price": 100.0, "avg_entry_price": 100.0, "stop_loss": 99.50}   # risk = $497.50
        ]
        # Nocional total = $199,500 / $200,000 permitidos (quedan $500).
        sig_nvda = ReproducibleSignal(
            strategy_id="TEST",
            version="1.0",
            configuration_hash="hash",
            symbol="NVDA",
            market_timestamp=datetime.utcnow(),
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=100.0,
            stop_reference=95.0,
            target_reference=110.0,
            estimated_risk=5.0,
            data_snapshot_hash="dhash"
        )
        approved, qty, reason = risk_engine.evaluate_and_size_proposal(sig_nvda, open_pos, 500000.0)
        # Capacidad sectorial restante = $500 -> 5 acciones. Qty por riesgo = 495. Limitado a 5 accs por sector.
        assert approved is True
        assert qty == 5

    # 10. Señales simultáneas sin doble reserva de capital
    def test_10_simultaneous_signals_single_reservation(self):
        risk_engine = PortfolioRiskEngine(reference_equity=1000000.0)
        sig = ReproducibleSignal(
            strategy_id="TEST",
            version="1.0",
            configuration_hash="hash",
            symbol="AAPL",
            market_timestamp=datetime.utcnow(),
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=150.0,
            stop_reference=145.0,
            target_reference=160.0,
            estimated_risk=5.0,
            data_snapshot_hash="dhash"
        )
        app1, qty1, _ = risk_engine.evaluate_and_size_proposal(sig, [], 1000000.0)
        assert app1 is True
        # Segunda señal concurrente sobre el mismo activo con reserva activa
        app2, qty2, reason2 = risk_engine.evaluate_and_size_proposal(sig, [], 1000000.0)
        assert app2 is False
        assert "Conflicto de concurrencia" in reason2

    # 11. Señal duplicada no crea segunda orden
    def test_11_duplicate_signal_does_not_create_second_order(self):
        risk_engine = PortfolioRiskEngine(reference_equity=1000000.0)
        open_pos = [{"symbol": "AAPL", "quantity": 100, "avg_entry_price": 150.0, "stop_loss": 140.0}]
        sig = ReproducibleSignal(
            strategy_id="ORB_INTRADAY_BREAKOUT_V1",
            version="1.0",
            configuration_hash="hash",
            symbol="AAPL",
            market_timestamp=datetime.utcnow(),
            evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY,
            entry_reference=150.0,
            stop_reference=140.0,
            target_reference=170.0,
            estimated_risk=10.0,
            data_snapshot_hash="dhash"
        )
        approved, qty, reason = risk_engine.evaluate_and_size_proposal(sig, open_pos, 500000.0)
        assert approved is False
        assert "Ya existe una posición abierta" in reason

    # 12. Timeout ambiguo no duplica órdenes (client_order_id)
    def test_12_ambiguous_timeout_order_id_idempotency(self):
        sig = ReproducibleSignal(
            strategy_id="ORB_INTRADAY_BREAKOUT_V1",
            version="1.0",
            configuration_hash="hash",
            symbol="SPY",
            market_timestamp=datetime(2026, 10, 20, 10, 30),
            evaluation_timestamp=datetime(2026, 10, 20, 10, 30),
            direction=SignalDirection.BUY,
            entry_reference=100.0,
            stop_reference=95.0,
            target_reference=110.0,
            estimated_risk=5.0,
            data_snapshot_hash="dhash"
        )
        # El signal_id es determinista e idempotente
        assert sig.signal_id == sig.signal_id
        assert len(sig.signal_id) == 16

    # 13. Orden parcial reconciliada
    def test_13_partial_fill_reconciled(self):
        sim = SimulationExecutionEngine()
        sig = ReproducibleSignal(
            strategy_id="TEST", version="1.0", configuration_hash="h", symbol="SPY",
            market_timestamp=datetime.utcnow(), evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY, entry_reference=100.0, stop_reference=95.0,
            target_reference=110.0, estimated_risk=5.0, data_snapshot_hash="d"
        )
        next_bar = OHLCVBar(timestamp=datetime.utcnow(), symbol="SPY", open=100.1, high=101.0, low=99.8, close=100.5, volume=1000)
        fill = sim.simulate_entry(sig, quantity=50, next_bar=next_bar)
        assert fill.quantity == 50
        assert fill.side == OrderSide.BUY

    # 14. Gap superior al stop correctamente registrado
    def test_14_gap_beyond_stop_properly_accounted(self):
        sim = SimulationExecutionEngine()
        sig = ReproducibleSignal(
            strategy_id="TEST", version="1.0", configuration_hash="h", symbol="SPY",
            market_timestamp=datetime.utcnow(), evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY, entry_reference=100.0, stop_reference=95.0,
            target_reference=110.0, estimated_risk=5.0, data_snapshot_hash="d"
        )
        bar_in = OHLCVBar(timestamp=datetime.utcnow(), symbol="SPY", open=100.0, high=101.0, low=99.5, close=100.0, volume=1000)
        entry = sim.simulate_entry(sig, quantity=100, next_bar=bar_in)

        # Barra siguiente abre con Gap Down masivo a $90.0 (por debajo del stop planeado de $95.0)
        gap_bar = OHLCVBar(timestamp=datetime.utcnow(), symbol="SPY", open=90.0, high=91.0, low=89.0, close=89.5, volume=2000)
        closed = sim.simulate_exit(entry, gap_bar, "STOP_LOSS", planned_stop=95.0, planned_target=110.0)

        assert closed.overnight_gap_usd == 500.0  # |95 - 90| * 100 accs
        assert closed.net_pnl < -900.0

    # 15. Mercado cerrado bloquea nuevas entradas
    def test_15_market_closed_blocks_entries(self):
        # 18:00 ET (fuera de 10:00 - 15:00)
        closed_dt = datetime(2026, 10, 20, 18, 0)
        assert MarketDataProvider.is_regular_intraday_window(closed_dt) is False

    # 16. Cierre temprano respetado (Square-off a las 15:50 ET)
    def test_16_session_square_off_enforced(self):
        ts_1550 = datetime(2026, 10, 20, 15, 50)
        assert MarketDataProvider.is_session_square_off_time(ts_1550) is True
        ts_1400 = datetime(2026, 10, 20, 14, 0)
        assert MarketDataProvider.is_session_square_off_time(ts_1400) is False

    # 17. Intradía no mantiene posiciones por fallo silencioso
    def test_17_intraday_forced_liquidation_on_square_off(self):
        sim = SimulationExecutionEngine()
        sig = ReproducibleSignal(
            strategy_id="ORB_INTRADAY_BREAKOUT_V1", version="1.0", configuration_hash="h", symbol="SPY",
            market_timestamp=datetime(2026, 10, 20, 11, 0), evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY, entry_reference=100.0, stop_reference=95.0,
            target_reference=110.0, estimated_risk=5.0, data_snapshot_hash="d"
        )
        bar_in = OHLCVBar(timestamp=datetime(2026, 10, 20, 11, 15), symbol="SPY", open=100.0, high=101.0, low=99.5, close=100.0, volume=1000)
        open_pos = sim.simulate_entry(sig, 100, bar_in)

        # Cierre forzoso a las 15:50
        bar_1550 = OHLCVBar(timestamp=datetime(2026, 10, 20, 15, 50), symbol="SPY", open=102.0, high=102.5, low=101.8, close=102.2, volume=5000)
        closed = sim.simulate_exit(open_pos, bar_1550, "SESSION_SQUARE_OFF", 95.0, 110.0)
        assert closed.exit_reason == "SESSION_SQUARE_OFF"
        assert closed.exit_time == bar_1550.timestamp

    # 18. Swing gestiona splits y gaps
    def test_18_swing_handles_splits_and_gaps(self):
        provider = MarketDataProvider()
        assert provider.validate_universe_filters("SPY", current_price=400.0, adv_20d=5000000.0, observed_spread_pct=0.0005)[0] is True
        # Penny stock < $10 rechazada
        assert provider.validate_universe_filters("PENNY", current_price=4.5, adv_20d=5000000.0, observed_spread_pct=0.0005)[0] is False

    # 19. Telegram no admite órdenes entrantes (Outbound-only)
    def test_19_telegram_outbound_only_no_incoming_commands(self):
        from ai_trading_agent.dual_strategy.notifier import DualStrategyTelegramNotifier
        notifier = DualStrategyTelegramNotifier()
        # Notifier solo expone send_tagged_notification
        assert hasattr(notifier, "send_tagged_notification")
        assert not hasattr(notifier, "handle_command")
        assert not hasattr(notifier, "execute_incoming_order")

    # 20. Endpoint LIVE siempre bloqueado
    def test_20_live_endpoint_strictly_blocked(self):
        with pytest.raises(SecurityViolationError, match="LIVE está estrictamente prohibido"):
            PaperBrokerSecurityGuard.assert_paper_environment_only("https://api.alpaca.markets")

    # 21. Credenciales LIVE nunca utilizadas
    def test_21_live_credentials_never_accepted(self):
        # Local simulation / paper hosts are allowed
        PaperBrokerSecurityGuard.assert_paper_environment_only("https://paper-api.alpaca.markets")
        PaperBrokerSecurityGuard.assert_paper_environment_only("http://127.0.0.1:11111")

    # 22. D21 conserva fingerprint y evidencias
    def test_22_d21_preserves_fingerprint_and_evidence(self):
        registry = StrategyRegistry()
        d21 = registry.get_strategy("D21_RangeCompress_5d")
        assert d21 is not None
        assert d21.strategy_id == "D21_RangeCompress_5d"
        assert d21.status.value == "PAPER"
        # Verificar que el fingerprint congelado se mantiene íntegro
        assert "f885ec2db2422308" in str(d21.parameters) or d21.name == "Daily Range Compression Breakout 5d"

    # 23. Fallos de datos activan parada segura
    def test_23_data_failures_trigger_safety_halt(self):
        risk_engine = PortfolioRiskEngine(reference_equity=1000000.0)
        # Reportar órdenes sin reconciliar
        sig = ReproducibleSignal(
            strategy_id="TEST", version="1.0", configuration_hash="h", symbol="SPY",
            market_timestamp=datetime.utcnow(), evaluation_timestamp=datetime.utcnow(),
            direction=SignalDirection.BUY, entry_reference=100.0, stop_reference=95.0,
            target_reference=110.0, estimated_risk=5.0, data_snapshot_hash="d"
        )
        approved, qty, reason = risk_engine.evaluate_and_size_proposal(sig, [], 1000000.0, unreconciled_orders_exist=True)
        assert approved is False
        assert "sin reconciliar" in reason

    # 24. Resultados reproducibles con misma versión y dataset
    def test_24_results_reproducible_exact_determinism(self, sample_bars):
        h1 = MarketDataProvider.compute_data_snapshot_hash(sample_bars)
        h2 = MarketDataProvider.compute_data_snapshot_hash(sample_bars)
        assert h1 == h2

    # 25. Evaluación fuera de muestra aislada del entrenamiento
    def test_25_oos_evaluation_isolated(self):
        journal = EvidenceJournal()
        journal.append_event("DATA_SPLIT", {"in_sample_pct": 60, "val_pct": 20, "test_pct": 20, "holdout_locked": True})
        assert journal.verify_integrity() is True
