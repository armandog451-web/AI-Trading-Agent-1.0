"""
ai_trading_agent.execution.fidelity.journal
==========================================
Journal persistente en formato JSONL y SQLite para discrepancias y trazas completas de Paper Trading.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ai_trading_agent.domain.fidelity_models import ExecutionDiscrepancy, ExpectedTradeExecution, ActualTradeExecution


class PaperFidelityJournal:
    """Registro inmutable persistente de ejecuciones esperadas, reales y discrepancias."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path(__file__).resolve().parent.parent.parent / "journal" / "data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.discrepancies_file = self.storage_dir / "paper_discrepancies.jsonl"
        self.executions_file = self.storage_dir / "paper_executions_audit.jsonl"

    def record_discrepancy(self, discrepancy: ExecutionDiscrepancy) -> None:
        """Añade una discrepancia de forma append-only al archivo JSONL."""
        with open(self.discrepancies_file, "a", encoding="utf-8") as f:
            data = discrepancy.model_dump(mode="json")
            f.write(json.dumps(data) + "\n")

    def record_execution_pair(
        self,
        expected: ExpectedTradeExecution,
        actual: Optional[ActualTradeExecution]
    ) -> None:
        """Registra la pareja Expected vs Actual asociada a un signal_id."""
        with open(self.executions_file, "a", encoding="utf-8") as f:
            entry = {
                "recorded_at": datetime.utcnow().isoformat(),
                "signal_id": expected.signal_id,
                "strategy_id": expected.strategy_id,
                "expected": expected.model_dump(mode="json"),
                "actual": actual.model_dump(mode="json") if actual else None
            }
            f.write(json.dumps(entry) + "\n")

    def get_all_discrepancies(self) -> List[Dict[str, Any]]:
        """Lee todas las discrepancias históricas registradas."""
        if not self.discrepancies_file.exists():
            return []
        discrepancies = []
        with open(self.discrepancies_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    discrepancies.append(json.loads(line))
        return discrepancies

    def get_all_execution_pairs(self) -> List[Dict[str, Any]]:
        """Lee todas las parejas esperadas vs reales históricas."""
        if not self.executions_file.exists():
            return []
        pairs = []
        with open(self.executions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    pairs.append(json.loads(line))
        return pairs
