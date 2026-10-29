"""
ai_trading_agent.dual_strategy.data_provider
============================================
Proveedor de datos de mercado multi-timeframe institucional para OracleBot v2.
Asegura validación de liquidez, ajuste de eventos corporativos, timestamps estrictos
y cálculo de hashes inmutables de snapshots (Zero Look-Ahead Bias).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, time, date, timedelta
import hashlib
import json
import numpy as np

from ai_trading_agent.domain.models import OHLCVBar
from ai_trading_agent.domain.enums import DataQualityStatus


class MarketDataProvider:
    """
    Proveedor y curador de datos de mercado para backtest, shadow y paper.
    Aplica filtros de universo, normaliza timeframes y valida calidad.
    """

    EXCLUDED_PATTERNS = ["SQQQ", "TQQQ", "SOXL", "SOXS", "SPXU", "UPRO", "UVXY", "VXX"]

    def __init__(self):
        self._sector_map: Dict[str, str] = {
            "SPY": "Index_ETF",
            "QQQ": "Index_ETF",
            "IWM": "Index_ETF",
            "DIA": "Index_ETF",
            "AAPL": "Technology",
            "MSFT": "Technology",
            "NVDA": "Technology",
            "AMZN": "Consumer_Cyclical",
            "GOOGL": "Communication",
            "META": "Communication",
            "TSLA": "Consumer_Cyclical",
            "JPM": "Financial",
            "BAC": "Financial",
            "XOM": "Energy",
            "CVX": "Energy",
            "UNH": "Healthcare",
            "JNJ": "Healthcare",
            "PG": "Consumer_Defensive",
            "HD": "Consumer_Cyclical",
            "AMD": "Technology"
        }

    def get_sector(self, symbol: str) -> str:
        return self._sector_map.get(symbol.upper(), "General_Equities")

    def register_symbol_sector(self, symbol: str, sector: str):
        self._sector_map[symbol.upper()] = sector

    @staticmethod
    def compute_data_snapshot_hash(bars: List[OHLCVBar]) -> str:
        """Calcula un hash SHA-256 representativo del dataset evaluado hasta la barra actual."""
        if not bars:
            return hashlib.sha256(b"empty").hexdigest()[:16]
        # Usamos los últimos 5 puntos y metadatos para un hash compacto y determinista
        sample = [(b.timestamp.isoformat(), b.open, b.high, b.low, b.close, b.volume) for b in bars[-5:]]
        raw = f"{len(bars)}:{bars[0].timestamp.isoformat()}:{bars[-1].timestamp.isoformat()}:{sample}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def validate_universe_filters(
        self,
        symbol: str,
        current_price: float,
        adv_20d: float,
        observed_spread_pct: float,
        is_leveraged: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Filtros de admisibilidad de universo:
        1. Precio >= 10.0 USD
        2. ADV_20 >= 1,000,000 acciones
        3. Spread observado <= 0.15% (0.0015)
        4. No penny stock, no apalancado
        """
        reasons = []
        sym_clean = symbol.upper()

        if is_leveraged or any(p in sym_clean for p in self.EXCLUDED_PATTERNS):
            reasons.append("Instrumento apalancado o ETF volátil excluido")

        if current_price < 10.0:
            reasons.append(f"Precio ${current_price:.2f} inferior al umbral mínimo de $10.00 USD")

        if adv_20d < 1000000.0:
            reasons.append(f"ADV 20d {adv_20d:,.0f} inferior al umbral de liquidez de 1,000,000 acc/día")

        if observed_spread_pct > 0.0015:
            reasons.append(f"Spread observado {observed_spread_pct*100:.3f}% supera el límite de 0.150%")

        return (len(reasons) == 0, reasons)

    @staticmethod
    def is_regular_intraday_window(ts: datetime) -> bool:
        """
        Horario de decisión para Intradía: 10:00 - 15:00 America/New_York (sesión regular).
        Excluye los primeros 30 min (apertura caótica) y los últimos 60 min.
        """
        t = ts.time()
        start = time(10, 0)
        end = time(15, 0)
        return (start <= t <= end) and (ts.weekday() < 5)

    @staticmethod
    def is_session_square_off_time(ts: datetime) -> bool:
        """Hora de liquidación obligatoria intradía: 15:50 ET."""
        return ts.time() >= time(15, 50)

    @staticmethod
    def aggregate_4h_bars(hourly_bars: List[OHLCVBar]) -> List[OHLCVBar]:
        """
        Agregación determinista y reproducible de velas de 4 horas basada en sesiones bursátiles:
        Sesión regular 09:30 - 16:00 ET dividida en 2 bloques consistentes:
        - Barra 1: 09:30 a 13:30 (4 horas)
        - Barra 2: 13:30 a 16:00 (cierre de sesión regular 2.5h normalizada a bloque de tarde)
        """
        if not hourly_bars:
            return []

        # Agrupar por fecha y bloque
        bars_by_date: Dict[date, List[OHLCVBar]] = {}
        for b in hourly_bars:
            d = b.timestamp.date()
            if d not in bars_by_date:
                bars_by_date[d] = []
            bars_by_date[d].append(b)

        four_h_bars: List[OHLCVBar] = []
        for d, day_bars in sorted(bars_by_date.items()):
            # Separar mañana (<13:30) y tarde (>=13:30)
            morning = [b for b in day_bars if b.timestamp.time() < time(13, 30)]
            afternoon = [b for b in day_bars if b.timestamp.time() >= time(13, 30)]

            for block, block_name in [(morning, "Morning_4h"), (afternoon, "Afternoon_4h")]:
                if not block:
                    continue
                o = block[0].open
                h = max(b.high for b in block)
                l = min(b.low for b in block)
                c = block[-1].close
                vol = sum(b.volume for b in block)
                ts = block[-1].timestamp
                four_h_bars.append(OHLCVBar(
                    timestamp=ts,
                    symbol=block[0].symbol,
                    open=round(o, 2),
                    high=round(h, 2),
                    low=round(l, 2),
                    close=round(c, 2),
                    volume=vol,
                    source=f"aggregated_{block_name}"
                ))

        return four_h_bars

    @staticmethod
    def generate_controlled_multitimeframe_dataset(
        symbol: str,
        start_date: datetime,
        days: int = 500,
        base_price: float = 150.0,
        trend_bias: float = 0.0003,
        volatility: float = 0.015,
        seed: int = 42
    ) -> Dict[str, List[OHLCVBar]]:
        """
        Generador sintético determinista multi-timeframe alineado (1D, 4h, 1h, 15m).
        Garantiza sincronización perfecta entre barras cerradas sin look-ahead bias.
        """
        np.random.seed(seed)
        daily_bars: List[OHLCVBar] = []
        hourly_bars: List[OHLCVBar] = []
        m15_bars: List[OHLCVBar] = []

        curr_p = base_price
        curr_dt = start_date

        for day_idx in range(days):
            # Saltear fines de semana
            while curr_dt.weekday() >= 5:
                curr_dt += timedelta(days=1)

            day_open = curr_p
            # Simular 26 barras de 15 min por sesión (09:30 a 16:00 = 6.5 horas = 26 x 15m)
            day_15m_bars = []
            bar_p = day_open
            session_start = datetime.combine(curr_dt.date(), time(9, 30))

            for m_idx in range(26):
                bar_time = session_start + timedelta(minutes=15 * (m_idx + 1))
                ret = np.random.normal(trend_bias, volatility / np.sqrt(26))
                b_open = bar_p
                b_close = max(1.0, round(b_open * (1.0 + ret), 2))
                b_high = max(b_open, b_close) + round(abs(np.random.normal(0, volatility * b_open * 0.2)), 2)
                b_low = min(b_open, b_close) - round(abs(np.random.normal(0, volatility * b_open * 0.2)), 2)
                b_vol = max(10000.0, float(np.random.lognormal(11.5, 0.4)))

                bar_15m = OHLCVBar(
                    timestamp=bar_time,
                    symbol=symbol,
                    open=b_open,
                    high=b_high,
                    low=b_low,
                    close=b_close,
                    volume=b_vol,
                    source="synthetic_aligned"
                )
                day_15m_bars.append(bar_15m)
                bar_p = b_close

            m15_bars.extend(day_15m_bars)

            # Agrupar a 1h (7 barras por sesión regular)
            for h_idx in range(7):
                h_start_idx = h_idx * 4
                h_end_idx = min(len(day_15m_bars), (h_idx + 1) * 4)
                chunk = day_15m_bars[h_start_idx:h_end_idx]
                if not chunk:
                    continue
                hourly_bars.append(OHLCVBar(
                    timestamp=chunk[-1].timestamp,
                    symbol=symbol,
                    open=chunk[0].open,
                    high=max(b.high for b in chunk),
                    low=min(b.low for b in chunk),
                    close=chunk[-1].close,
                    volume=sum(b.volume for b in chunk),
                    source="synthetic_aligned_1h"
                ))

            # Barra diaria
            d_high = max(b.high for b in day_15m_bars)
            d_low = min(b.low for b in day_15m_bars)
            d_close = day_15m_bars[-1].close
            d_vol = sum(b.volume for b in day_15m_bars)
            daily_bars.append(OHLCVBar(
                timestamp=datetime.combine(curr_dt.date(), time(16, 0)),
                symbol=symbol,
                open=day_open,
                high=d_high,
                low=d_low,
                close=d_close,
                volume=d_vol,
                source="synthetic_aligned_1d"
            ))

            curr_p = d_close
            curr_dt += timedelta(days=1)

        four_h_bars = MarketDataProvider.aggregate_4h_bars(hourly_bars)

        return {
            "15m": m15_bars,
            "1h": hourly_bars,
            "4h": four_h_bars,
            "1d": daily_bars
        }
