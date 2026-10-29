# ESPECIFICACIÓN TÉCNICA FORMAL — ORB_SWING_PULLBACK_V1

**Estrategia:** `ORB_SWING_PULLBACK_V1`  
**Versión:** `1.0.0`  
**Fingerprint Criptográfico:** `7e830e2de5df3eec`  
**Familia:** `Daily/4h Trend Pullback Reversal`  
**Estado:** `INSUFFICIENT_EVIDENCE` (Investigación Activa)  

---

## 1. DEFINICIÓN DEL UNIVERSO Y FILTROS PREVIOS

- **Activos Elegibles:** Acciones estadounidenses ordinarias y ETFs con precios históricos ajustados por splits y dividendos.
- **Precio Mínimo de Referencia:** $\ge \$10.00\text{ USD}$.
- **Volumen Medio Diario (ADV 20d):** $\ge 1,000,000\text{ acciones/día}$.
- **Spread Observado:** $\le 0.150\%$.

---

## 2. TEMPORALIDADES Y REGLAS DE TENDENCIA DIARIA (1D)

- **Timeframe de Contexto:** Diario (1D).
- **Timeframe de Señal:** 4 horas (4h, bloques estándar de sesión regular: 09:30-13:30 y 13:30-16:00 ET).
- **Filtro de Tendencia Macro (1D):**
  $$\text{EMA}_{50}(1D) > \text{EMA}_{200}(1D)$$
  $$\text{Close}_{1D}(t-1) > \text{EMA}_{50}(1D)$$
  $$\text{EMA}_{50}(1D, t) > \text{EMA}_{50}(1D, t-10) \quad [\text{Pendiente positiva confirmada}]$$
  *Garantía causal:* Barras diarias cerradas antes de la sesión actual únicamente.

---

## 3. MECÁNICA DE RETROCESO Y GATILLO (4 HORAS)

Evaluado sobre las últimas 5 barras completas de 4 horas:
1. **Toque de Soporte Dinámico:** Al menos una vela en las últimas 5 ha tocado o cruzado la $\text{EMA}_{20}(4h)$ ($\text{Low} \le \text{EMA}_{20} \le \text{High}$ o $\text{Low} \le \text{EMA}_{20}$).
2. **Respeto de Tendencia Local:** Ninguna de las 5 velas ha cerrado por debajo de la $\text{EMA}_{50}(4h)$ ($\text{Close}_i \ge \text{EMA}_{50}$).
3. **Vela de Reversión (Gatillo):** $\text{Close}_{4h}(t) > \text{High}_{4h}(t-1)$ (el cierre supera el máximo de la barra previa).
4. **Confirmación por encima de la media:** $\text{Close}_{4h}(t) > \text{EMA}_{20}(4h)$.

---

## 4. GESTIÓN DE ENTRADA, STOP, OBJETIVO Y RIESGO NOCTURNO

- **Entrada:** Apertura de la siguiente barra de 4h con fricción de deslizamiento y comisiones.
- **Stop Loss Inicial:**
  $$\text{Stop Inicial} = \min_{i=0}^{4} \text{Low}_{4h}(t-i) - 0.10 \times \text{ATR}_{14}(4h)$$
- **Objetivo de Beneficio (Take Profit):**
  $$\text{Target} = \text{Entry} + 2.0 \times (\text{Entry} - \text{Stop}) \quad [R:R \ge 2:1]$$
- **Horizonte Temporal Máximo:** 10 sesiones bursátiles completas ($\approx 20$ barras de 4h). Al vencer el horizonte temporal, se ejecuta salida por tiempo (`TIME_EXIT`) en el cierre.
- **Modelado de Riesgo Nocturno (Overnight):** Si la apertura de una sesión presenta un Gap bajista por debajo del stop planificado, la orden stop se ejecuta en el precio de apertura del gap, registrando la pérdida adicional por deslizamiento de gap (`overnight_gap_usd`).
