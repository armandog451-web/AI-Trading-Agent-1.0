"""
ai_trading_agent.notifications.journal
======================================
Journal inmutable append-only de notificaciones emitidas por Telegram.
Registra entregas, códigos HTTP y reintentos, garantizando que el bot token
NUNCA sea persistido en disco.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class NotificationJournal:
    """Persistencia local de eventos de notificación en formato JSONL."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path(__file__).resolve().parent.parent / "journal" / "data"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.storage_dir / "telegram_notifications.jsonl"

    def record_notification(
        self,
        notification_id: str,
        event_type: str,
        severity: str,
        message_hash: str,
        delivery_status: str,
        retry_count: int = 0,
        telegram_response_code: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Registra una entrada en el log.
        INVARIANTE DE SEGURIDAD: TELEGRAM_BOT_TOKEN NUNCA SE ESCRIBE AQUÍ.
        """
        record = {
            "notification_id": notification_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "message_hash": message_hash,
            "delivery_status": delivery_status,
            "retry_count": retry_count,
            "telegram_response_code": telegram_response_code,
            "error_message": error_message
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def get_recent_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Recupera los últimos registros de notificaciones."""
        if not self.log_file.exists():
            return []
        records = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-limit:]
