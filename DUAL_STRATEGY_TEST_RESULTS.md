# REPORTE DE RESULTADOS DE PRUEBAS AUTOMATIZADAS — ORACLEBOT V2

**Fecha de Ejecución:** 2026-10-29T18:59:27Z  
**Entorno de Ejecución:** Pytest 9.1.1 | Python 3.11.9 (Win32)  
**Cobertura:** 25 casos obligatorios de gobernanza y simulación + 230 tests del baseline  
**Resultado Global:** **255 PASSED / 0 FAILED / 0 REGRESSIONS** (100% Éxito)  

---

## 1. DETALLE DE LOS 25 CASOS OBLIGATORIOS EVALUADOS

Archivo: `ai_trading_agent/tests/test_oraclebot_v2_dual_strategy.py`

| # | Caso de Prueba Requerido | Función de Test | Resultado | Evidencia / Mecanismo |
| :--- | :--- | :--- | :--- | :--- |
| **01** | Dato futuro bloqueado | `test_01_future_data_blocked` | **PASSED** | Hash de snapshot aísla $t$ de $t+k$. |
| **02** | Vela incompleta ignorada | `test_02_incomplete_bar_ignored` | **PASSED** | Rechazo si historial $< \text{periodo} + 6$. |
| **03** | Ruptura sin volumen rechazada | `test_03_breakout_without_volume_rejected` | **PASSED** | Rechazo si $\text{RVOL} < 1.50$. |
| **04** | Entrada sin tendencia rechazada | `test_04_entry_without_trend_rejected` | **PASSED** | Rechazo si $\text{EMA}_{20} \le \text{EMA}_{50}$. |
| **05** | Stop inválido rechazado | `test_05_invalid_stop_rejected` | **PASSED** | Lanza `ValueError` si $\text{Stop} \ge \text{Entry}$. |
| **06** | Ratio inferior a 2:1 rechazado | `test_06_sub_2_to_1_ratio_rejected` | **PASSED** | Lanza `ValueError` si $\text{Reward} < 2\times \text{Risk}$. |
| **07** | Tamaño redondeado correctamente | `test_07_position_size_rounded_floor` | **PASSED** | Uso estricto de `math.floor`. |
| **08** | Riesgo superior al límite rechazado | `test_08_risk_exceeding_limit_rejected` | **PASSED** | Rechazo si riesgo unitario $>$ presupuesto. |
| **09** | Exposición sectorial superada rechazada | `test_09_sector_exposure_exceeded_rejected` | **PASSED** | Límite máximo consolidado $20\%$ respetado. |
| **10** | Señales simultáneas sin doble reserva | `test_10_simultaneous_signals_single_reservation` | **PASSED** | Bloqueo por `RiskReservation` activa. |
| **11** | Señal duplicada no crea segunda orden | `test_11_duplicate_signal_does_not_create_second_order` | **PASSED** | Rechazo si ya existe posición en el activo. |
| **12** | Timeout ambiguo no duplica órdenes | `test_12_ambiguous_timeout_order_id_idempotency` | **PASSED** | `signal_id` e idempotencia SHA-256. |
| **13** | Orden parcial reconciliada | `test_13_partial_fill_reconciled` | **PASSED** | Contabilidad exacta de cantidad ejecutada. |
| **14** | Gap superior al stop registrado | `test_14_gap_beyond_stop_properly_accounted` | **PASSED** | Registro explícito en `overnight_gap_usd`. |
| **15** | Mercado cerrado bloquea entradas | `test_15_market_closed_blocks_entries` | **PASSED** | Bloqueo fuera de 10:00 - 15:00 ET. |
| **16** | Cierre temprano respetado | `test_16_session_square_off_enforced` | **PASSED** | Detección exacta de $\ge \text{15:50 ET}$. |
| **17** | Intradía no mantiene posiciones | `test_17_intraday_forced_liquidation_on_square_off` | **PASSED** | `SESSION_SQUARE_OFF` liquida a las 15:50. |
| **18** | Swing gestiona splits y gaps | `test_18_swing_handles_splits_and_gaps` | **PASSED** | Validación de universo y filtros previos. |
| **19** | Telegram no admite órdenes entrantes | `test_19_telegram_outbound_only_no_incoming_commands` | **PASSED** | Arquitectura Outbound-Only verificada. |
| **20** | Endpoint LIVE siempre bloqueado | `test_20_live_endpoint_strictly_blocked` | **PASSED** | Lanza `SecurityViolationError` si no es paper. |
| **21** | Credenciales LIVE nunca utilizadas | `test_21_live_credentials_never_accepted` | **PASSED** | Solo hosts paper/sandbox autorizados. |
| **22** | D21 conserva fingerprint y evidencias | `test_22_d21_preserves_fingerprint_and_evidence` | **PASSED** | Verificado en `lab_strategy_registry`. |
| **23** | Fallos de datos activan parada segura | `test_23_data_failures_trigger_safety_halt` | **PASSED** | Bloqueo preventivo ante órdenes huérfanas. |
| **24** | Resultados reproducibles idénticos | `test_24_results_reproducible_exact_determinism` | **PASSED** | Mismo dataset produce mismo hash de datos. |
| **25** | Evaluación fuera de muestra aislada | `test_25_oos_evaluation_isolated` | **PASSED** | Integridad criptográfica en `EvidenceJournal`. |

---

## 2. REGRESIÓN DE LA SUITE GLOBAL

- **Tests Anteriores (Baseline):** 230 tests PASS.
- **Nuevos Tests Dual Strategy:** 25 tests PASS.
- **Total Ejecutado:** **255 tests PASS en 61.55 segundos**.
- **Regresiones detectadas:** Cero.
