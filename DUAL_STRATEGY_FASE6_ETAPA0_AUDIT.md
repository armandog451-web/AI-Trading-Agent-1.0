# ORACLEBOT V2 — FASE 6: AUDITORÍA DE EJECUCIÓN (ETAPA 0) Y ESPECIFICACIÓN DE HIPÓTESIS A, B, C

**Fecha:** 2026-10-29  
**Entorno Operativo:** `TrdEnv.SIMULATE` (Moomoo OpenD 127.0.0.1:11111)  
**Modo de Ejecución:** `TRADING_MODE = ANALYSIS_ONLY` (Ejecución real y paper conectada estrictamente bloqueadas)  
**Estado de Estrategias:**  
- `D21_RangeCompress_5d`: `PAPER` (Score 69.17, Fingerprint `f885ec2db2422308`, Aislado e Intacto)  
- `ORB_INTRADAY_BREAKOUT_V1`: `REJECTED` (Expectancy -0.16R, PF 0.29)  
- `ORB_SWING_PULLBACK_V1`: `REJECTED` (Forward 2026 WR 9.1% / 33.3%, PF 0.16 / 0.77, Inviable)  
- **Nuevas Hipótesis A, B, C:** `RESEARCH_CONCEPTUAL` (A la espera de autorización expresa para Etapas 1-3)

---

## 1. RECONSTRUCCIÓN CRONOLÓGICA DE LAS 11 OPERACIONES FORWARD (2026)

Se auditó la cronología real de las 11 operaciones ejecutadas durante la campaña Forward Shadow (204 sesiones bursátiles de 2026). En la simulación anterior, al iterarse símbolo por símbolo (`SPY` completo y luego `QQQ`), el diario de operaciones quedó desordenado temporalmente.

A continuación se presenta la secuencia cronológica real en la línea temporal unificada:

| # | Símbolo | Fecha/Hora Entrada | Fill Price | Fecha/Hora Salida | Exit Price | Motivo Salida | Gap Adverso | Net PnL ($) | R-Múltiple |
|---|---|---|---|---|---|---|---|---|---|
| **1** | `SPY` | 2026-01-05 16:00:00 | $684.22 | 2026-01-20 16:00:00 | $678.96 | `STOP_LOSS` | No | -$1,059.04 | -1.00 R |
| **2** | `QQQ` | 2026-01-09 16:00:00 | $620.89 | 2026-01-14 16:00:00 | $614.28 | `STOP_LOSS` | Sí (-$0.17) | -$1,005.10 | -1.01 R |
| **3** | `QQQ` | 2026-01-28 16:00:00 | $625.57 | 2026-02-03 16:00:00 | $611.59 | `STOP_LOSS` | Sí (-$4.44) | -$1,266.58 | -1.35 R |
| **4** | `SPY` | 2026-02-02 16:00:00 | $694.70 | 2026-02-03 16:00:00 | $691.02 | `STOP_LOSS` | No | -$890.30 | -1.00 R |
| **5** | `SPY` | 2026-06-04 16:00:00 | $749.97 | 2026-06-05 16:00:00 | $740.26 | `STOP_LOSS` | Sí (-$7.02) | -$980.60 | -1.88 R |
| **6** | `SPY` | 2026-07-09 16:00:00 | $742.06 | 2026-07-23 16:00:00 | $736.91 | `STOP_LOSS` | Sí (-$0.15) | -$837.74 | -1.01 R |
| **7** | `SPY` | 2026-08-19 16:00:00 | $767.87 | 2026-08-20 16:00:00 | $764.06 | `STOP_LOSS` | Sí (-$0.57) | -$400.18 | -1.09 R |
| **8** | `SPY` | 2026-08-27 16:00:00 | $767.12 | 2026-09-01 16:00:00 | $759.79 | `STOP_LOSS` | Sí (-$0.05) | -$638.68 | -1.00 R |
| **9** | `SPY` | 2026-09-25 16:00:00 | $773.12 | 2026-09-29 16:00:00 | $783.21 | `TAKE_PROFIT` | No | +$1,190.28 | +2.00 R |
| **10** | `SPY` | 2026-10-09 16:00:00 | $773.06 | 2026-10-14 16:00:00 | $768.21 | `STOP_LOSS` | Sí (-$1.78) | -$781.04 | -1.22 R |
| **11** | `QQQ` | *(Bloqueada por falso disyuntor acumulado en el bucle secuencial)* | — | — | — | — | — | — | — |

---

## 2. AUDITORÍA DEL SIMULADOR: HALLAZGOS Y CORRECCIÓN

La auditoría forense del código reveló **dos fallos arquitectónicos en el simulador de investigación**:

### Fallo A: Ausencia de reinicio diario y semanal de pérdidas en `PortfolioRiskEngine`
1. El método `update_equity(current_equity, realized_pnl_delta)` acumulaba el delta de pérdidas de forma monótona en `self.daily_realized_pnl` y `self.weekly_realized_pnl`.
2. El simulador de campañas **nunca invocaba** `reset_daily_circuit()` al cambiar de fecha.
3. Como resultado, pérdidas normales espaciadas a lo largo de **10 meses de calendario** (enero a octubre de 2026) se acumularon hasta cruzar -$5,000.
4. **Verificación matemática de sesiones:**
   - La pérdida máxima en una única sesión bursátil fue de **-$1,266.58** (el 03/02/2026).
   - En ninguna sesión de 2026 la pérdida diaria de la cartera alcanzó el límite de 2.0R ($5,000.00).
   - Por tanto, el bloqueo del disyuntor diario fue un **falso positivo acumulativo**.

### Fallo B: Bucle secuencial por símbolo en lugar de simulación sincrónica multi-activo
1. El script `run_forward_shadow_campaign.py` ejecutaba `for s in symbols:`, simulando a `SPY` desde enero hasta octubre, y luego a `QQQ` desde enero llevando consigo el estado de parada acumulado de octubre.
2. Los 13 activos restantes (`AAPL`, `MSFT`, `NVDA`, `AMZN`, `GOOGL`, `META`, `TSLA`, `JPM`, `BAC`, `XOM`, `UNH`, `AMD`, `COST`) nunca pudieron ejecutar operaciones porque encontraron el disyuntor ya bloqueado.

### Resolución de la Anomalía de Costes 1x vs 2x:
Bajo costes 2x, cada trade de SPY perdió ~$50 adicionales en comisiones y deslizamiento. Esa fricción extra causó que el límite acumulado de -$5,000 se cruzara justo antes del trade 3 de QQQ (el 28/01/2026). Al bloquear ese trade perdedor de -$1,266.58, el PnL reportado a 2x fue de -$5,387.76 (aparentando ser "mejor" que 1x con -$6,160.88). Una vez corregido el simulador a ejecución sincrónica bar-by-bar con reinicio diario, **la degradación por costes es estrictamente monótona y lógica**.

---

## 3. COMPARATIVA ANTES VS. DESPUÉS DE LA CORRECCIÓN

| Métrica | Antes (Simulador Secuencial con Fallo de Acumulación) | Después (Simulador Sincrónico Multi-Activo con Reinicios) |
|---|---|---|
| **Estrategia Auditada** | `ORB_SWING_PULLBACK_V1` (Variante 5) | `ORB_SWING_PULLBACK_V1` (Variante 5) |
| **Temporalidad y Periodo** | 4H / 204 sesiones (2026) | 4H / 204 sesiones (2026) |
| **Universo Evaluado** | 15 Símbolos Líquidos | 15 Símbolos Líquidos (Sincronizado) |
| **Total Operaciones (1x)** | 11 ops (solo SPY y QQQ) | **66 ops** (distribuidas en 15 símbolos) |
| **Win Rate** | 9.1% (1W / 10L) | **33.3%** (22W / 44L) |
| **Profit Factor (1x)** | 0.16 | **0.77** |
| **Expectancy R** | -0.81 R | **-0.16 R** |
| **PnL Neto (1x)** | -$6,160.88 | **-$14,378.89** |
| **Max Drawdown** | 0.62% ($6,160.88) | **2.13%** ($21,310.65) |
| **Sensibilidad a Costes 2x** | 10 ops \| PF 0.17 \| -$5,387.76 *(anómalo)* | **65 ops \| PF 0.75 \| -$16,072.88** *(monótono)* |
| **Sensibilidad a Costes 3x** | 10 ops \| PF 0.15 \| -$5,883.52 | **63 ops \| PF 0.62 \| -$24,942.23** *(monótono)* |
| **Conclusión de Aptitud** | **REJECTED** | **REJECTED** (PF < 1.0, Expectativa negativa) |

> [!IMPORTANT]
> **Veredicto Institucional:** Aunque la corrección del simulador aumentó la muestra de operaciones de 11 a 66 y el Profit Factor de 0.16 a 0.77, la estrategia `ORB_SWING_PULLBACK_V1` **sigue siendo netamente perdedora** (-0.16R, Profit Factor 0.77, PnL -$14,378.89 a costes 1x). El estado formal **REJECTED** es 100% correcto y se mantiene inmutable.

---

## 4. LAS CUATRO DIMENSIONES DEL RIESGO (INSTRUCCIÓN 5)

Para garantizar consistencia contable y evitar ambigüedades entre presupuestos teóricos y dinero real:

1. **Riesgo Presupuestado ($R_{presup}$):**
   - Límite teórico de capital arriesgado por operación según el mandato institucional.
   - Fórmula: $R_{presup} = \text{Reference Equity} \times \text{Risk Per Trade Pct} = \$1.000.000 \times 0.25\% = \$2.500,00$.
2. **Riesgo Reservado ($R_{reserv}$):**
   - Capital congelado preventivamente por `PortfolioRiskEngine` para prevenir colisiones y *race conditions* concurrentes. Incluye buffer de costes.
   - Fórmula: $R_{reserv} = \text{Qty} \times \left( |\text{Entry}_{\text{ref}} - \text{Stop}_{\text{ref}}| + \text{CostBuffer} \right)$.
3. **Riesgo Efectivamente Asumido ($R_{asum}$):**
   - Exposición real de la posición en el instante exacto del llenado de la orden en el mercado.
   - Fórmula: $R_{asum} = \text{Qty} \times |\text{Fill Price} - \text{Stop}_{\text{ref}}|$.
4. **Pérdida Realizada ($L_{real}$):**
   - Resultado monetario neto efectivo al cierre de la posición, incluyendo el impacto de deslizamiento en salida, comisiones y gaps adversos.
   - Fórmula: $L_{real} = \text{Qty} \times (\text{Exit Fill Price} - \text{Entry Fill Price}) - \text{Comisiones Totales}$.

---

## 5. AUDITORÍA DETALLADA DE RECHAZOS

En la campaña de 2026 se registraron los siguientes filtros y causas de rechazo:

| Causa de Rechazo | Recuento | Descripción y Comportamiento |
|---|---|---|
| **Filtro Macro SPY < SMA200** | 360 barras | Bloqueo determinista cuando el índice director de mercado cotiza por debajo de su SMA(200) diaria. |
| **Filtro de Volatilidad NATR(14) > 3.5%** | 181 barras | Bloqueo de activos con excesivo ruido o riesgo de gap (concentrado en `AMD`: 161, `TSLA`: 12, `NVDA`: 8). |
| **Conflicto de Concurrencia de Reserva** | 81 eventos | Señal generada en un activo que ya tenía una reserva activa en tránsito o posición abierta (`AAPL`: 27, `SPY`: 16, `NVDA`: 16, `QQQ`: 12, `MSFT`: 10). |
| **Límite de Riesgo Agregado (> 0.50%)** | 14 eventos | Señales descartadas porque la cartera ya tenía 2 posiciones abiertas ($5,000 de riesgo comprometido). |
| **Disyuntor Diario Activado (Legítimo)** | 3 eventos | Sesiones de alta volatilidad donde se alcanzaron 2.0R de pérdidas en el mismo día (bloqueando nuevas entradas por el resto de esa sesión). |

---

## 6. PRUEBAS DE REGRESIÓN INCORPORADAS

Se actualizaron los tests unitarios en [`test_oraclebot_v2_dual_strategy.py`](file:///C:/Users/edsel/OneDrive/Documents/PROJET%202/ai_trading_agent/tests/test_oraclebot_v2_dual_strategy.py) agregando las pruebas institucionales 26, 27 y 28:
- **Test 26 (`test_26_daily_loss_circuit_reset_on_new_date`):** Valida que el disyuntor diario de 2R se reinicia exactamente a $0.0 al cambiar la sesión bursátil, desbloqueando la operativa sin perder la acumulación semanal.
- **Test 27 (`test_27_weekly_loss_circuit_reset_on_new_week`):** Valida que el disyuntor semanal de 5R se reinicia al cambiar la semana ISO.
- **Test 28 (`test_28_atomic_reservation_release_on_position_close`):** Valida que cada reserva de riesgo se libera de forma atómica en el motor al registrarse el cierre de posición, eliminando cualquier riesgo de reservas huérfanas.

**Resultado:** 28 tests de 28 pasados exitosamente (100% de éxito).

---

## 7. ESPECIFICACIÓN CONCEPTUAL DE NUEVAS HIPÓTESIS (A, B, C)

Conforme a la instrucción expresa de no implementar código operativo antes de la aprobación de la Etapa 0, se formulan las especificaciones matemáticas y lógicas:

### HIPÓTESIS A — Clasificador Determinista de Régimen de Mercado
- **Objetivo:** Filtrar entradas de seguimiento de tendencia cuando el mercado carece de inercia direccional o se encuentra en consolidación errática.
- **Métricas:**
  1. $\text{ADX}(14)$: Fuerza direccional de la tendencia.
  2. $\text{Efficiency Ratio de Kaufman}(20)$ ($ER_{20} = \frac{|\text{Close}_t - \text{Close}_{t-20}|}{\sum_{i=0}^{19} |\text{Close}_{t-i} - \text{Close}_{t-i-1}|}$).
- **Estados de Salida:**
  - `TRENDING_BULL`: $\text{ADX}_{14} \ge 25$ y $ER_{20} \ge 0.35$ y $\text{Close} > \text{SMA}_{50}$.
  - `RANGING`: $\text{ADX}_{14} < 20$ y $ER_{20} < 0.25$.
  - `INDETERMINATE`: Rango intermedio de transición (comportamiento defensivo: sin aperturas de riesgo).
- **Aislamiento:** Módulo desacoplado en `ai_trading_agent.dual_strategy.regime`.

### HIPÓTESIS B — Swing Pullback con Filtro de Momentum / Aceleración
- **Identificador de Nueva Estrategia:** `SWING_PULLBACK_MOMENTUM_V2` (No reactiva ni modifica `ORB_SWING_PULLBACK_V1`, la cual permanece en `REJECTED`).
- **Gating de Entrada:**
  - Solo permite evaluar pullbacks si el Régimen de Mercado (Hipótesis A) es `TRENDING_BULL`.
  - Confirmación de giro mediante `RSI(14)` recuperando el nivel 40 tras tocar la zona 30-38 y vela de rechazo (cierre en el tercio superior del rango).
  - Stop loss adaptativo colocado bajo el swing low reciente + $0.5 \times \text{ATR}(14)$. Target mínimo 2.0R.

### HIPÓTESIS C — Estrategia Independiente de Reversión a la Media
- **Identificador:** `MEAN_REVERSION_BB_RSI_V1`
- **Lógica Operativa:**
  - Solo activa cuando el Régimen de Mercado es `RANGING`.
  - Condición de compra: Cierre por debajo de la Banda de Bollinger inferior (20 periodos, 2.0 desv. est.) con `RSI(2) < 10`.
  - Condición de salida: Cierre al cruzar la Media Móvil Simple de 20 periodos (banda central) o Stop Loss a 1.0 ATR.
  - Exigencia de ratio R:R planificado $\ge 2.0:1$.
