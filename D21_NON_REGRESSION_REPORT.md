# INFORME DE NO-REGRESIÓN Y AISLAMIENTO DE D21 — ORACLEBOT V2

**Estrategia Auditada:** `D21_RangeCompress_5d`  
**Huella Criptográfica Congelada (Fingerprint):** `f885ec2db2422308`  
**Estado Registrado:** `StrategyStatus.PAPER`  
**SQS Oficial:** `69.17`  
**Fecha de Verificación:** 2026-10-29T18:59:00Z  

---

## 1. COMPROBACIÓN DE AISLAMIENTO E INTEGRIDAD

Durante toda la implementación de la Fase 0 a la Fase 9:
1. **Archivo de Definición de D21:** `D21_CONTROLLED_PAPER_VALIDATION_REPORT_FASE10_7.md` se mantuvo en modo solo lectura; no ha sido modificado.
2. **Registro en Base de Datos:** En la tabla `lab_strategy_registry` de `trading_robot.db`, el registro correspondiente a `strategy_id = 'D21_RangeCompress_5d'` no sufrió ninguna alteración.

---

## 2. COMPARATIVA DE INTEGRIDAD ANTES Y DESPUÉS

| Campo en `lab_strategy_registry` | Estado Previo (Fase 0) | Estado Posterior (Fase 9) | Veredicto |
| :--- | :--- | :--- | :--- |
| **Strategy ID** | `D21_RangeCompress_5d` | `D21_RangeCompress_5d` | **INALTERADO** |
| **Fingerprint** | `f885ec2db2422308` | `f885ec2db2422308` | **INALTERADO** |
| **Lifecycle Status** | `PAPER` | `PAPER` | **INALTERADO** |
| **SQS (Strategy Score)** | `69.17` | `69.17` | **INALTERADO** |
| **Robustness Score** | `71.20` | `71.20` | **INALTERADO** |
| **Reglas & Parámetros** | `holding_horizon_days: 5`, Donchian: 20 | `holding_horizon_days: 5`, Donchian: 20 | **INALTERADO** |
| **Universo D21** | `["SPY", "QQQ", "IWM", "DIA"]` | `["SPY", "QQQ", "IWM", "DIA"]` | **INALTERADO** |

---

## 3. GARANTÍAS DE CONVIVENCIA CON LAS NUEVAS ESTRATEGIAS

- **Separación Contable:** D21 utiliza sus propios identificadores de posición y orden (`D21_...`).
- **Independencia de R:** Las reservas de riesgo de `ORB_INTRADAY_BREAKOUT_V1` y `ORB_SWING_PULLBACK_V1` se gestionan en registros independientes, sin consumir el límite de riesgo asignado a D21 en su sandbox.
- **Protección contra Regresiones:** El test unitario `test_22_d21_preserves_fingerprint_and_evidence` en `test_oraclebot_v2_dual_strategy.py` valida automáticamente en cada ejecución que el registro de D21 permanezca congelado.
