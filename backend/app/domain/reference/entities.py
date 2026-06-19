"""Reference data entities — Securities, Strategies, Benchmarks, Fee Schedules."""
from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field


@dataclass
class Security:
    """Securities master — equities, debt, MF, ETF."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    isin: str = ""
    symbol: str = ""
    name: str = ""
    exchange: str = "NSE"
    instrument_type: str = "equity"
    sector: str = ""
    is_active: bool = True


@dataclass
class Benchmark:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""   # e.g. "NIFTY 50 TRI"


@dataclass
class BenchmarkValue:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    benchmark_id: uuid.UUID = field(default_factory=uuid.uuid4)
    as_of: dt.date = field(default_factory=dt.date.today)
    index_level: float = 0


@dataclass
class Strategy:
    """Investment strategy that portfolio accounts are managed under."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    approach: str = "discretionary"    # discretionary | model
    benchmark_id: uuid.UUID | None = None
    is_active: bool = True


@dataclass
class StrategyConstituent:
    """Model portfolio target weights."""
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    strategy_id: uuid.UUID = field(default_factory=uuid.uuid4)
    security_id: uuid.UUID = field(default_factory=uuid.uuid4)
    target_weight_pct: float = 0


@dataclass
class FeeSchedule:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    mgmt_fee_pct: float = 0       # e.g. 2.0 = 2%
    perf_fee_pct: float = 0       # e.g. 20.0 = 20% above HWM
    high_water_mark: bool = True


@dataclass
class Broker:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    sebi_reg_no: str = ""
