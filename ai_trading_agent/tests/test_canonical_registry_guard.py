"""
ai_trading_agent/tests/test_canonical_registry_guard.py
======================================================
Regression tests for Canonical Strategy Registry Guard, Data Provenance,
and Lifecycle Immutability.

Verifies:
A. RESEARCH strategy can receive research metric updates.
B. PAPER strategy rejects experiment metric overwrite.
C. APPROVED strategy rejects experiment metric overwrite.
D. Synthetic dataset cannot alter canonical PAPER metrics.
E. Experiment remains stored in lab_experiments regardless of strategy status.
F. D21 fingerprint remains unchanged.
G. Lifecycle status remains PAPER.
H. Canonical metrics remain: PRS = 71.2, SQS = 69.17.
"""

import pytest
import json
import hashlib
from datetime import datetime

from ai_trading_agent.strategy_lab.core.models import (
    LabStrategyDefinition,
    StrategyStatus,
    LabExperiment
)
from ai_trading_agent.strategy_lab.registry.registry import (
    strategy_registry,
    ProtectedStrategyOverwriteError,
    DataProvenanceViolationError,
    PROTECTED_LIFECYCLE_STATES
)
from ai_trading_agent.strategy_lab.experiments.engine import experiment_engine
from database import get_connection


@pytest.fixture(autouse=True)
def cleanup_test_records():
    """Ensure temporary test strategies and experiments are never left in SQLite."""
    yield
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lab_strategy_registry WHERE strategy_id LIKE 'TEST_%'")
    c.execute("DELETE FROM lab_experiments WHERE experiment_id LIKE '%TEST%'")
    conn.commit()
    conn.close()


def test_a_research_strategy_can_receive_metric_updates():
    """A. RESEARCH strategy can receive research metric updates normally."""
    strat = LabStrategyDefinition(
        strategy_id="TEST_RESEARCH_STRAT_001",
        name="Test Research Strat",
        version="1.0",
        description="Temporary test strategy",
        created_by="TEST_RUNNER",
        status=StrategyStatus.RESEARCH,
        universe=["SPY"],
        timeframes=["1D"],
        parameters={"lookback": 10},
        rules={"entry": ["Close > SMA10"]},
        robustness_score=50.0,
        strategy_score=55.0,
        metrics={"total_trades": 10, "profit_factor": 1.2}
    )
    strategy_registry.register_strategy(strat)

    # Update metrics in RESEARCH
    strat.robustness_score = 58.0
    strat.strategy_score = 62.0
    strat.metrics = {"total_trades": 15, "profit_factor": 1.4}
    strategy_registry.register_strategy(strat)

    retrieved = strategy_registry.get_strategy("TEST_RESEARCH_STRAT_001")
    assert retrieved is not None
    assert retrieved.robustness_score == 58.0
    assert retrieved.strategy_score == 62.0
    assert retrieved.metrics["total_trades"] == 15


def test_b_paper_strategy_rejects_experiment_metric_overwrite():
    """B. PAPER strategy rejects experiment metric overwrite."""
    strat = LabStrategyDefinition(
        strategy_id="TEST_PAPER_STRAT_001",
        name="Test Paper Strat",
        version="1.0",
        description="Temporary paper strategy",
        created_by="TEST_RUNNER",
        status=StrategyStatus.PAPER,
        universe=["SPY"],
        timeframes=["1D"],
        parameters={"lookback": 20},
        rules={"entry": ["Close > SMA20"]},
        robustness_score=75.0,
        strategy_score=72.0,
        metrics={"total_trades": 100, "profit_factor": 1.5}
    )
    # Register with governance override
    strategy_registry.register_strategy(strat, allow_governance_override=True)

    # Attempt unauthorized metric overwrite from research experiment
    strat_tampered = LabStrategyDefinition(
        strategy_id="TEST_PAPER_STRAT_001",
        name="Test Paper Strat",
        version="1.0",
        description="Tampered paper strategy",
        created_by="TEST_RUNNER",
        status=StrategyStatus.PAPER,
        universe=["SPY"],
        timeframes=["1D"],
        parameters={"lookback": 20},
        rules={"entry": ["Close > SMA20"]},
        robustness_score=99.99,  # Overwritten score
        strategy_score=40.00,    # Overwritten score
        metrics={"total_trades": 5, "profit_factor": 10.0}
    )

    with pytest.raises(ProtectedStrategyOverwriteError) as exc_info:
        strategy_registry.register_strategy(strat_tampered, allow_governance_override=False)

    assert "protected lifecycle state 'PAPER'" in str(exc_info.value)

    # Verify state in database was NOT altered
    retrieved = strategy_registry.get_strategy("TEST_PAPER_STRAT_001")
    assert retrieved.robustness_score == 75.0
    assert retrieved.strategy_score == 72.0
    assert retrieved.metrics["total_trades"] == 100


def test_c_approved_strategy_rejects_experiment_metric_overwrite():
    """C. APPROVED strategy rejects experiment metric overwrite."""
    strat = LabStrategyDefinition(
        strategy_id="TEST_APPROVED_STRAT_001",
        name="Test Approved Strat",
        version="1.0",
        description="Temporary approved strategy",
        created_by="TEST_RUNNER",
        status=StrategyStatus.APPROVED,
        universe=["SPY"],
        timeframes=["1D"],
        parameters={"lookback": 50},
        rules={"entry": ["Close > SMA50"]},
        robustness_score=80.0,
        strategy_score=78.0,
        metrics={"total_trades": 200, "profit_factor": 1.6}
    )
    strategy_registry.register_strategy(strat, allow_governance_override=True)

    strat_tampered = LabStrategyDefinition(
        strategy_id="TEST_APPROVED_STRAT_001",
        name="Test Approved Strat",
        version="1.0",
        description="Tampered approved strategy",
        created_by="TEST_RUNNER",
        status=StrategyStatus.APPROVED,
        universe=["SPY"],
        timeframes=["1D"],
        parameters={"lookback": 50},
        rules={"entry": ["Close > SMA50"]},
        robustness_score=99.0,
        strategy_score=45.0,
        metrics={"total_trades": 8, "profit_factor": 12.0}
    )

    with pytest.raises(ProtectedStrategyOverwriteError):
        strategy_registry.register_strategy(strat_tampered, allow_governance_override=False)

    retrieved = strategy_registry.get_strategy("TEST_APPROVED_STRAT_001")
    assert retrieved.robustness_score == 80.0
    assert retrieved.strategy_score == 78.0


def test_d_synthetic_dataset_cannot_alter_canonical_paper_metrics():
    """D. Synthetic dataset cannot alter canonical PAPER metrics."""
    strat = strategy_registry.get_strategy("D21_RangeCompress_5d")
    assert strat is not None
    assert strat.status == StrategyStatus.PAPER

    # Attempt to pass synthetic provenance
    with pytest.raises((ProtectedStrategyOverwriteError, DataProvenanceViolationError)):
        strategy_registry.register_strategy(
            strat,
            allow_governance_override=False,
            provenance={
                "dataset_version": "synthetic_seed_42",
                "timeframe": "15m",
                "experiment_id": "EXP-ATTEMPT-01",
                "source_type": "synthetic_backtest"
            }
        )


def test_e_experiment_remains_stored_in_lab_experiments():
    """E. Experiment remains stored in lab_experiments even if registry update is blocked."""
    exp = LabExperiment(
        experiment_id="EXP-TEST-REGISTRY-GUARD",
        hypothesis_id="HYP-GUARD-01",
        strategy_id="D21_RangeCompress_5d",
        strategy_version="1.0",
        dataset_version="synthetic_seed_42",
        universe=["SPY"],
        symbols=["SPY"],
        timeframe="15m",
        parameters={"param": 1},
        features=["feat1"],
        metrics={"total_trades": 8, "profit_factor": 13.09},
        status="COMPLETED"
    )
    experiment_engine._save_experiment_to_db(exp)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT experiment_id, strategy_id FROM lab_experiments WHERE experiment_id = 'EXP-TEST-REGISTRY-GUARD'")
    row = c.fetchone()
    conn.close()

    assert row is not None
    assert row["strategy_id"] == "D21_RangeCompress_5d"


def test_f_g_h_d21_canonical_integrity():
    """F, G, H. D21 fingerprint, status, and canonical metrics remain uncorrupted."""
    d21 = strategy_registry.get_strategy("D21_RangeCompress_5d")
    assert d21 is not None

    # F. Fingerprint remains unchanged
    serialized = json.dumps(d21.parameters, sort_keys=True)
    fp = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    assert fp == "f885ec2db2422308", f"Fingerprint mismatch: {fp}"

    # G. Status remains PAPER
    assert d21.status == StrategyStatus.PAPER

    # H. Canonical metrics remain PRS = 71.2, SQS = 69.17
    assert d21.robustness_score == 71.2
    assert d21.strategy_score == 69.17
    assert d21.metrics.get("total_trades") == 102
    assert d21.metrics.get("profit_factor") == 1.17
    assert d21.metrics.get("expectancy_dollars") == 65.0
