# POST-INSTALL SYSTEM HEALTH CHECK — AI TRADING AGENT

**Fecha de Evaluación:** 2026-10-05T23:10:00-04:00  
**Entorno Operativo:** Windows 11 (64-bit) — Nueva Instalación  
**Ruta del Proyecto:** `C:\Users\edsel\OneDrive\Documents\trading-app-main`  
**Sujeto de Validación:** `D21_RangeCompress_5d` en modo `PAPER`  

---

## 1. REPOSITORY INTEGRITY

* **Estado de Git:** No inicializado / Sin directorio `.git` (Carpeta extraída desde archivo ZIP de exportación).
* **Branch Actual:** N/A (no versionado en este directorio).
* **HEAD Commit:** N/A.
* **Acceso a origin/main:** Bloqueado (falta metadatos `.git`).
* **Working Tree:** N/A.
* **Archivos Críticos Faltantes:**
  * `ai_trading_agent/scratch/fase10_discovery_summary.json`
  * `ai_trading_agent/scratch/fase8_1_audit_summary.json`
  * `ai_trading_agent/scratch/fase9_discovery_summary.json`
  * Artefactos de auditoría de holdout en `ai_trading_agent/scratch/`
* **Veredicto:** `REPO_STATUS = FAIL`

---

## 2. PYTHON ENVIRONMENT

* **Python Runtime:** Python 3.14.7 (64-bit)
* **Entorno Virtual:** Presente en `C:\Users\edsel\OneDrive\Documents\trading-app-main\.venv`
* **Pip Version:** pip 26.2.1
* **Dependencias:** Instaladas en `.venv` (fastapi, uvicorn, pydantic, pandas, numpy, yfinance, moomoo, etc.).
* **Conflictos detectados en pip (`pip check`):**
  * `alpaca-trade-api 3.2.0`: Desalineación estricta de versiones con `msgpack`, `PyYAML`, `urllib3` y `websockets`.
  * Entorno global de Windows no posee `pytest` instalado (debe ejecutarse obligatoriamente desde `.venv`).
* **Veredicto:** `ENVIRONMENT_STATUS = FAIL`

---

## 3. CONFIGURATION FILES

| Archivo / Objeto | Estado | Observación |
| :--- | :---: | :--- |
| **`.env`** | `PRESENT` | Cargado correctamente |
| **`config.py`** | `PRESENT` | Configuración raíz operativa |
| **`ai_trading_agent/config/settings.py`** | `PRESENT` | Validación Pydantic Settings funcional |
| **`trade_config.json`** | `PRESENT` | Parámetros de trading presentes |
| **`AgentSettings`** | `PRESENT` | Instancia creada y validada |
| **Broker Config** | `PRESENT` | Configuración Moomoo / Alpaca presente |
| **Database Config** | `PRESENT` | `trading_robot.db` y `ai_trading_agent.db` referenciadas |
| **Logging Config** | `PRESENT` | Logger de eventos y SQLite configurados |
| **Paper Trading Config** | `PRESENT` | Perfil de $1,000,000 USD definido |

---

## 4. SECRETS / CREDENTIALS CHECK

*(No se imprimen ni exponen secretos)*

* **Telegram Bot Token:** `PRESENT`
* **Telegram Chat ID:** `PRESENT`
* **Moomoo Gateway Host/Port (127.0.0.1:11111):** `PRESENT`
* **Moomoo Paper Account ID:** `PRESENT`
* **Alpaca Paper API Key:** `MISSING` (vacío en `.env`)
* **Alpaca Paper Base URL:** `PRESENT` (Sandbox `https://paper-api.alpaca.markets`)
* **Live Trading Credentials:** `DISABLED / NOT USED` (Confirmado: ningún endpoint real activo)

---

## 5. DATABASE HEALTH

* **Archivo SQLite (`trading_robot.db`):** Accesible (212,992 bytes).
* **Integridad SQLite (`PRAGMA integrity_check`):** `ok` (Sin corrupción).
* **Tablas Críticas:** `signals`, `strategy_metrics`, `settings`, `logs`, `lab_strategy_registry`, `lab_hypotheses`, `lab_experiments`.
* **Prueba de Lectura/Escritura:** `PASS`
* **Tabla `lab_strategy_registry`:** Disponible.
* **Registro de `D21_RangeCompress_5d` en DB:** `MISSING` (No figura registrada en `lab_strategy_registry`).
* **Veredicto:** `DATABASE_STATUS = FAIL`

---

## 6. D21 STRATEGY INTEGRITY

* **Strategy ID:** `D21_RangeCompress_5d`
* **Fingerprint Esperado:** `f885ec2db2422308`
* **Fingerprint Calculado:** `f885ec2db2422308` (`MATCH EXACTO`)
* **Parámetros Sellados Verificados:**
  * Timeframe: `1D`
  * Range Compression: `High(t-1) - Low(t-1) < 0.60 * ATR14(t-1)`
  * Trend Filter: `Close(t-1) > SMA20(t-1)`
  * Entry Timing: `Next session open`
  * Holding Horizon: `Máximo 5 días` (Time exit)
  * Stop Loss: `2.0 * ATR14`
  * Profit Target: `NONE`
  * Universe: `[SPY, QQQ, IWM, DIA]`
* **Estado en Registro SQLite:** Ausente en la base de datos de esta máquina.
* **Veredicto:** `D21_INTEGRITY = FAIL` (Espec y hash son idénticos, pero no está persistida en SQLite).

---

## 7. LIFECYCLE STATUS

* **Estado Persistido Esperado:** `StrategyStatus.PAPER`
* **Estado Actual en DB:** `NO ENCONTRADA`
* **Candidate Gating Rules:** Definidas e inmutables en código.
* **Robustness Score (PRS):** Requiere $\ge 60.0$ (D21 registró $71.2$ en reporte).
* **Strategy Quality Score (SQS):** $69.17$
* **Estado Aprobado (`APPROVED`):** `FALSE` (Bloqueo estricto por $SQS < 70.00$).
* **Veredicto:** `FAIL` (Estado PAPER no está persistido en la base de datos local).

---

## 8. PAPER BROKER CHECK

* **Broker Environment:** `PAPER` (Sandbox aislado).
* **Conexión a Paper Broker Interno:** `PASS`
* **Account Info Accesible:** Sí, balance de referencia `$1,000,000.00 USD` (Cash: `$1,000,000.00 USD`).
* **Posiciones Abiertas:** `[]` (Sin posiciones activas).
* **Moomoo OpenD Local (127.0.0.1:11111):** Puerto abierto; fallback de simulación activo si el gateway OpenD no está autenticado.
* **Órdenes de Prueba:** Ninguna orden real ni artificial fue enviada.
* **Veredicto:** `BROKER_PAPER_STATUS = PASS`

---

## 9. LIVE SAFETY CHECK

* **Live Trading:** `DISABLED` (El enum `TradingMode` no contiene la opción `LIVE`).
* **Modo Actual de Operación:** `ANALYSIS_ONLY` (Imposibilidad física de enrutar órdenes).
* **Kill Switch Global:** Operativo (`KILL_SWITCH_ACTIVE = False`, listo para armar).
* **Protección de Promoción Automática:** Bloqueada por diseño en `LifecycleManager`.
* **Veredicto:** `LIVE_SAFETY = PASS`

---

## 10. RISK ENGINE CHECK

* **Reference Equity:** `$1,000,000.00 USD`
* **Risk per Trade:** `0.25%` ($\le \$2,500.00$ cap nominal por operación).
* **Max Allocation per Symbol:** `10.0%` ($\le \$100,000.00$ notional).
* **Max Concurrent Positions:** `2` (Exposición bruta máxima $20\%$).
* **Daily Loss Limit:** `1.0%` ($\le \$10,000.00$ freno de emergencia).
* **Drawdown Circuit Breaker:** `10.0%` ($\le \$100,000.00$).
* **Consecutive Loss Brake:** `3` operaciones perdedoras consecutivas pausan el trading.
* **Simulación Interna de Propuesta:** Evaluada exitosamente con `DeterministicRiskEngine.assess_proposal()`:
  * Propuesta SPY ($5 nominal risk): Aprobó 200 acciones, $1,000 riesgo, $100,000 capital asignado.
* **Veredicto:** `RISK_ENGINE_STATUS = PASS`

---

## 11. DATA PIPELINE CHECK

* **Proveedor de Datos:** Yahoo Finance (`yfinance`) con fallback resiliente.
* **Activos Verificados (Barras diarias cerradas al 2026-10-05):**
  * `SPY`: 35 barras, última barra: 2026-10-05, Cierre: $774.83
  * `QQQ`: 35 barras, última barra: 2026-10-05, Cierre: $756.20
  * `IWM`: 35 barras, última barra: 2026-10-05, Cierre: $283.38
  * `DIA`: 35 barras, última barra: 2026-10-05, Cierre: $512.11
* **Geometría de Barras:** Válida ($High \ge Low$, $High \ge Open$, $High \ge Close$).
* **Detección de Barras Futuras:** Ninguna detectada.
* **Alineación Temporal:** Consistente con horario oficial de Wall Street (`America/New_York`).
* **Veredicto:** `DATA_PIPELINE_STATUS = PASS`

---

## 12. SCHEDULER / RUNTIME CHECK

* **Market Calendar Service:** Activo y sincronizado con el calendario de la NYSE.
* **Hora Actual del Sistema (ET):** 2026-10-05 23:10 ET
* **Próxima Apertura de Mercado:** `2026-10-06 09:30:00-04:00 (EDT)`
* **Próximo Cierre de Mercado:** `2026-10-06 16:00:00-04:00 (EDT)`
* **Lógica Next-Open:** Lista para evaluar en apertura tras confirmación de barra diaria cerrada.
* **Veredicto:** `PASS` (Próxima ejecución programada: Apertura del martes 06 de octubre a las 09:30 EDT).

---

## 13. PROCESS PERSISTENCE CHECK

* **Servicio Windows / Tarea Programada:** NO configurado para `trading-app-main`.
* **Arranque tras Reboot:** Requiere ejecución manual o configurar `INSTALAR_ARRANQUE_CON_WINDOWS.bat`.
* **Persistencia de Logs y Base de Datos:** `PASS` (Los archivos `.db` y logs se mantienen en disco).
* **Veredicto:** `WARNING`

---

## 14. LOGGING HEALTH

* **Directorio de Logs y Permisos:** `PASS`
* **Persistencia en SQLite (`logs` table):** `PASS`
* **Evento de Prueba:** Se insertó exitosamente el evento no operativo `SYSTEM_HEALTH_CHECK` en la tabla `logs` con timestamp `2026-10-05 23:09:08`.
* **Veredicto:** `PASS`

---

## 15. FULL TEST SUITE

* **Comando:** `python run_agent_tests.py` (ejecutado con `.venv`)
* **Total Tests Ejecutados:** 228
* **Tests Aprobados:** 211
* **Tests Fallidos:** 17
* **Causa Raíz de los Fallos:**
  1. Ausencia de `D21_RangeCompress_5d` en la tabla `lab_strategy_registry` (5 tests fallidos).
  2. Falta de archivos de resumen y artefactos en `ai_trading_agent/scratch/` debido a exclusión en `.gitignore` durante la migración ZIP (12 tests fallidos).
* **Veredicto:** `FAIL` (Regla: *Si cualquier test falla, NO iniciar Paper Runtime*).

---

## 16. DRY-RUN PAPER CYCLE

Se ejecutó un ciclo de simulación controlado de punta a punta:
1. **Carga de datos:** 35 barras diarias de SPY desde yfinance (último cierre: 2026-10-05).
2. **Cálculo de indicadores:** $ATR14 = \$7.28$, $SMA20 = \$764.31$, Rango diario: $\$6.98$ ($0.96 \times ATR$).
3. **Evaluación de reglas D21:** Range compression ($<0.6 \times ATR$): False | Trend ($Close > SMA20$): True.
4. **Formulación de orden:** TradeProposal evaluado con stop nominal de $2.0 \times ATR$.
5. **Paso por Risk Engine:** Aprobó orden simulada de 129 acciones con riesgo $\le \$2,500$ USD.
6. **Bloqueo de seguridad:** La orden fue interceptada y bloqueada antes de alcanzar cualquier endpoint de broker.
* **Veredicto:** `DRY_RUN_STATUS = PASS`

---

## 17. PORT / FIREWALL / NETWORK CHECK

* **DNS y Conectividad Externa:** `PASS` (Google, Yahoo Finance, Alpaca, Telegram accesibles).
* **Puerto Local 11111 (Moomoo OpenD):** `REACHABLE`
* **Firewall / Proxy:** Sin bloqueos activos.
* **Veredicto:** `NETWORK_STATUS = PASS`

---

## 18. SYSTEM CLOCK

* **Hora del Sistema:** Lunes, 05 de Octubre de 2026, 11:10 PM
* **Timezone de Windows:** Eastern Standard Time / Daylight Time (`UTC-04:00 EDT`)
* **Timezone del Bot:** `America/New_York` (`UTC-04:00 EDT`)
* **Alineación:** Perfecta discrepancia 0 horas con el horario oficial de Wall Street.
* **Servicio NTP Windows (`w32time`):** Detenido (`0x80070426`) $\rightarrow$ Reloj en hora pero sin daemon NTP activo.
* **Veredicto:** `WARNING`

---

## 19. FINAL STARTUP READINESS MATRIX

| Componente | Estado | ¿Crítico? | Acción Requerida |
| :--- | :---: | :---: | :--- |
| **Repository** | `FAIL` | Sí | Inicializar repositorio Git y sincronizar con `origin/main` |
| **Python Environment** | `FAIL` | Sí | Corregir dependencias de `alpaca-trade-api` e instalar `pytest` en entorno global si se usa sin `.venv` |
| **Dependencies** | `WARNING` | Sí | Resolver advertencias de pins estrictos en pip |
| **Config** | `PASS` | Sí | Ninguna (archivos `.env`, `settings.py`, `config.py` OK) |
| **Secrets** | `WARNING` | Sí | Configurar `ALPACA_API_KEY` si se operará en Alpaca Paper |
| **Database** | `FAIL` | Sí | Registrar `D21_RangeCompress_5d` en `lab_strategy_registry` con estado `PAPER` |
| **D21 Fingerprint** | `FAIL` | Sí | Inyectar spec sellada en SQLite para que coincida con `f885ec2db2422308` |
| **Lifecycle** | `FAIL` | Sí | Persistir formalmente `StrategyStatus.PAPER` en base de datos |
| **Paper Broker** | `PASS` | Sí | Ninguna (Sandbox de $1M operativo) |
| **Live Safety** | `PASS` | Sí | Ninguna (Live físicamente bloqueado) |
| **Risk Engine** | `PASS` | Sí | Ninguna (Límites de $1M, 0.25%, cap $2.5k verificados) |
| **Data Pipeline** | `PASS` | Sí | Ninguna (SPY, QQQ, IWM, DIA al día) |
| **Scheduler** | `PASS` | No | Ninguna (Sincronizado con apertura a las 09:30 EDT) |
| **Persistence** | `WARNING` | No | Ejecutar `INSTALAR_ARRANQUE_CON_WINDOWS.bat` para arranque automático |
| **Logging** | `PASS` | Sí | Ninguna (Evento `SYSTEM_HEALTH_CHECK` persistido) |
| **Tests** | `FAIL` | Sí | Subsanar 17 tests fallidos para alcanzar 228/228 PASS |
| **Dry Run** | `PASS` | Sí | Ninguna (Ciclo completo validado sin fallas) |
| **Network** | `PASS` | Sí | Ninguna (Todos los puertos y APIs accesibles) |
| **System Clock** | `WARNING` | Sí | Iniciar servicio `w32time` para sincronización NTP continua |

---

## 20. FINAL VERDICT

# `SYSTEM_NOT_READY`

### Lista Exacta de Correcciones Requeridas antes de Iniciar Paper Runtime:

1. **Restaurar el Registro de D21 en SQLite:**
   * La estrategia `D21_RangeCompress_5d` con fingerprint `f885ec2db2422308`, score PRS $71.2$, SQS $69.17$ y status `StrategyStatus.PAPER` debe insertarse formalmente en la tabla `lab_strategy_registry` de `trading_robot.db`.
2. **Restaurar Artefactos de Auditoría de Fases Anteriores:**
   * Copiar la carpeta `ai_trading_agent/scratch/` desde la máquina de desarrollo original (contiene `fase10_discovery_summary.json`, `fase8_1_audit_summary.json`, `fase9_discovery_summary.json` y los reportes de holdout). Estos archivos fueron excluidos por `.gitignore` durante la compresión del ZIP.
3. **Alcanzar Suite de Pruebas 100% PASS:**
   * Con los dos puntos anteriores corregidos, volver a ejecutar `python run_agent_tests.py` hasta obtener los **228 / 228 PASS**.
4. **Inicializar Control de Versiones Git:**
   * Ejecutar `git init` y vincular el remoto `https://github.com/armandog451-web/AI-Trading-Agent-1.0.git` o `trading-app` para tener trazabilidad de commits.
5. **Activar Persistencia de Proceso (Opcional pero Recomendado):**
   * Configurar el script de arranque automático en Windows para garantizar continuidad 24/7.

> **Regla de Gobernanza:**  
> **NO INICIAR PAPER RUNTIME HASTA QUE SE HAYAN CORREGIDO LOS PUNTOS CRÍTICOS Y LA SUITE DE PRUEBAS REGISTRE 0 FALLOS.**
