# POLÍTICA DE RIESGO DE CARTERA COMPARTIDA — ORACLEBOT V2

**Ámbito de Aplicación:** Consolidado conjunto de `ORB_INTRADAY_BREAKOUT_V1` y `ORB_SWING_PULLBACK_V1`  
**Base Contable de Referencia:** $1,000,000 USD (Paper Account Profile)  
**Autoridad de Riesgo:** `PortfolioRiskEngine`  

---

## 1. PARÁMETROS DETERMINISTAS Y LÍMITES CONSOLIDADOS

Los siguientes límites son comunes a toda la cartera y no pueden ser relajados por ninguna estrategia candidata:

| Métrica de Control | Límite Máximo Permitido | Monto Nocional ($1,000,000 USD) | Acción ante Incumplimiento |
| :--- | :--- | :--- | :--- |
| **Riesgo Unitario por Trade** | $0.25\%$ del equity | $\$2,500\text{ USD}$ ($1.0\text{R}$) | Reducción de tamaño o rechazo de propuesta |
| **Riesgo Abierto Agregado** | $0.50\%$ del equity | $\$5,000\text{ USD}$ ($2.0\text{R}$) | Bloqueo estricto de nuevas reservas |
| **Exposición Máxima por Acción** | $5.0\%$ del equity | $\$50,000\text{ USD}$ | Capping determinista de cantidad |
| **Exposición Máxima por Sector** | $20.0\%$ del equity | $\$200,000\text{ USD}$ | Bloqueo de compras adicionales del sector |
| **Límite Pérdida Diaria (Daily Loss)** | $2.0\text{R}$ | $\$5,000\text{ USD}$ | **CIRCUIT BREAKER DIARIO:** Pausa hasta siguiente día |
| **Límite Pérdida Semanal** | $5.0\text{R}$ | $\$12,500\text{ USD}$ | **CIRCUIT BREAKER SEMANAL:** Bloqueo semanal |
| **Drawdown Máximo de Campaña** | $5.0\%$ desde High Water Mark | $\$50,000\text{ USD}$ | **KILL SWITCH TOTAL:** Requiere intervención humana |
| **Apalancamiento Permitido** | $1:1$ (Cash Equity puro) | Sin endeudamiento | Rechazo de órdenes que requieran margen |
| **Shorts / Opciones / Derivados** | **ESTRICTAMENTE PROHIBIDOS** | $0\text{ USD}$ | Bloqueo en capa de validación Pydantic |

---

## 2. FÓRMULA DE DIMENSIONAMIENTO DETERMINISTA DE POSICIÓN

$$\text{Presupuesto de Riesgo} = \text{Equity} \times 0.0025 \quad (= \$2,500\text{ USD})$$
$$\text{Riesgo Unitario Estimado} = |\text{Entry} - \text{Stop}| + \text{Cost Buffer} \quad (\text{Cost Buffer} = \$0.05/\text{acc})$$
$$\text{Cantidad}_{\text{riesgo}} = \left\lfloor \frac{\text{Presupuesto de Riesgo}}{\text{Riesgo Unitario Estimado}} \right\rfloor$$

$$\text{Cantidad}_{\text{final}} = \min \left( \text{Cantidad}_{\text{riesgo}}, \text{Cantidad}_{\text{stock\_5\%}}, \text{Cantidad}_{\text{sector\_20\%}}, \text{Cantidad}_{\text{liquidez}}, \text{Cantidad}_{\text{cash}} \right)$$

> Si $\text{Cantidad}_{\text{final}} < 1$, la orden es rechazada inmediatamente.

---

## 3. PROTOCOLO DE RESOLUCIÓN DE CONFLICTOS ENTRE ESTRATEGIAS

1. **Unicidad de Activo:** Ambas estrategias no pueden mantener posiciones simultáneas sobre el mismo símbolo. La primera señal aprobada bloquea el activo.
2. **Registro Central de Reservas:** Toda señal aprobada registra un `RiskReservation` con bloqueo de hilo (`threading.Lock`), impidiendo condiciones de carrera cuando se reciben señales en la misma barra.
3. **Prioridad Absoluta de la Cartera:** Los límites consolidados de $5\%$ por acción y $20\%$ por sector se imponen jerárquicamente sobre las señales individuales.
4. **Resistencia a Inconsistencias:** Si se detecta una orden pendiente no reconciliada o desconexión con el broker, se activa la parada preventiva y se rechazan todas las nuevas propuestas.
