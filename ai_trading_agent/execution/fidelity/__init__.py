"""
ai_trading_agent.execution.fidelity
===================================
Subsistema institucional Paper Trading Fidelity & Discrepancy Engine.
"""

from ai_trading_agent.execution.fidelity.engine import PaperFidelityEngine, paper_fidelity_engine
from ai_trading_agent.execution.fidelity.discrepancy import DiscrepancyDetector
from ai_trading_agent.execution.fidelity.scoring import FidelityScorer
from ai_trading_agent.execution.fidelity.metrics import ExecutionMetricsAnalyzer
from ai_trading_agent.execution.fidelity.gates import HardSafetyGates
from ai_trading_agent.execution.fidelity.journal import PaperFidelityJournal
from ai_trading_agent.execution.fidelity.reporter import PaperFidelityReporter

__all__ = [
    "PaperFidelityEngine",
    "paper_fidelity_engine",
    "DiscrepancyDetector",
    "FidelityScorer",
    "ExecutionMetricsAnalyzer",
    "HardSafetyGates",
    "PaperFidelityJournal",
    "PaperFidelityReporter"
]
