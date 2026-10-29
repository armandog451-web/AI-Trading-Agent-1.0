"""
ai_trading_agent.dual_strategy.notifier
=======================================
Notificador de Alertas a Telegram Outbound-Only para OracleBot v2.
Etiqueta explícitamente cada evento como [BACKTEST], [SHADOW] o [PAPER].
No acepta comandos entrantes, con deduplicación y registro inmutable append-only.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import logging

from ai_trading_agent.config.settings import settings
from ai_trading_agent.notifications.telegram_service import telegram_notifier

logger = logging.getLogger(__name__)


class DualStrategyTelegramNotifier:
    """Emisor de notificaciones etiquetadas y deduplicadas."""

    def __init__(self):
        self._sent_hashes: set = set()
        self._notification_log: List[Dict[str, Any]] = []

    def send_tagged_notification(
        self,
        tag: str,  # "BACKTEST", "SHADOW", "PAPER"
        title: str,
        details: Dict[str, Any]
    ) -> bool:
        if tag not in ("BACKTEST", "SHADOW", "PAPER"):
            raise ValueError(f"Tag inválido: {tag}. Debe ser [BACKTEST], [SHADOW] o [PAPER].")

        # Generar hash de deduplicación basado en título y timestamp minuto
        minute_slot = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        dedup_raw = f"{tag}:{title}:{minute_slot}:{details.get('strategy_id', '')}:{details.get('symbol', '')}"
        dedup_hash = hashlib.sha256(dedup_raw.encode("utf-8")).hexdigest()

        if dedup_hash in self._sent_hashes:
            logger.info(f"Notificación duplicada evitada: {dedup_hash}")
            return False

        lines = [
            f"🔔 *[{tag}] — {title}*",
            f"• *Timestamp:* `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}`"
        ]
        for k, v in details.items():
            lines.append(f"• *{k.replace('_', ' ').title()}:* `{v}`")

        msg = "\n".join(lines)

        self._sent_hashes.add(dedup_hash)
        self._notification_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tag": tag,
            "title": title,
            "details": details,
            "dedup_hash": dedup_hash
        })

        # Envío síncrono outbound seguro a través de telegram_notifier configurado
        try:
            return telegram_notifier.send_message_sync(msg)
        except Exception as e:
            logger.warning(f"Error emitiendo notificación Telegram [{tag}]: {e}")
            return False
