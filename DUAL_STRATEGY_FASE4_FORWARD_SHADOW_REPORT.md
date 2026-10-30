# INFORME DE VALIDACIÓN FORWARD SHADOW (FASE DUAL-4)
**Fecha:** 2026-10-29  
**Proyecto:** OracleBot v2 — Dual Strategy Research  
**Estrategia Evaluada:** `ORB_SWING_PULLBACK_V1` (Variante 5 Congelada)  
**Versión:** `1.5.0-SHADOW`  
**Fingerprint Inmutable:** `b0e2f3a85d1b8eec`  
**Período de Observación Forward:** 2026-01-02 a 2026-10-23 (204 sesiones bursátiles reales / 408 barras de 4H)  
**Modo Operativo:** SHADOW (ANALYSIS_ONLY, Cero órdenes al broker, ejecución desconectada)

---

## 1. Auditoría de Reproducibilidad y Sincronización con GitHub

Se auditaron los archivos, estados y hashes criptográficos correspondientes al commit base de Fase 3:
- **Commit Base:** [`a50b847`](https://github.com/armandog451-web/AI-Trading-Agent-1.0/commit/a50b847)
- **Hashes SHA-256 de Archivos Clave:**
  - `orchestrator.py`: `9aceafb4fc44f4a3e7076936cb1fb742a7eb71a34bb0a370c43a84a5851b93d1`
  - `models.py`: `f6063f5907b77334aaadf4bc677bece8f2462399d687b53dca5c0a43e4debd6e`
  - `swing_pullback.py`: `e31bcdf9b4266c87a965eb50af659ec2badce100b411450841ef681861bc5e18`
  - `risk.py`: `bdfbb7ae7f711f1143bb9257989b0975b7533b86c0c3b7343628c6fe7c7b62c2`
  - `simulation.py`: `3b08ebc4d1ab5a0cb6b680f8794b86ac59ab58c9841bd114bb56f7c6bc4bb2c8`
  - `test_oraclebot_v2_dual_strategy.py`: `3e784aca38f1d33b572594a8cfca780d7209cef366080b210a3733feb9744b8c`
- **Declaración Metodológica Honesta:** Se reconoce formalmente que la Variante 5 fue seleccionada tras observar los datos del *Blind Holdout* (2025). En consecuencia, dicho conjunto fue reclasificado como **exploratorio/calibración**, exigiendo una validación prospectiva verdaderamente independiente.

---

## 2. Configuración y Congelación de la Variante 5

La configuración algorítmica fue congelada estrictamente sin optimizaciones durante la campaña forward:

```json
{
  "strategy_id": "ORB_SWING_PULLBACK_V1",
  "version": "1.5.0-SHADOW",
  "daily_fast_ema": 50,
  "daily_slow_ema": 200,
  "daily_slope_bars": 10,
  "four_h_pullback_ema": 20,
  "four_h_support_ema": 50,
  "pullback_window_bars": 8,
  "atr_stop_buffer_mult": 0.10,
  "target_rr_ratio": 2.0,
  "max_holding_sessions": 10,
  "use_spy_macro_filter": true,
  "max_natr_threshold": 3.5,
  "operational_mode": "SHADOW_PAPER_UNCONNECTED",
  "fingerprint": "b0e2f3a85d1b8eec"
}
```

---

## 3. Resultados de la Validación Forward Shadow (2026: 204 Sesiones)

Se procesaron 408 barras reales de 4H para 15 activos estadounidenses líderes (`SPY, QQQ, AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA, JPM, BAC, XOM, UNH, AMD, COST`) en el periodo comprendido entre el **02/01/2026 y el 23/10/2026** (más de 3,4 veces el mínimo requerido de 60 sesiones).

### 3.1 Métricas de Rendimiento en SHADOW

| Métrica Cuantitativa | Resultado Forward (2026) | Backtest Histórico (2024-2025) | Divergencia / Diagnóstico |
| :--- | :---: | :---: | :--- |
| **Sesiones Observadas** | **204 sesiones** | ~500 sesiones | Amplitud muestral suficiente. |
| **Señales Generadas** | 223 señales | ~600 señales | Frecuencia de disparo consistente. |
| **Rechazos por Riesgo / Macro**| 753 rechazos | N/A | Filtrado activo del motor de riesgo. |
| **Operaciones Ejecutadas** | **11 operaciones** | 204 operaciones | Alta selectividad por límites de concurrencia y corte 2R. |
| **Tasa de Acierto (Win Rate)** | **9,1% (1W / 10L)** | **44,0% (90W / 114L)** | **Colapso severo (-34,9 puntos porcentuales)**. |
| **Profit Factor (1x costes)** | **0,16** | **1,45** | **Deterioro crítico; expectativa matemática destruida**. |
| **Profit Factor (2x costes)** | 0,17 | 1,28 | Sin resistencia a fricción. |
| **Profit Factor (3x costes)** | 0,15 | 1,25 | Pérdidas crecientes. |
| **Expectancy en R** | **-0,81R** | **+0,14R** | Pérdida media casi equivalente a 1R completo por trade. |
| **Expectancy en USD** | -\$560,08 | +\$345,92 | Deriva monetaria negativa. |
| **PnL Neto (1x costes)** | **-\$6.160,88 USD** | +\$17.296,24 USD | Pérdida de capital en forward. |
| **Max Drawdown** | **0,62% (\$6.160,88)** | 1,45% (\$14.500) | Contenido por el circuito de corte 2.0R. |
| **Comisiones Totales** | \$22,00 USD | \$1.020,00 USD | Comisiones institucionales normales (\$0.005/acc). |
| **Deslizamiento Modelado** | \$814,84 USD | \$4.120,00 USD | 5 bps de slippage base por orden. |

---

## 4. Análisis de Divergencias entre Backtest y Forward

1. **Cambio Estructural de Régimen Bursátil:**
   - **En el Backtest (2024–2025):** El mercado se encontró en una tendencia alcista secular potente y sostenida (bull run tecnológico). En ese entorno, cualquier retroceso hacia la EMA20 de 4H era absorbido rápidamente por compradores institucionales, generando continuación alcista hacia el target de 2:1.
   - **En el Forward Shadow (2026):** El mercado entró en una fase de consolidación lateral de rango amplio y alta volatilidad en máximos históricos (\$730 a \$770 en SPY). Los retrocesos a la EMA20 de 4H sufrieron falsas rupturas alcistas y giros bruscos a la baja, ejecutando los stops de pérdida de forma reiterada.
2. **Deficiencia del Filtro de Tendencia:**
   - La condición de tendencia diaria `EMA50 > EMA200` y `SPY > SMA200` se mantuvo en estado alcista durante casi todo 2026, a pesar de que el mercado se encontraba lateralizando. La estrategia no poseía un filtro de **fuerza de tendencia (ADX) o dispersión de rango** que detectara la pérdida de momento.

---

## 5. Informe de Gaps Nocturnos y Riesgo Realizado vs. Planificado

- **Eventos de Gap Adverso en Salidas:** Se registraron **8 aperturas con gap a la baja** por debajo del stop loss planeado en 2026.
- **Pérdida Adicional por Deslizamiento de Gap:** **\$1.105,15 USD** acumulados (media de **\$138,14 USD** por evento).
- **Riesgo Planificado vs. Realizado:**
  - Riesgo planificado por operación: 0,25% (\$2.500 USD).
  - Máxima pérdida individual observada en un trade (incluyendo gap adverso): **\$763,28 USD** (en SPY el 2026-06-05).
  - **Eficacia del Motor de Riesgo:** El dimensionamiento mediante `math.floor` y el circuito de corte diario (2.0R) limitaron el Drawdown total a un modesto **0,62% (\$6.160,88 USD)**, protegiendo eficazmente el capital de la cuenta paper frente al fallo del modelo de entrada.

---

## 6. Estado Oficial en el Registro de Estrategias (`trading_robot.db`)

Se actualizó la tabla [`lab_strategy_registry`](file:///c:/Users/edsel/OneDrive/Documents/PROJET%202/trading_robot.db):

1. **`ORB_INTRADAY_BREAKOUT_V1` $\longrightarrow$ `REJECTED`:**
   - Archivada formalmente. Código, evidencias históricas y documentación preservados intactos. Rechazada para cualquier promoción.
2. **`ORB_SWING_PULLBACK_V1` $\longrightarrow$ `SHADOW` / `CANDIDATE`:**
   - Parámetros y fingerprint `b0e2f3a85d1b8eec` registrados con los resultados forward de 2026.
3. **`D21_RangeCompress_5d` $\longrightarrow$ `PAPER`:**
   - **Completamente intacta**, fingerprint `f885ec2db2422308`, puntuación 69.17 inalterada.

---

## 7. Dictamen Final y Recomendación Fundamentada

| Estrategia | Veredicto Final | Argumentación Cuantitativa y Acción Inmediata |
| :--- | :---: | :--- |
| **`ORB_INTRADAY_BREAKOUT_V1`** | **DESCARTADA DEFINITIVAMENTE (ARCHIVADA)** | Expectativa matemática negativa (-0,16R), Profit Factor deficiente (0,29) e incapacidad de absorber comisiones y spread en datos alineados. Conservada únicamente como evidencia histórica en el registro. |
| **`ORB_SWING_PULLBACK_V1`** | **NO APTA PARA PROMOCIÓN $\longrightarrow$ RETENER EN RESEARCH / REDISEÑAR** | A pesar de su excelente rendimiento en tendencias del pasado (2024-2025), la estrategia **fracasó rotundamente en la validación forward independiente de 2026** (Win Rate del 9,1%, Profit Factor de 0,16 y expectativa de -0,81R). Demostró sobreajuste al régimen tendencial y extrema fragilidad ante mercados laterales. **Prohibido promocionar a paper conectado ni dinero real.** Debe permanecer congelada en `RESEARCH` o rediseñarse desde cero con un detector explícito de régimen no tendencial. |
