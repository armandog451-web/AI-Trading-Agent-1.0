# DUAL STRATEGY SIGNAL DIAGNOSTIC & DATA AUDIT REPORT
**Fecha:** 2026-10-29  
**Proyecto:** OracleBot v2 — Dual Strategy Research  
**Estrategias:** `ORB_INTRADAY_BREAKOUT_V1` & `ORB_SWING_PULLBACK_V1`  
**Autor:** Antigravity AI  
**Estado:** AUDITORÍA FASE A COMPLETADA — EVIDENCIA DIAGNOSTICADA

---

## 1. Naturaleza y Calidad de los Datos Evaluados

### 1.1 Distinción de Datos: Sintéticos vs. Históricos Reales
- **Datos de la Fase Previa:** Los 5 años comunicados previamente (1.200 días bursátiles) fueron generados de forma **100% sintética** mediante el método determinista `generate_controlled_multitimeframe_dataset` (Movimiento Browniano Geométrico con sesgo alcista y volatilidad parametrizada).
- **Anomalía en Deriva Sintética Detectada:** En el generador sintético previo, el parámetro `trend_bias` (0.0004) se aplicaba a cada barra de 15 minutos en lugar de escalarse por las 26 barras de la sesión. Esto generó un efecto de capitalización exponencial no realista a lo largo de 31.200 barras, elevando artificialmente el precio nominal de los activos tras varios años simulados.
- **Capacidad de Moomoo OpenD:** Moomoo OpenD (`127.0.0.1:11111`) dispone de histórico real con ajuste de splits y dividendos (`ft.AuType.QFQ`) en temporalidades `K_DAY`, `K_240M`, `K_60M` y `K_15M`. Sin embargo, la cuenta tiene una cuota de 100 peticiones históricas detalladas por mes.

### 1.2 Auditoría del Agregador de 4 Horas y Sesiones Bursátiles
- **Estructura de la Sesión Regular (EE. UU.):** El horario regular de negociación en NYSE/NASDAQ es de 09:30 a 16:00 ET (6,5 horas de duración total).
- **Incompatibilidad Matemática de Bloques de 4 Horas:** En 6,5 horas de sesión continua es matemáticamente imposible acomodar dos velas de 4 horas completas.
- **Alineación con Moomoo OpenD:** Se auditó la respuesta nativa de Moomoo OpenD para `KLType.K_240M`:
  - Barra 1: 09:30 a 13:30 ET (4 horas).
  - Barra 2: 13:30 a 16:00 ET (2,5 horas, normalizada como vela de cierre de sesión).
- **Conclusión de Agregación:** El agregador `aggregate_4h_bars` en `MarketDataProvider` replica exactamente la partición oficial de Moomoo OpenD.

---

## 2. El Hallazgo Crítico: Causa Raíz de la Escasez de Operaciones

### 2.1 El "Bloqueo Permanente de Reserva de Riesgo" (Engine Reservation Bug)
Se descubrió por qué la campaña inicial produjo únicamente 5 operaciones en Intradía y 4 en Swing (exactamente 1 operación por símbolo):
1. Cuando una señal es aprobada por `PortfolioRiskEngine.evaluate_and_size_proposal`, el motor crea un registro `RiskReservation` con estado `ACTIVE` para evitar colisiones atómicas.
2. En `DualStrategyOrchestrator.run_backtest_intraday` y `run_backtest_swing`, al cerrarse la posición simulada (por Take Profit, Stop Loss o Fin de Sesión), **nunca se invocaba `risk_engine.release_reservation(reservation_id)` ni `commit_reservation`**.
3. Debido a esto, la reserva permanecía en estado `ACTIVE` indefinidamente.
4. Para todas las barras futuras de los 5 años restantes, cualquier señal posterior en ese símbolo era rechazada con:
   ```text
   Conflicto de concurrencia: Existe una reserva activa en curso para {symbol}
   ```
5. Esto congeló permanentemente cada acción tras su primera operación en la partición Train, impidiendo la ejecución de cualquier operación en Validation y Test.

---

## 3. Diagnóstico de Embudo por Filtro (Filter Attribution Funnel)

Se auditó el comportamiento de cada regla algorítmica sobre las **155.875 barras de 15m** y **11.700 barras de 4h** correspondientes a 1.200 sesiones sobre los 5 activos de referencia.

### 3.1 Embudo Intradía (`ORB_INTRADAY_BREAKOUT_V1`)

| Etapa del Filtro | Condición Evaluada | Barras que Pasan (Secuencial) | Retención Relativa | Aprobación Independiente |
| :--- | :--- | :---: | :---: | :---: |
| **Población Total** | Todas las barras de 15m (1.200 días x 5 activos) | 155.875 | 100,00% | 100,00% |
| **Ventana Operativa** | Sesión regular 10:00 - 15:00 ET | 125.895 | 80,77% | 80,77% |
| **Tendencia 1H** | EMA20(1h) > EMA50(1h) y Cierre(1h) > EMA20(1h) | 109.058 | 86,63% | 86,65% |
| **Ruptura Donchian** | Cierre(15m) > Máximo previo de 20 barras | **8.199** | **7,52%** | **6,68%** |
| **Volumen Relativo** | Volumen barra $\ge 1,5 \times$ SMA20 volumen | **1.011** | **12,33%** | **12,07%** |
| **Cuerpo de Vela** | Rango del cuerpo $\ge 50\%$ del rango total | 460 | 45,50% | 21,40% |
| **Cierre Cuartil Superior** | Cierre en el 25% superior de la vela | 323 | 70,22% | 23,80% |
| **Stop y R:R Válido** | Stop $\ge 0,05\$$, ratio proyectado $\ge 2:1$ | **323** | **100,00%** | **100,00%** |

#### Conclusiones de Intradía:
- Los dos filtros más estrangulantes son la **Ruptura de Donchian de 20 barras** (filtra el 93,3% de las barras) y el **RVOL $\ge 1,5$** (filtra el 87,7% restante).
- A pesar de la severidad, se generaron **323 señales válidas** que habrían generado 36 operaciones en SPY Train si no se hubiera producido el bloqueo de la reserva de riesgo.

---

### 3.2 Embudo Swing (`ORB_SWING_PULLBACK_V1`)

| Etapa del Filtro | Condición Evaluada | Barras que Pasan (Secuencial) | Retención Relativa | Aprobación Independiente |
| :--- | :--- | :---: | :---: | :---: |
| **Población Total** | Todas las barras de 4h (1.200 días x 5 activos) | 11.700 | 100,00% | 100,00% |
| **Tendencia Diaria** | EMA50(1D) > EMA200(1D), Cierre > EMA50, Pendiente > 0 | 9.895 | 84,57% | 84,57% |
| **Toque EMA20 (4h)** | Toque o cruce de EMA20 en las últimas 5 barras | **1.199** | **12,12%** | **12,09%** |
| **Estabilidad EMA50** | Ningún cierre $< \text{EMA50}$ en las últimas 5 barras | 1.189 | 99,17% | 99,91% |
| **Cierre > High Previo** | Vela de reacción supera el máximo anterior | **383** | **32,21%** | **40,41%** |
| **Cierre > EMA20** | Cierre de confirmación por encima de EMA20 | 381 | 99,48% | 98,22% |
| **Stop y R:R Válido** | Stop bajo mínimo de 5 barras $- 0,1 \times \text{ATR}$, R:R $\ge 2:1$ | **381** | **100,00%** | **100,00%** |

#### Conclusiones de Swing:
- El filtro más restrictivo es el **Toque de EMA20 en las últimas 5 barras** (rechaza el 87,9% de las barras en tendencia).
- El segundo filtro limitante es la exigencia de que el cierre supere el **Máximo de la barra anterior** (rechaza el 67,8% adicional).
- Se produjeron **381 señales Swing válidas** a nivel de motor.

---

## 4. Auditoría Forense de las 9 Operaciones Previas

### 4.1 Cronología de Operaciones Ejecutadas en la Fase Anterior

#### Intradía (5 operaciones):
1. **SPY:** Entrada 2021-03-26 10:30 ET @ \$216.10, Salida 16:00 ET @ \$213.59 | PnL: -\$580.97 (-0.56R) | Causa: `SESSION_SQUARE_OFF`
2. **QQQ:** Entrada 2021-04-16 11:30 ET @ \$336.56, Salida 16:00 ET @ \$334.80 | PnL: -\$375.40 (-0.38R) | Causa: `SESSION_SQUARE_OFF`
3. **AAPL:** Entrada 2021-05-18 10:15 ET @ \$263.85, Salida 16:00 ET @ \$265.20 | PnL: +\$175.20 (+0.18R) | Causa: `SESSION_SQUARE_OFF`
4. **MSFT:** Entrada 2021-06-08 14:00 ET @ \$312.40, Salida 16:00 ET @ \$310.90 | PnL: -\$210.50 (-0.21R) | Causa: `SESSION_SQUARE_OFF`
5. **NVDA:** Entrada 2021-07-02 10:45 ET @ \$418.90, Salida 11:45 ET @ \$412.10 | PnL: -\$726.83 (-1.05R) | Causa: `STOP_LOSS`

#### Swing (4 operaciones):
1. **SPY:** Entrada 2022-03-24 12:30 ET @ \$3,003.39, Salida 2022-04-04 16:00 ET @ \$3,193.96 | PnL: +\$3,048.12 (+2.00R) | Causa: `TAKE_PROFIT`
2. **QQQ:** Entrada 2022-05-17 12:30 ET @ \$28,856.15, Salida 2022-05-24 12:30 ET @ \$32,693.98 | PnL: +\$3,836.83 (+2.00R) | Causa: `TAKE_PROFIT`
3. **AAPL:** Entrada 2021-12-10 12:30 ET @ \$1,939.85, Salida 2021-12-17 12:30 ET @ \$2,047.74 | PnL: +\$2,696.25 (+2.00R) | Causa: `TAKE_PROFIT`
4. **NVDA:** Entrada 2021-10-28 16:00 ET @ \$3,285.55, Salida 2021-11-10 16:00 ET @ \$3,631.16 | PnL: +\$4,837.54 (+2.00R) | Causa: `TAKE_PROFIT`

### 4.2 Verificación del Profit Factor de 99.00 en Swing
- Se inspeccionó la línea 55 de [`ai_trading_agent/dual_strategy/metrics.py`](file:///c:/Users/edsel/OneDrive/Documents/PROJET%202/ai_trading_agent/dual_strategy/metrics.py#L55):
  ```python
  profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)
  ```
- **Conclusión Indiscutible:** Al no existir operaciones perdedoras en Swing (0 pérdidas, 4 ganancias), el cálculo de Profit Factor $\frac{\$14.418,74}{0}$ produce una indeterminación matemática ($+\infty$). El motor sustituyó el valor por `99.00` de forma artificial como cota superior para evitar un error de división por cero.
- **Dictamen:** Dicho valor **no representa rentabilidad comprobada ni robustez estadística real**.

---

## 5. Dictamen y Plan de Corrección para Fase B y C

1. **Liberación de Reservas en Orquestador:** Corregir en `orchestrator.py` la llamada obligatoria a `risk_engine.release_reservation(res_id)` en cada salida de posición para permitir que el backtest procese todas las señales reales y no solo la primera.
2. **Transición a Datos Reales Verificables:** Para Fase B, utilizar datos de precios históricos de mercado reales descargados mediante la API oficial de Moomoo OpenD y/o Yahoo Finance diario/horario verificado para contrastar el comportamiento contra el baseline.
3. **Variantes Controladas (Fase C):** Probar las variantes paramétricas autorizadas sin desarmar la gestión de riesgos ni los ratios 2:1.
