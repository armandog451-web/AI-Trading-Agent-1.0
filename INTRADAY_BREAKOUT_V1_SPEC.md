# ESPECIFICACIÓN TÉCNICA FORMAL — ORB_INTRADAY_BREAKOUT_V1

**Estrategia:** `ORB_INTRADAY_BREAKOUT_V1`  
**Versión:** `1.0.0`  
**Fingerprint Criptográfico:** `617a2311672c8625`  
**Familia:** `Intraday Donchian Breakout Multi-Timeframe`  
**Estado:** `INSUFFICIENT_EVIDENCE` (Investigación Activa)  

---

## 1. DEFINICIÓN DEL UNIVERSO Y FILTROS PREVIOS

- **Activos Elegibles:** Acciones estadounidenses ordinarias de alta capitalización y ETFs de índices (SPY, QQQ, AAPL, MSFT, NVDA).
- **Precio Mínimo de Referencia:** $\ge \$10.00\text{ USD}$.
- **Volumen Medio Diario (ADV 20d):** $\ge 1,000,000\text{ acciones/día}$.
- **Spread Observado:** $\le 0.150\%$ ($15\text{ bps}$).
- **Exclusiones:** Penny stocks, instrumentos apalancados (SQQQ, TQQQ, SOXL, etc.) y activos en suspensión.

---

## 2. TEMPORALIDADES Y REGLAS DE TENDENCIA

- **Timeframe de Contexto:** 1 hora (1H).
- **Timeframe de Señal:** 15 minutos (15m).
- **Ventana de Decisión:** 10:00 – 15:00 America/New_York (sesión regular únicamente).
- **Filtro de Tendencia (1H):**
  $$\text{EMA}_{20}(1H) > \text{EMA}_{50}(1H)$$
  $$\text{Close}_{1H}(t-1) > \text{EMA}_{20}(1H)$$
  *Garantía causal:* Únicamente velas de 1H confirmadas y cerradas antes del tiempo de evaluación.

---

## 3. MECÁNICA DE RUPTURA (15 MINUTOS)

Una barra cerrada de 15m genera una propuesta alcista si y solo si cumple simultáneamente:
1. **Ruptura de Máximo Previo:** $\text{Close}_{15m}(t) > \max_{i=1}^{20} \text{High}_{15m}(t-i)$. (Excluye estrictamente la barra actual).
2. **Confirmación de Volumen Institucional:** $\text{Volume}_{15m}(t) \ge 1.50 \times \text{SMA}_{20}(\text{Volume}_{15m})$.
3. **Cuerpo Decisivo:** $\frac{|\text{Close} - \text{Open}|}{\text{High} - \text{Low}} \ge 0.50$ (Cuerpo representa $\ge 50\%$ del rango).
4. **Cierre en Cuartil Superior:** $\frac{\text{Close} - \text{Low}}{\text{High} - \text{Low}} \ge 0.75$ (Cierre dentro del $25\%$ superior de la vela).
5. **Spread Válido:** $\le 0.15\%$.

---

## 4. GESTIÓN DE ENTRADA, STOP Y SALIDA

- **Entrada:** Simulación en el precio de apertura de la barra siguiente ($t+1$), incluyendo deslizamiento adverso ($5\text{ bps}$) y comisiones ($\$0.005/\text{acción}$).
- **Stop Loss Inicial:**
  $$\text{Stop Inicial} = \min_{i=0}^{4} \text{Low}_{15m}(t-i) - 0.10 \times \text{ATR}_{14}(15m)$$
  Rechazo automático si $\text{Stop} \ge \text{Entry}$ o si la distancia de riesgo es $\le \$0.05$.
- **Objetivo de Beneficio (Take Profit):**
  $$\text{Target} = \text{Entry} + 2.0 \times (\text{Entry} - \text{Stop}) \quad [R:R \ge 2:1]$$
- **Liquidación Obligatoria (Square-off):** A las **15:50 ET**, toda posición abierta es liquidada forzosamente a precio de mercado. Ninguna posición intradía permanece abierta de la noche a la mañana.
- **Límites de Frecuencia:** Máximo 2 entradas por símbolo/día; máximo 4 nuevas posiciones intradía en cartera/día.
