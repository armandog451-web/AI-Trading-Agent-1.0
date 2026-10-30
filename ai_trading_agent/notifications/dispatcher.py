"""
ai_trading_agent.notifications.dispatcher
=========================================
Despachador pasivo y desacoplado de notificaciones para Telegram.
Implementa:
- Deduplicación estricta por evento y hash.
- Rate limiting por severidad (INFO/LOW suprimidos o agrupados, HIGH/CRITICAL emitidos).
- Política de reintentos finita (máx 3 intentos con backoff) sin loops infinitos.
- Fail-safe absoluto: cualquier falla en Telegram NO afecta la ejecución del trading core.
- UNIDIRECCIONAL: Sin handlers de comandos inbound ni interfaces hacia el broker.
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional
import httpx

from ai_trading_agent.config.settings import settings
from ai_trading_agent.notifications.models import ObservabilityEvent, NotificationSeverity, NotificationType
from ai_trading_agent.notifications.formatter import TelegramMessageFormatter
from ai_trading_agent.notifications.journal import NotificationJournal

logger = logging.getLogger(__name__)


class TelegramDispatcher:
    """Despachador pasivo hacia la API de Telegram con salvaguardas de producción."""

    def __init__(self, journal: Optional[NotificationJournal] = None):
        self.journal = journal or NotificationJournal()
        self._sent_event_hashes: Dict[str, float] = {}  # hash -> timestamp
        self._dedup_window_seconds = 300.0  # 5 minutos para deduplicar eventos idénticos
        self._max_retries = 3
        self._online_notified = False

    def _generate_event_fingerprint(self, event: ObservabilityEvent) -> str:
        """Crea una clave determinista para evitar spam repetitivo del mismo evento."""
        key = (
            f"{event.strategy_id}:{event.event_type.value}:{event.severity.value}:"
            f"{event.signal_id or ''}:{event.order_id or ''}:{event.title}"
        )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _should_suppress_rate_limit(self, event: ObservabilityEvent, fp: str) -> bool:
        """Aplica las reglas de rate-limiting y deduplicación por severidad."""
        now = time.time()

        # Críticos nunca se suprimen por tiempo a menos que sea literalmente idéntico en < 30 seg
        if event.severity == NotificationSeverity.CRITICAL:
            if fp in self._sent_event_hashes and (now - self._sent_event_hashes[fp]) < 30.0:
                return True
            return False

        # Evento ONLINE: una sola vez
        if event.event_type == NotificationType.SYSTEM_ONLINE:
            if self._online_notified:
                return True
            return False

        # Severidad LOW: no se envía por Telegram salvo configuración explícita
        if event.severity == NotificationSeverity.LOW:
            return True

        # INFO / MEDIUM / HIGH: comprobar ventana de deduplicación
        if fp in self._sent_event_hashes:
            elapsed = now - self._sent_event_hashes[fp]
            if elapsed < self._dedup_window_seconds:
                return True

        return False

    def dispatch(self, event: ObservabilityEvent) -> bool:
        """
        Envía un evento a Telegram.
        FAIL-SAFE DESIGN:
        Cualquier excepción o falla de red es capturada y registrada;
        NUNCA arroja excepción ni propaga errores al trading core.
        """
        fp = self._generate_event_fingerprint(event)
        message_text = TelegramMessageFormatter.format_event(event)
        message_hash = hashlib.sha256(message_text.encode("utf-8")).hexdigest()

        # 1. Comprobar rate limit / deduplicación
        if self._should_suppress_rate_limit(event, fp):
            self.journal.record_notification(
                notification_id=event.event_id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                message_hash=message_hash,
                delivery_status="SUPPRESSED_DEDUPLICATED",
                retry_count=0
            )
            return False

        # 2. Comprobar si Telegram está configurado y habilitado
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        is_enabled = getattr(settings, "TELEGRAM_ENABLED", False)

        if not (bot_token and chat_id and is_enabled):
            self.journal.record_notification(
                notification_id=event.event_id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                message_hash=message_hash,
                delivery_status="DISABLED_OR_UNCONFIGURED",
                retry_count=0
            )
            return False

        # 3. Envío con reintentos finitos y timeout seguro
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }

        success = False
        last_code = None
        last_error = None

        for attempt in range(1, self._max_retries + 1):
            try:
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, json=payload)
                    last_code = resp.status_code
                    if resp.status_code == 200:
                        success = True
                        break
                    elif resp.status_code == 400:
                        # Fallback a texto plano si Markdown tiene caracteres especiales
                        payload.pop("parse_mode", None)
                        fallback_resp = client.post(url, json=payload)
                        last_code = fallback_resp.status_code
                        if fallback_resp.status_code == 200:
                            success = True
                            break
            except Exception as e:
                last_error = str(e)
                time.sleep(0.5 * (2 ** (attempt - 1)))  # Exponential backoff ligero

        # 4. Actualizar estado de deduplicación y Journal
        if success:
            self._sent_event_hashes[fp] = time.time()
            if event.event_type == NotificationType.SYSTEM_ONLINE:
                self._online_notified = True

        status_str = "DELIVERED" if success else "NOTIFICATION_FAILED"
        self.journal.record_notification(
            notification_id=event.event_id,
            event_type=event.event_type.value,
            severity=event.severity.value,
            message_hash=message_hash,
            delivery_status=status_str,
            retry_count=attempt if not success else attempt - 1,
            telegram_response_code=last_code,
            error_message=last_error
        )

        return success


telegram_dispatcher = TelegramDispatcher()
