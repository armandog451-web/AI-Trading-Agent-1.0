# WORKSPACE REPAIR AUDIT LOG

**Execution Timestamp:** 2026-10-21T15:44:53.226352
**Backup Directory:** `C:\Users\edsel\OneDrive\Documents\backups_repair_20261021_154453`

## 1. PRE-REPAIR FILE INTEGRITY & SHA-256 MANIFEST

| Source Path | Backup File | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\trading_robot.db` | `main_trading_robot.db` | 229376 | `182f92cea5c8ce658708de1fbd85b9cb3ec1e65dd537fae0f61ac2fdfaa4ccc5` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\trading_robot.db` | `repo_trading_robot.db` | 581632 | `9ebb74e786e0a4fbf723455a3a9ab3b81d59be4f77ee8852ca1122df38403096` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\ai_trading_agent.db` | `main_ai_trading_agent.db` | 110592 | `385e5f54c1c850f73c0efa79c54267ccdf4fc1f2597b91f8069fddcdbdf638c0` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\ai_trading_agent.db` | `repo_ai_trading_agent.db` | 208896 | `cddc201a20b2d197aa9d72e18314dffb5ea1df704216d5a33d0db4ced0426255` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\.env` | `main_.env` | 1529 | `a66518c403da42f0332e3455bb794b52406023eb24794b066b7145cff9ad7cac` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\.env` | `repo_.env` | 1529 | `a66518c403da42f0332e3455bb794b52406023eb24794b066b7145cff9ad7cac` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\trade_config.json` | `main_trade_config.json` | 660 | `ee71c40fa84518544d193366309590e4135939b0809fdcb17d77cd3e931fe8c1` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\trade_config.json` | `repo_trade_config.json` | 660 | `ee71c40fa84518544d193366309590e4135939b0809fdcb17d77cd3e931fe8c1` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\start_superrobot.bat` | `main_start_superrobot.bat` | 921 | `366b307aeaa46d80da13738f4f952ab5b6942a4758057bb1b032cf8055ddb0db` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\start.bat` | `main_start.bat` | 158 | `37bfec707f0aa5bd91d0684eb07f7249ef6f1643df9e00cc5b30c90fe60bd024` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\start_tradepulse.bat` | `main_start_tradepulse.bat` | 164 | `2a60269bbae84881cb0bfba1d2f4326f732c120705dd9bfd7e347ccb7408e095` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-main\run_superrobot.py` | `main_run_superrobot.py` | 675 | `fafc95d1c977667d3ab08db4fac4be7d88abd98cf5e904378c0c453a7dab9c19` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\start_superrobot.bat` | `repo_start_superrobot.bat` | 952 | `ab0dcbb0618d856336d42a37a92be536b12a267227911877fe5ce10191b6bb56` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\start.bat` | `repo_start.bat` | 163 | `834828c6452609c2664d358141729c281c10879f9d7969199bda62096789c340` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\start_tradepulse.bat` | `repo_start_tradepulse.bat` | 169 | `ee9ae73e46937b2066f380d628fa6ba5a52278242b83a27a52a2dc314291b67b` |
| `C:\Users\edsel\OneDrive\Documents\trading-app-repo\run_superrobot.py` | `repo_run_superrobot.py` | 698 | `1c51561a915f9cd7de0c05ebc3ea839ba87073555cbf0d7909d2c09389da21d7` |
| `C:\Users\edsel\Desktop\AI Trading Agent SuperRobot.lnk` | `desktop_AI Trading Agent SuperRobot.lnk` | 2127 | `1d82aa51a38fcf6a5e56a5827d769441fc762a6b779096c981afd9b8c9480db2` |
| `C:\Users\edsel\Desktop\AlgortimTrading Robot.lnk` | `desktop_AlgortimTrading Robot.lnk` | 2130 | `13e1fa7d337124717e7be2868bd857f6d63c03dec3e154622635ed89e466377b` |
| `C:\Users\edsel\Desktop\TradePulse Engine.lnk` | `desktop_TradePulse Engine.lnk` | 2127 | `9dccbe25130d5fc3b1824737b0b8504fad53ad817e7fd24de26a635c4bc851c7` |
| `C:\Users\edsel\Desktop\SuperBot.lnk` | `desktop_SuperBot.lnk` | 2334 | `37180b16c7be3f2c0b3313b369916272479bb7728be1f0a9227c5ffcdaec08fb` |

## 2. D21 CANONICAL ROW RESTORATION IN `trading-app-repo\trading_robot.db`

- **Strategy ID:** `D21_RangeCompress_5d`
- **Fingerprint Anchor:** `f885ec2db2422308` (MATCH: EXACT)
- **Lifecycle Status:** `PAPER`

### Value Reconciliation Comparison

| Field | Pre-Repair Corrupted Value (from EXP-FA0D6CAE) | Restored Canonical Value (Phase 10.7) |
| :--- | :--- | :--- |
| **robustness_score (PRS)** | `99.78` | `71.2` |
| **strategy_score (SQS)** | `46.11` | `69.17` |
| **total_trades** | `8` (Synthetic 15m SPY) | `102` (4-Yr 1D Universe) |
| **profit_factor** | `13.09` | `1.17` |
| **expectancy_dollars** | `230.88` | `65.0` |
| **updated_at** | `2026-10-06T03:23:03.571481+00:00` | `2026-10-05T19:12:00Z` |
