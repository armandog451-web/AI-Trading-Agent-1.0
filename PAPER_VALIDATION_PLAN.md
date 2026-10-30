# PLAN DE VALIDACIÓN PAPER Y CONDICIONES DE ACTIVACIÓN — ORACLEBOT V2

**Estrategias Objeto:** `ORB_INTRADAY_BREAKOUT_V1` y `ORB_SWING_PULLBACK_V1`  
**Entorno Autorizado:** `SHADOW` (Simulación en memoria sin transmisión externa)  
**Entorno Restringido:** `PAPER_BROKER` (Alpaca Paper / Moomoo Simulate)  
**Entorno Prohibido:** `LIVE` (Mercados Reales con Capital Real)  

---

## 1. ESTADO ACTUAL Y CONDICIÓN DE ARRANQUE

Por defecto, ambas estrategias operan en modo **`SHADOW`**.
- Las señales generadas quedan registradas en el diario criptográfico inmutable (`EvidenceJournal`).
- No se envían órdenes al socket ni a la API de ningún broker paper.

---

## 2. PUERTAS DE CONTROL REQUERIDAS ANTES DE ACTIVAR `PAPER_BROKER`

Para que el operador humano pueda autorizar la transición de `SHADOW` a `PAPER_BROKER`:

1. **Ampliación de Muestra:** Se debe realizar una campaña de exploración con parámetros ligeramente flexibilizados para alcanzar $\ge 100\text{ operaciones}$ totales y $\ge 30\text{ operaciones fuera de muestra}$.
2. **Estabilidad OOS:** El Sharpe ratio en Out-of-Sample debe ser $\ge 0.80 \times \text{Sharpe Train}$ y la Expectancy debe ser positiva tras costes 2x.
3. **Validación de Fidelidad:** Ejecutar 60 sesiones consecutivas en modo `SHADOW` comparando precios de fill virtuales con el libro de órdenes observado mediante `FidelityEngine`. El score de fidelidad debe ser $\ge 90\%$.
4. **Aprobación Humana Explícita:** Se prohíbe la transición autónoma sin confirmación firmada en el diario de auditoría.

---

## 3. PROTOCOLO DE DESPLIEGUE EN `PAPER_BROKER`

Cuando sea autorizado por el usuario:
- Se asignará una sub-cuenta virtual de papel con $\$200,000\text{ USD}$ asignados de los $\$1,000,000\text{ USD}$ del profile.
- Cada orden enviará un `client_order_id` prefijado con el `strategy_id` para garantizar que nunca se confundan con las órdenes de D21.
- Moomoo OpenD se ejecutará exclusivamente con el flag `TrdEnv.SIMULATE`.
- Alpaca operará exclusivamente contra `paper-api.alpaca.markets`.
- El endpoint real estará bloqueado a nivel de transporte (`PaperBrokerSecurityGuard`).
