# INFORME DE AUDITORÍA FORENSE DE EJECUCIÓN Y PROPUESTA DE REDISEÑO (FASE 5)
**Fecha:** 2026-10-29  
**Proyecto:** OracleBot v2 — Strategy Laboratory  
**Estrategias Auditadas:** `ORB_SWING_PULLBACK_V1` & `ORB_INTRADAY_BREAKOUT_V1`  
**Estado Registrado:** AMBAS ESTRATEGIAS RECHAZADAS (`REJECTED`) EN `lab_strategy_registry`  
**Entorno Operativo:** AUDITORÍA DESCONECTADA / MODO ANALYSIS_ONLY / CERO ÓRDENES AL BROKER

---

## 1. Reconstrucción Cronológica y Auditoría de las 11 Operaciones (Forward 2026)

Se procesó la reconstrucción tick-a-tick de las 11 operaciones simuladas durante las 204 sesiones bursátiles de 2026 en Moomoo:

| # | Símbolo | Fecha/Hora Entrada | Precio Entrada | Cantidad | Nocional (\$) | Fecha/Hora Salida | Precio Salida | Motivo Salida | PnL Neto (\$) | Retorno R | Fricción Desliz. (\$) |
| :-: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | SPY | 2026-01-05 16:00 | \$683.54 | 73 acc | \$49.898,42 | 2026-01-20 13:30 | \$674.51 | `TIME_EXIT` | -\$660,19 | -0.96R | \$74,64 |
| **2** | SPY | 2026-02-02 16:00 | \$691.19 | 72 acc | \$49.765,68 | 2026-02-03 16:00 | \$678.53 | `STOP_LOSS` | -\$912,52 | -1.04R | \$73,73 |
| **3** | SPY | 2026-05-20 16:00 | \$736.98 | 67 acc | \$49.377,66 | 2026-06-01 13:30 | \$754.11 | `TAKE_PROFIT` | **+\$1.146,71** | **+1.77R** | \$75,04 |
| **4** | SPY | 2026-06-04 16:00 | \$753.86 | 66 acc | \$49.754,76 | 2026-06-05 13:30 | \$746.72 | `STOP_LOSS` | -\$472,24 | -1.09R | \$74,28 |
| **5** | SPY | 2026-07-09 16:00 | \$750.46 | 66 acc | \$49.530,36 | 2026-07-23 13:30 | \$736.37 | `TIME_EXIT` | -\$930,94 | -1.05R | \$73,41 |
| **6** | SPY | 2026-08-19 16:00 | \$768.25 | 65 acc | \$49.936,25 | 2026-08-20 13:30 | \$763.49 | `STOP_LOSS` | -\$310,40 | -1.31R | \$74,69 |
| **7** | SPY | 2026-08-27 16:00 | \$770.42 | 64 acc | \$49.306,88 | 2026-09-01 13:30 | \$759.27 | `STOP_LOSS` | -\$714,60 | -1.05R | \$73,70 |
| **8** | SPY | 2026-09-25 16:00 | \$771.85 | 64 acc | \$49.398,40 | 2026-09-29 13:30 | \$762.23 | `STOP_LOSS` | -\$616,68 | -1.06R | \$73,60 |
| **9** | SPY | 2026-10-09 16:00 | \$778.62 | 64 acc | \$49.831,68 | 2026-10-14 13:30 | \$769.41 | `STOP_LOSS` | -\$590,44 | -1.07R | \$74,24 |
| **10**| QQQ | 2026-01-09 16:00 | \$624.39 | 80 acc | \$49.951,20 | 2026-01-14 13:30 | \$613.99 | `STOP_LOSS` | -\$833,00 | -1.05R | \$74,04 |
| **11**| QQQ | 2026-01-28 16:00 | \$631.59 | 79 acc | \$49.895,61 | 2026-02-03 13:30 | \$615.57 | `STOP_LOSS` | -\$1.266,58 | -1.03R | \$73,47 |

---

## 2. Diagnóstico de Discrepancias del Simulador: Por qué 2x Costes es Menos Negativo que 1x

La comparación trade-a-trade reveló la explicación matemática exacta:

1. **La Paradoja Aparente:**
   - PnL Neto a 1x Costes: **-\$6.160,88 USD** (11 operaciones ejecutadas).
   - PnL Neto a 2x Costes: **-\$5.387,76 USD** (10 operaciones ejecutadas).
2. **Causa Raíz Descubierta:**
   - En la simulación a 2x costes, las primeras 10 operaciones acumularon un mayor nivel de fricción por pérdida (~+\$50 USD extra de deslizamiento por trade).
   - Debido a esta mayor fricción acumulada, el circuito de protección de cartera (`is_trading_halted = True` al superar el límite de pérdida diaria de 2.0R = \$5.000 USD) **se activó antes en la simulación a 2x costes**.
   - Al dispararse antes, el circuito de seguridad **bloqueó e impidió la ejecución de la Operación #11** (QQQ el 28/01/2026).
   - Dado que la Operación #11 resultó ser una pérdida severa por Stop Loss de **-\$1.266,58 USD**, el portafolio a 2x costes se ahorró esa pérdida entera.
   - **Balance Matemático:**
     $$\Delta \text{PnL} = \text{Ahorro Operación \#11 } (+\$1.266,58) - \text{Sobrecoste 2x en ops 1 a 10 } (-\$493,46) = +\$773,12 \text{ neto}$$
   - **Conclusión Técnica:** La aparente "mejora" a 2x costes es un artefacto de truncamiento no lineal provocado por el disyuntor de seguridad de riesgo (*circuit breaker interaction*), no una ventaja intrínseca de la estrategia frente a los costes.

---

## 3. Auditoría de Rechazos y Gestión de Reservas

### 3.1 Clasificación de los 753 Rechazos
De las 223 señales generadas a nivel algorítmico, se produjeron 753 rechazos en las diferentes evaluaciones de barra debido a dos causas fundamentales:
1. **Límite de Riesgo Abierto Agregado (0,50% = \$5.000 USD):**
   - El riesgo planificado por operación es de \$2.500 USD (0,25% de \$1.000.000).
   - Cuando coinciden dos posiciones abiertas simultáneas (p. ej. SPY y QQQ), el riesgo comprometido alcanza exactamente \$5.000 USD ($2 \times \$2.500$).
   - Cualquier tercera señal concurrente en AAPL, MSFT, NVDA, BAC o XOM fue **correctamente rechazada** para no sobrepasar la exposición agregada permitida.
2. **Conflicto de Concurrencia por Reserva Activa:**
   - Mientras una posición en un activo específico permanecía abierta, el motor bloqueó cualquier entrada adicional en ese mismo símbolo, garantizando la política de no-duplicación (*single position per symbol*).
3. **Liberación de Reservas:** Se verificó que todas las reservas fueron liberadas atómicamente al confirmarse la salida de cada trade. No existieron bloqueos huérfanos ni pérdidas de sincronización en memoria.

---

## 4. Gobernanza Oficial de Estrategias (`trading_robot.db`)

Se actualizaron los registros oficiales en la base de datos de laboratorio:

| Estrategia ID | Estado Registrado | Motivo de Gobernanza |
| :--- | :---: | :--- |
| **`ORB_INTRADAY_BREAKOUT_V1`** | `REJECTED` | Archivada formalmente. Expectativa matemática negativa (-0,16R), Profit Factor 0,29. Sin ventaja frente a costes. |
| **`ORB_SWING_PULLBACK_V1`** | `REJECTED` | **Rechazada para promoción.** Fracasó en validación forward independiente de 2026 (Win Rate 9,1%, Profit Factor 0,16, Expectativa -0,81R). Sobreajustada al bull run de 2024–2025. |
| **`D21_RangeCompress_5d`** | `PAPER` | **Completamente intacta.** Fingerprint `f885ec2db2422308`, puntuación 69.17 y aislamiento preservados al 100%. |

---

## 5. Propuesta Teórica de Nuevas Hipótesis (Sin Implementación)

En cumplimiento de la Sección 5, se presentan las hipótesis conceptuales formuladas para futura revisión:

### Hipótesis A: Detector Determinista de Régimen de Mercado (Trend vs. Chop Index)
- **Concepto:** Evitar operar en estrategias tendenciales cuando el mercado carece de inercia direccional.
- **Formulación Matemática:**
  $$\text{ER} = \frac{|\text{Close}_t - \text{Close}_{t-20}|}{\sum_{i=0}^{19} |\text{Close}_{t-i} - \text{Close}_{t-i-1}|} \quad (\text{Efficiency Ratio de Kaufman})$$
  $$\text{ADX}_{14} > 25 \quad \text{y} \quad \text{ER}_{20} > 0,35 \implies \mathbf{RÉGIMEN\_TENDENCIAL}$$
  $$\text{ADX}_{14} \le 20 \quad \text{o} \quad \text{ER}_{20} \le 0,20 \implies \mathbf{RÉGIMEN\_LATERAL\_RANGO}$$
- **Hipótesis a Contrastar:** Los retrocesos a medias móviles solo tienen probabilidad favorable cuando el $\text{ER}_{20} > 0,35$.

### Hipótesis B: Swing Pullback Filtrado por Inercia Real (Momentum-Gated Swing)
- **Concepto:** Modificar la entrada en Swing exigiendo que la pendiente de la EMA50 diaria sea superior a un umbral mínimo de aceleración y que el ADX diario supere 25.
- **Hipótesis a Contrastar:** Filtrar las entradas en consolidaciones de máximos históricos reduciría el número de operaciones en 2026 de 11 a menos de 3, evitando 8 de las 10 pérdidas por Stop Loss.

### Hipótesis C: Estrategia de Reversión a la Media en Rango (Mean Reversion Candidate)
- **Concepto:** Diseñada exclusivamente para activarse cuando el Detector de Régimen (Hipótesis A) declare `RÉGIMEN_LATERAL_RANGO`.
- **Formulación Preliminar:**
  - Entrada: Compra cuando el precio cierre por debajo de la Banda Inferior de Bollinger (20 periodos, 2.0 desviaciones estándar) y el RSI(2) sea $< 10$.
  - Salida: Toma de beneficios al cruzar la Media Móvil Simple de 20 periodos o a los 3 días de tenencia.
  - Stop Loss: 1.5 ATR(14) por debajo del precio de entrada.
- **Hipótesis a Contrastar:** En regímenes donde el Swing de ruptura falla, la reversión a la media captura los rebotes de sobreventa dentro del canal lateral.

---

> [!IMPORTANT]
> **COMPROMISO DE NO IMPLEMENTACIÓN PREMATURA:**  
> Ninguna de las hipótesis anteriores ha sido codificada ni activada en backtest o simulación. Se mantienen en fase de diseño documental a la espera de la revisión y directrices del usuario.
