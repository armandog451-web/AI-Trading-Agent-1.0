"""
ai_trading_agent.dual_strategy.metrics
======================================
Motor de Métricas Cuantitativas e Institucionales para OracleBot v2.
Calcula Sharpe, Sortino, Expectancy en R, Profit Factor, Drawdown y estabilidad OOS.
"""

from typing import List, Dict, Any, Optional
import numpy as np

from ai_trading_agent.dual_strategy.models import TradeFillRecord


class MetricsEngine:
    """Calculador determinista de métricas financieras con costes netos."""

    @staticmethod
    def calculate_performance_summary(
        trades: List[TradeFillRecord],
        initial_capital: float = 1000000.0,
        risk_free_rate: float = 0.04  # 4% T-Bills anualizado
    ) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "expectancy_r": 0.0,
                "expectancy_usd": 0.0,
                "net_pnl": 0.0,
                "gross_pnl": 0.0,
                "total_commissions": 0.0,
                "total_slippage": 0.0,
                "total_costs": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown_usd": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_holding_bars": 0.0,
                "overnight_gaps_total_usd": 0.0
            }

        total_trades = len(trades)
        net_pnls = [t.net_pnl for t in trades]
        gross_pnls = [t.gross_pnl for t in trades]
        r_multiples = [t.r_multiple for t in trades]

        wins = [p for p in net_pnls if p > 0]
        losses = [p for p in net_pnls if p < 0]

        win_rate = (len(wins) / total_trades) * 100.0

        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

        expectancy_r = float(np.mean(r_multiples))
        expectancy_usd = float(np.mean(net_pnls))

        total_net_pnl = sum(net_pnls)
        total_gross_pnl = sum(gross_pnls)
        total_commissions = sum(t.commission_usd for t in trades)
        total_slippage = sum(t.slippage_usd for t in trades)
        total_gaps = sum(t.overnight_gap_usd for t in trades)

        # Curva de equity y drawdown
        equity_curve = [initial_capital]
        for p in net_pnls:
            equity_curve.append(equity_curve[-1] + p)

        peak = initial_capital
        max_dd_usd = 0.0
        max_dd_pct = 0.0

        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd_usd = peak - eq
            dd_pct = (dd_usd / peak) * 100.0 if peak > 0 else 0.0
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Sharpe y Sortino anualizados basados en retornos por trade
        returns = np.array(net_pnls) / initial_capital
        std_ret = np.std(returns)
        mean_ret = np.mean(returns)

        # Factor de anualización aproximado (suponiendo 252 días y ~200 trades/año)
        ann_factor = np.sqrt(252.0)
        sharpe = float(((mean_ret * 252.0) - risk_free_rate) / (std_ret * ann_factor)) if std_ret > 1e-6 else 0.0

        downside_returns = [r for r in returns if r < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 1 else 0.0
        sortino = float(((mean_ret * 252.0) - risk_free_rate) / (downside_std * ann_factor)) if downside_std > 1e-6 else 0.0

        avg_bars = float(np.mean([t.holding_bars for t in trades]))

        return {
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(min(99.0, profit_factor), 2),
            "expectancy_r": round(expectancy_r, 2),
            "expectancy_usd": round(expectancy_usd, 2),
            "net_pnl": round(total_net_pnl, 2),
            "gross_pnl": round(total_gross_pnl, 2),
            "total_commissions": round(total_commissions, 2),
            "total_slippage": round(total_slippage, 2),
            "total_costs": round(total_commissions + total_slippage, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_drawdown_usd": round(max_dd_usd, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "avg_holding_bars": round(avg_bars, 1),
            "overnight_gaps_total_usd": round(total_gaps, 2)
        }
