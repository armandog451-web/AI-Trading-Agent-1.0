# INFORME DE EXPERIMENTOS CONTROLADOS Y VALIDACIÓN EMPÍRICA (FASE DUAL-2)
**Fecha:** 2026-10-29  
**Proyecto:** OracleBot v2 — Dual Strategy Research  
**Estrategias:** `ORB_INTRADAY_BREAKOUT_V1` & `ORB_SWING_PULLBACK_V1`  
**Datos Utilizados:** Datos históricos reales de Moomoo OpenD (Ajuste QFQ, 1D, 4H, 1H, 15M)  
**Entorno Operativo:** RESEARCH / SHADOW (Modo de ejecución: ANALYSIS_ONLY, 0 órdenes reales)

---

## 1. Auditoría de Cobertura y Calidad de Datos

### 1.1 Descarga Directa desde Moomoo OpenD
Se integraron y almacenaron en caché datos históricos reales descargados de Moomoo OpenD (`127.0.0.1:11111`) para 15 acciones líderes del mercado estadounidense:
- **Universo Central (5 activos):** `US.SPY`, `US.QQQ`, `US.AAPL`, `US.MSFT`, `US.NVDA`
- **Universo Ampliado (10 activos adicionales):** `US.AMZN`, `US.GOOGL`, `US.META`, `US.TSLA`, `US.JPM`, `US.BAC`, `US.XOM`, `US.UNH`, `US.AMD`, `US.COST`
- **Profundidad descargada por activo:**
  - **1D (Diario):** 956 barras reales (enero 2023 – octubre 2026).
  - **4H (K_240M):** 1.000 barras reales (enero 2024 – enero 2026).
  - **1H (K_60M):** 1.000 barras reales (enero 2025 – julio 2025).
  - **15M (K_15M):** 3.000 barras reales paginadas (enero 2026 – junio 2026).
- **Ajuste de Precios:** Forward-adjusted (`ft.AuType.QFQ`) para preservar continuidad matemática frente a splits y dividendos.

---

## 2. Reparación del Motor de Riesgo (Bug de Reserva Activa)

- **Causa del bloqueo:** En la versión anterior de `orchestrator.py`, la reserva atómica `RiskReservation` creada al entrar a una posición nunca era liberada (`release_reservation`) al salir de la misma. Como consecuencia, tras el primer trade, cada activo quedaba congelado de por vida.
- **Corrección verificada:** Se incorporó la liberación atómica en `simulate_exit` tanto para Intradía como para Swing. El sistema ahora permite la secuencia continua y sin restricciones de todas las oportunidades detectadas.

---

## 3. Resultados de los Experimentos Controlados

Se estructuró la evaluación con partición temporal causal estricta:
- **Train (60%):** Optimización y verificación in-sample.
- **Validation (20%):** Selección de hiperparámetros.
- **Test (20% - Out-of-Sample):** Prueba ciega fuera de muestra bajo estrés de costes (1x, 2x y 3x fricción: comisión \$0.005/acción + 5 a 15 bps de deslizamiento).

### 3.1 Estrategia A: `ORB_INTRADAY_BREAKOUT_V1`

| Variante | Universo | Parámetros Clave | Total Ops | Train (Ops / WR / PF) | Test OOS (1x PnL) | Test OOS (2x PnL) | Test OOS (3x PnL) | Max DD |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | 5 activos | RVOL 1.50, Cuerpo 50% | 58 | 32 / 34,4% / 0,69 | -\$2.665,61 | -\$3.111,58 | -\$3.560,31 | 0,59% |
| **Var 1** | 5 activos | RVOL 1.25, Cuerpo 50% | 81 | 40 / 32,5% / 0,60 | -\$2.508,63 | -\$3.460,39 | -\$4.413,62 | 0,74% |
| **Var 2** | 5 activos | RVOL 1.50, Cuerpo 40% | 58 | 32 / 34,4% / 0,69 | -\$2.665,61 | -\$3.111,58 | -\$3.560,31 | 0,58% |
| **Var 3** | 15 activos | RVOL 1.50, Cuerpo 50% | 95 | 52 / 44,2% / 1,19 | -\$3.677,49 | -\$4.529,36 | -\$5.383,11 | 0,45% |
| **Var 4** | 15 activos | RVOL 1.25, Cuerpo 40% | **137** | 73 / 35,6% / 0,70 | -\$3.324,15 | -\$4.879,91 | -\$6.439,63 | 0,77% |

#### Hallazgos Intradía:
1. **Ausencia de Ventaja Estadística Neta:** En todas las variantes (tanto en el baseline como en el universo ampliado), el rendimiento fuera de muestra (**Test OOS**) genera pérdidas consistentes (-\$2.508 a -\$3.677 en 1x costes).
2. **Impacto de la Fricción:** Al duplicar (2x) o triplicar (3x) los costes por spread y deslizamiento, las pérdidas aumentan linealmente (hasta -\$6.439).
3. **Efecto de Relajar Filtros:** Reducir el RVOL de 1,50 a 1,25 incrementa el volumen de operaciones (de 58 a 81 en 5 activos, y a 137 en 15 activos), pero **reduce el Win Rate (de 34,4% a 32,5%) y acelera las pérdidas netas**.

---

### 3.2 Estrategia B: `ORB_SWING_PULLBACK_V1`

| Variante | Universo | Parámetros Clave | Total Ops | Train (Ops / WR / PF) | Val PnL | Test OOS (1x PnL) | Test OOS (2x PnL) | Test OOS (3x PnL) | Max DD |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline** | 5 activos | Lookback 5 barras | 88 | 57 / 43,9% / 1,02 | +\$16.796,61 | -\$416,20 | -\$1.257,31 | -\$2.107,86 | 0,81% |
| **Var 1** | 5 activos | Lookback 8 barras | 86 | 53 / 47,2% / 1,13 | +\$18.816,17 | +\$1.492,24 | +\$670,62 | -\$161,33 | 0,72% |
| **Var 2** | 15 activos | Lookback 5 barras | **242** | 162 / 43,8% / 1,04 | +\$32.084,89 | -\$4.855,83 | -\$6.724,29 | -\$8.577,96 | 1,67% |
| **Var 3** | 15 activos | Lookback 8 barras | **227** | 148 / 42,6% / 0,91 | +\$38.700,49 | +\$1.494,57 | -\$353,31 | -\$2.178,11 | 2,39% |

#### Hallazgos Swing:
1. **Sensibilidad al Régimen y Fricción:** El rendimiento in-sample y de validación fue positivo durante periodos de expansión sostenida (Validation generó entre \$16k y \$38k). Sin embargo, el periodo fuera de muestra (**Test OOS**) exhibió alta vulnerabilidad:
   - En Baseline y Var 2, Test OOS es deficitario (-\$4.855 a -\$8.577).
   - En Var 1 y Var 3 (ventana de retroceso de 8 barras), Test OOS es positivo a 1x (\$1.492 a \$1.494), pero **colapsa a negativo bajo costes 2x y 3x** (-\$161 a -\$2.178).
2. **Volumen Muestral:** El universo ampliado de 15 activos superó ampliamente el umbral exigido de evidencia ($\ge 100$ operaciones totales y $\ge 30$ fuera de muestra: **242 operaciones totales y 38 operaciones OOS**).

---

## 4. Verificación de Seguridad y No-Regresión (Fase E)

- **Ejecución de Pruebas Unitarias:** **255 de 255 pruebas superadas (100%)** en `ai_trading_agent/tests/`. Cero fallos, cero regresiones.
- **Integridad de D21:** Se auditó [`trading_robot.db`](file:///c:/Users/edsel/OneDrive/Documents/PROJET%202/trading_robot.db). La estrategia `D21_RangeCompress_5d` conserva su fingerprint `f885ec2db2422308`, puntuación 69.17 y estado `PAPER` inalterados.
- **Aislamiento de US.SPY:** Las 382 acciones en la cuenta paper de Moomoo permanecen intactas, sin órdenes de cierre ni interferencias.
- **Cero Órdenes al Broker:** Ambas estrategias operan estrictamente en modo simulación/sombra. No se emitió ninguna orden a Moomoo OpenD.

---

## 5. Recomendación Argumentada

| Estrategia | Veredicto Técnico | Dictamen y Argumentación Cuantitativa |
| :--- | :---: | :--- |
| **`ORB_INTRADAY_BREAKOUT_V1`** | **DESCARTAR / REDISEÑAR DESDE CERO** | **Sin ventaja estadística.** Incluso con datos reales y universo ampliado (137 operaciones), la estrategia muestra una expectativa matemática negativa (-0.08R a -0.11R) y pérdidas sistemáticas fuera de muestra. Relajar filtros de volumen o geometría sólo incrementa la tasa de pérdida. No es apta para paper conectado ni producción. |
| **`ORB_SWING_PULLBACK_V1`** | **MANTENER EN RESEARCH / REFINAR** | **Ventaja condicional frágil.** Cumple con la masa crítica muestral (242 operaciones totales, 38 OOS), y muestra rentabilidad sólida en tendencias claras. No obstante, no soporta costes a 2x/3x ni cambios de régimen de volatilidad. Se recomienda mantenerla estrictamente en `RESEARCH` e investigar un filtro macro de régimen antes de cualquier consideración de paper conectado. |
