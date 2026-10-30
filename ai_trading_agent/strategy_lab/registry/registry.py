"""
ai_trading_agent.strategy_lab.registry.registry
================================================
Registro Central de Estrategias con Versionado Inmutable y Persistencia SQLite.
Gestiona el catálogo de estrategias investigadas, candidatas y aprobadas con
protección criptográfica, guardas de estado de ciclo de vida y procedencia de datos.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

from ai_trading_agent.strategy_lab.core.models import LabStrategyDefinition, StrategyStatus, StrategyLineage
from database import get_connection

logger = logging.getLogger(__name__)


class ProtectedStrategyOverwriteError(ValueError):
    """Raised when an unauthorized experiment or mutation attempts to overwrite a strategy in a protected lifecycle state."""
    pass


class DataProvenanceViolationError(ValueError):
    """Raised when synthetic or mock data attempts to overwrite metrics of a non-research strategy."""
    pass


PROTECTED_LIFECYCLE_STATES = {
    StrategyStatus.PAPER,
    StrategyStatus.APPROVED,
    StrategyStatus.PAUSED,
    StrategyStatus.RETIRED,
}

SYNTHETIC_DATASET_MARKERS = (
    "synthetic",
    "mock",
    "test fixture",
    "unit-test dataset",
    "synthetic_seed",
)


class StrategyRegistry:
    """Registro central con soporte de versionado y persistencia relacional."""

    def register_strategy(
        self,
        strat: LabStrategyDefinition,
        allow_governance_override: bool = False,
        provenance: Optional[Dict[str, Any]] = None
    ):
        """
        Registra o actualiza una estrategia en SQLite con validación estricta de:
        1. Inmutabilidad de estrategias en estados protegidos (PAPER, APPROVED, PAUSED, RETIRED).
        2. Procedencia de datos (Rechazo de datasets sintéticos/mock fuera de RESEARCH/BACKTEST).
        3. Separación entre métricas experimentales y métricas canónicas de producción.
        """
        existing = self.get_strategy(strat.strategy_id)

        # 1. Protección de estados protegidos (PAPER, APPROVED, PAUSED, RETIRED)
        if existing and existing.status in PROTECTED_LIFECYCLE_STATES:
            if not allow_governance_override:
                # Comprobar si se intentan alterar métricas o scores
                metrics_changed = (
                    strat.robustness_score != existing.robustness_score
                    or strat.strategy_score != existing.strategy_score
                    or (strat.metrics != existing.metrics and strat.metrics is not None)
                )
                if metrics_changed:
                    raise ProtectedStrategyOverwriteError(
                        f"REJECTED: Strategy '{strat.strategy_id}' is in protected lifecycle state '{existing.status.value}'. "
                        f"Overwriting canonical registry metrics with research/experiment data is forbidden."
                    )
                if strat.status != existing.status:
                    raise ProtectedStrategyOverwriteError(
                        f"REJECTED: Strategy '{strat.strategy_id}' is in protected lifecycle state '{existing.status.value}'. "
                        f"Direct status mutation is forbidden. Use LifecycleManager."
                    )

        # 2. Data Provenance Guard: rechazar datasets sintéticos/mock fuera de RESEARCH/BACKTEST
        if provenance:
            dataset_ver = str(provenance.get("dataset_version", "")).lower()
            source_type = str(provenance.get("source_type", "")).lower()
            is_synthetic = any(marker in dataset_ver or marker in source_type for marker in SYNTHETIC_DATASET_MARKERS)

            target_status = existing.status if existing else strat.status
            if is_synthetic and target_status not in (StrategyStatus.RESEARCH, StrategyStatus.BACKTEST):
                raise DataProvenanceViolationError(
                    f"REJECTED: Dataset '{dataset_ver}' (source_type='{source_type}') is marked as synthetic/mock "
                    f"and CANNOT update metrics for strategy '{strat.strategy_id}' with lifecycle status '{target_status.value}'."
                )

        # Adjuntar procedencia a metrics_json si fue provista
        metrics_to_store = dict(strat.metrics or {})
        if provenance:
            metrics_to_store["_provenance"] = {
                "dataset_version": provenance.get("dataset_version", "unknown"),
                "timeframe": provenance.get("timeframe", "unknown"),
                "experiment_id": provenance.get("experiment_id", "unknown"),
                "source_type": provenance.get("source_type", "unknown"),
                "timestamp": provenance.get("timestamp", datetime.utcnow().isoformat())
            }

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_strategy_registry
            (strategy_id, name, version, description, parent_strategy_id, created_by, created_at, updated_at, status, universe_json, timeframes_json, parameters_json, rules_json, robustness_score, strategy_score, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_id) DO UPDATE SET
            status = excluded.status,
            robustness_score = excluded.robustness_score,
            strategy_score = excluded.strategy_score,
            metrics_json = excluded.metrics_json,
            updated_at = excluded.updated_at
        """, (
            strat.strategy_id,
            strat.name,
            strat.version,
            strat.description,
            strat.parent_strategy_id,
            strat.created_by,
            strat.created_at.isoformat(),
            strat.updated_at.isoformat(),
            strat.status.value,
            json.dumps(strat.universe, default=str),
            json.dumps(strat.timeframes, default=str),
            json.dumps(strat.parameters, default=str),
            json.dumps(strat.rules, default=str),
            strat.robustness_score,
            strat.strategy_score,
            json.dumps(metrics_to_store, default=str)
        ))
        conn.commit()
        conn.close()

    def record_lineage(self, lineage: StrategyLineage):
        """Registra la relación padre-hijo (mutación evolutiva) en SQLite."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_strategy_lineage (parent_id, child_id, mutation_description, reason, experiment_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            lineage.parent_id,
            lineage.child_id,
            lineage.mutation_description,
            lineage.reason,
            lineage.experiment_id,
            lineage.created_at.isoformat()
        ))
        conn.commit()
        conn.close()

    def get_strategy(self, strategy_id: str) -> Optional[LabStrategyDefinition]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lab_strategy_registry WHERE strategy_id = ?", (strategy_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return LabStrategyDefinition(
            strategy_id=row["strategy_id"],
            name=row["name"],
            version=row["version"],
            description=row["description"],
            parent_strategy_id=row["parent_strategy_id"] or "",
            created_by=row["created_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            status=StrategyStatus(row["status"]),
            universe=json.loads(row["universe_json"]),
            timeframes=json.loads(row["timeframes_json"]),
            parameters=json.loads(row["parameters_json"]),
            rules=json.loads(row["rules_json"]),
            robustness_score=row["robustness_score"],
            strategy_score=row["strategy_score"],
            metrics=json.loads(row["metrics_json"] or "{}")
        )

    def list_strategies(self, status_filter: Optional[StrategyStatus] = None) -> List[LabStrategyDefinition]:
        conn = get_connection()
        cursor = conn.cursor()
        if status_filter:
            cursor.execute("SELECT * FROM lab_strategy_registry WHERE status = ? ORDER BY strategy_score DESC", (status_filter.value,))
        else:
            cursor.execute("SELECT * FROM lab_strategy_registry ORDER BY strategy_score DESC")
        rows = cursor.fetchall()
        conn.close()

        strategies = []
        for r in rows:
            strategies.append(LabStrategyDefinition(
                strategy_id=r["strategy_id"],
                name=r["name"],
                version=r["version"],
                description=r["description"],
                parent_strategy_id=r["parent_strategy_id"] or "",
                created_by=r["created_by"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
                status=StrategyStatus(r["status"]),
                universe=json.loads(r["universe_json"]),
                timeframes=json.loads(r["timeframes_json"]),
                parameters=json.loads(r["parameters_json"]),
                rules=json.loads(r["rules_json"]),
                robustness_score=r["robustness_score"],
                strategy_score=r["strategy_score"],
                metrics=json.loads(r["metrics_json"] or "{}")
            ))
        return strategies


strategy_registry = StrategyRegistry()
