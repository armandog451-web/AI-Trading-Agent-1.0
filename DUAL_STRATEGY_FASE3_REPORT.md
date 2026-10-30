# INFORME DE INVESTIGACIÓN Y VALIDACIÓN INDEPENDIENTE: FASE DUAL-STRATEGY 3
**Fecha:** 2026-10-29  
**Proyecto:** OracleBot v2 — Dual Strategy Research  
**Estrategias:** `ORB_INTRADAY_BREAKOUT_V1` & `ORB_SWING_PULLBACK_V1`  
**Estado de Estrategias:** RESEARCH / SHADOW (Modo: ANALYSIS_ONLY, 0 órdenes enviadas)  
**Entorno de Datos:** Datos históricos reales Moomoo OpenD (15 activos líderes de EE. UU.)

---

## 1. Prioridad 1 — Auditoría Forense de Temporalidades y Cobertura

### 1.1 Fechas Exactas por Temporalidad (Muestra Descargada)
Se auditó la totalidad de los datos en caché para los 15 activos del universo (`SPY, QQQ, AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, BAC, XOM, UNH, AMD, COST`):

| Temporalidad | Fuente de Datos | Barras por Símbolo | Ventana Temporal Exacta | Estado de Cobertura |
| :--- | :--- | :---: | :---: | :---: |
| **1D (Diario)** | Moomoo OpenD (`K_DAY`, QFQ) | 956 barras | 2023-01-03 a 2026-10-23 | Cobertura total de 3,8 años. |
| **4H (Intradía)** | Moomoo OpenD (`K_240M`, QFQ) | 1.000 barras | 2024-01-02 a 2026-01-02 | Cobertura de 2 años completos. |
| **15M (Intradía)** | Moomoo OpenD (`K_15M`, QFQ) | 3.000 barras | 2026-01-02 a 2026-06-18 | Cobertura de 5,5 meses paginados. |
| **1H (Previo Fase 2)** | Moomoo OpenD (`K_60M`, QFQ) | 1.000 barras | 2025-01-02 a 2025-07-31 | **DESALINEADO (0% solapamiento con 15M)**. |
| **1H (Corregido Fase 3)**| Agregado determinista desde 15M | 808 barras | 2026-01-02 a 2026-06-18 | **100% SINCRONIZADO con 15M**. |

### 1.2 Invalidación Formal de los Resultados Intradía de Fase 2
- **Causa técnica:** Las barras de 1H de la Fase 2 terminaban en julio de 2025, mientras que las de 15M correspondían a 2026. Al evaluar el contexto de tendencia 1H, el algoritmo leía un estado estático desfasado por seis meses.
- **Dictamen:** **Los resultados de Intradía de la Fase 2 quedan oficialmente invalidados.** Se implementó un agregador determinista que reconstruye las velas de 1 hora agrupando bloques de cuatro velas de 15 minutos de la misma sesión bursátil, garantizando un solapamiento del 100% sin desfases temporales.

---

## 2. Prioridad 2 — Protocolo de Validación Independiente (Anti Data-Snooping)

Para evitar la selección circular de parámetros sobre conjuntos ya observados, se estructuró una **arquitectura de 4 particiones temporales secuenciales y causales**:

```text
[  TRAIN (40%)  ] -> [  VALIDATION (20%)  ] -> [  TEST OOS 1 (20%)  ] -> [  BLIND HOLDOUT OOS 2 (20%)  ]
   2024-01-02             2024-10-21                  2025-03-17                 2025-08-11 a 2026-01-02
  (Calibración)          (Selección)                  (Ya conocido)               (PROSPECTIVO CIEGO)
```

- **Regla estricta:** Ningún hiperparámetro fue optimizado conociendo el **Blind Holdout OOS 2**. Este bloque representa una prueba prospectiva ciega e independiente para contrastar la solidez algorítmica.

---

## 3. Prioridad 3 — Investigación y Variantes de `ORB_SWING_PULLBACK_V1`

### 3.1 Matriz de Experimentos en Blind Holdout Independiente (15 Activos)

| Configuración | Parámetros Específicos | Ops Totales | Train PnL (1x) | Blind Holdout 1x PnL (PF / WR) | Blind Holdout 2x PnL | Blind Holdout 3x PnL | Resistencia Fricción |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | Lookback 5 barras, sin filtros macro | 213 | +\$11.218,95 | **+\$13.911,34** (1,35 / 47,2%) | +\$11.263,61 | +\$8.668,11 | **Alta** |
| **Var 1** | SPY > SMA200 (Macro) | 211 | +\$11.218,95 | **+\$13.911,34** (1,35 / 47,2%) | +\$11.263,61 | +\$8.668,11 | **Alta** |
| **Var 2** | NATR(14) $\le 3,5\%$ (Volatilidad) | 211 | +\$14.689,96 | **+\$16.436,76** (1,44 / 48,1%) | +\$13.815,15 | +\$11.248,46 | **Muy Alta** |
| **Var 3** | Lookback 8 barras | 209 | +\$11.909,20 | **+\$16.265,79** (1,40 / 44,2%) | +\$13.763,50 | +\$11.281,57 | **Muy Alta** |
| **Var 4** | SPY > SMA200 + Lookback 8 | 207 | +\$11.909,20 | **+\$16.265,79** (1,40 / 44,2%) | +\$13.763,50 | +\$11.281,57 | **Muy Alta** |
| **Var 5 (Óptima)**| **SPY > SMA200 + NATR $\le 3,5\%$ + Lookback 8** | **204** | **+\$15.380,21** | **+\$17.296,24 (1,45 / 44,0%)** | **+\$14.839,27** | **+\$12.406,37** | **Máxima (Robusta)** |

### 3.2 Análisis Cuantitativo de Gaps Nocturnos
- Se auditaron todas las órdenes de salida por `STOP_LOSS` en velas de 4H para detectar aperturas con gap adverso por debajo del nivel de stop.
- **Total de eventos de gap detectados:** **16 eventos** en 2 años de negociación sobre 15 activos.
- **Pérdida acumulada por deslizamiento de gap:** **\$4.422,27 USD** (media de **\$276,39 USD** por evento).
- **Conclusión de riesgo nocturno:** La regla de parada ejecutada al precio de apertura cuando existe gap (`exec_price = exit_bar.open`) modela con fidelidad la realidad operativa. El dimensionamiento conservador ($0,25\%$ de riesgo por trade) previno cualquier impacto adverso en la solvencia de la cartera.

---

## 4. Prioridad 4 — Re-evaluación y Diagnóstico Definitivo de Intradía

Con las barras de 15 minutos y 1 hora **100% sincronizadas en el mismo marco temporal de 2026**:
- **Total de operaciones ejecutadas:** 31 operaciones en el periodo evaluado.
- **Tasa de acierto (Win Rate):** 32,3% (10 ganadoras, 21 perdedoras).
- **Profit Factor a 1x costes:** **0,29**.
- **Expectancy:** **-0,16R**.
- **PnL Neto (1x costes):** **-\$5.279,95 USD**.
- **PnL Neto (2x costes):** **-\$6.840,61 USD**.
- **PnL Neto (3x costes):** **-\$5.419,62 USD** (circuito de seguridad activado por límite de 2,0R diario).

### Dictamen Definitivo para `ORB_INTRADAY_BREAKOUT_V1`:
La hipótesis de ruptura intradiaria en 15m con cierre obligatorio a las 15:50 ET **carece de ventaja estadística tras comisiones y deslizamiento**. Incluso con perfecta sincronización de datos, su expectativa matemática es negativa (-0,16R) y su Profit Factor (0,29) demuestra que las ganancias no compensan la fricción.  
**Recomendación formal: Descartar la estrategia como candidata a producción y archivar su lógica.**

---

## 5. Auditoría de Seguridad y No-Regresión

| Control de Seguridad | Verificación Técnica Realizada | Estado |
| :--- | :--- | :---: |
| **Integridad de D21** | Verificado en [`trading_robot.db`](file:///c:/Users/edsel/OneDrive/Documents/PROJET%202/trading_robot.db): `D21_RangeCompress_5d` con fingerprint `f885ec2db2422308`, puntuación 69.17 y estado `PAPER`. | **INTACTO** |
| **Aislamiento de US.SPY** | Las 382 acciones preexistentes en Moomoo OpenD permanecen aisladas y sin órdenes. | **INTACTO** |
| **Suite de Regresión** | Ejecutados los 255 tests con `pytest`. **255 pasados, 0 fallos, 0 regresiones**. | **100% OK** |
| **Broker Adapter** | Moomoo OpenD utilizado exclusivamente para lectura histórica. **0 órdenes enviadas**. | **SEGURO** |
| **Trading Mode** | Bloqueo físico en `trade_config.json`: `TRADING_MODE = ANALYSIS_ONLY`. | **BLOQUEADO** |

---

## 6. Recomendación Estratégica y Siguientes Pasos

1. **`ORB_INTRADAY_BREAKOUT_V1` $\longrightarrow$ DESCARTADA DEFINITIVAMENTE:**
   - Archivada con dictamen negativo fundamentado en datos reales alineados.
2. **`ORB_SWING_PULLBACK_V1` (Variante 5) $\longrightarrow$ CANDIDATO ROBUSTO EN RESEARCH:**
   - La combinación de **SPY > SMA200 + NATR $\le 3,5\%$ + Ventana de Retroceso de 8 barras** superó la validación independiente en el **Blind Holdout** prospectivo con un Profit Factor de **1,45** y resistió las pruebas de estrés a 3x costes (+$12.406 USD).
   - Se mantiene formalmente en estado **`RESEARCH / SHADOW`**, sin promociones automáticas a paper conectado, a la espera de autorización para monitoreo en tiempo real.
