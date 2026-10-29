"""
ai_trading_agent.dual_strategy.tracker
======================================
Diario de Evidencias Inmutable y Seguidor de Experimentos (Evidence Journal & Tracker).
Implementa encadenamiento criptográfico append-only (SHA-256 Hash Chain) para trazabilidad.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json


class EvidenceJournal:
    """Diario append-only inmutable con encadenamiento criptográfico."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._last_hash: str = self.GENESIS_HASH

    def append_event(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Añade una entrada inmutable con sello temporal y hash encadenado."""
        ts = datetime.utcnow().isoformat()
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        raw = f"{len(self._entries)}:{self._last_hash}:{ts}:{event_type}:{payload_str}"
        entry_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        entry = {
            "index": len(self._entries),
            "timestamp": ts,
            "event_type": event_type,
            "previous_hash": self._last_hash,
            "entry_hash": entry_hash,
            "payload": payload
        }
        self._entries.append(entry)
        self._last_hash = entry_hash
        return entry_hash

    def verify_integrity(self) -> bool:
        """Verifica la integridad criptográfica de toda la cadena de bloques del diario."""
        expected_prev = self.GENESIS_HASH
        for e in self._entries:
            if e["previous_hash"] != expected_prev:
                return False
            payload_str = json.dumps(e["payload"], sort_keys=True, default=str)
            raw = f"{e['index']}:{e['previous_hash']}:{e['timestamp']}:{e['event_type']}:{payload_str}"
            calc_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if calc_hash != e["entry_hash"]:
                return False
            expected_prev = calc_hash
        return True

    def get_entries(self) -> List[Dict[str, Any]]:
        return list(self._entries)


class ExperimentTracker:
    """Rastreador de campañas de backtesting y validación de hipótesis."""

    def __init__(self, journal: EvidenceJournal):
        self.journal = journal
        self._experiments: Dict[str, Dict[str, Any]] = {}

    def log_experiment_run(
        self,
        experiment_id: str,
        strategy_id: str,
        dataset_hash: str,
        train_metrics: Dict[str, Any],
        val_metrics: Dict[str, Any],
        test_metrics: Dict[str, Any],
        cost_multiplier: float = 1.0
    ) -> str:
        record = {
            "experiment_id": experiment_id,
            "strategy_id": strategy_id,
            "dataset_hash": dataset_hash,
            "cost_multiplier": cost_multiplier,
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics,
            "recorded_at": datetime.utcnow().isoformat()
        }
        self._experiments[experiment_id] = record
        return self.journal.append_event("EXPERIMENT_COMPLETED", record)
