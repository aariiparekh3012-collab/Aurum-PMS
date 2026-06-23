"""Performance calculation engine — pure Python, zero framework dependencies.

Implements:
  - Time-Weighted Rate of Return (TWRR / Modified Dietz sub-period linking)
  - Money-Weighted Rate of Return (MWRR / XIRR via Newton-Raphson)
  - Management fee accrual (flat % of AUM)
  - Performance fee accrual (high-water mark + hurdle)
  - NAV per unit computation

All monetary inputs are in paise (1 = 100 paise). Percentages are decimal
fractions internally (0.12 = 12%) and converted to display % only at the API
boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Sequence


# Value types

@dataclass(frozen=True)
class CashFlow:
    """A single external cash flow. Positive = contribution, negative = withdrawal."""
    date: date
    amount_paise: int


@dataclass(frozen=True)
class ValuationPoint:
    """Portfolio market value at a specific date."""
    date: date
    market_value_paise: int
    cost_value_paise: int
    cash_paise: int

    @property
    def total_value_paise(self) -> int:
        return self.market_value_paise + self.cash_paise


@dataclass
class FeeSchedule:
    mgmt_fee_pct: float        # annual %, e.g. 1.5 means 1.5% p.a.
    perf_fee_pct: float        # % of gains above hurdle, e.g. 20.0
    high_water_mark: bool = True
    hurdle_rate_pct: float = 0.0  # annual hurdle, e.g. 8.0


@dataclass
class ReturnResult:
    period: str       # '1M', '3M', '6M', '1Y', '3Y', 'SI'
    as_of: date
    twrr_pct: float   # display %
    mwrr_pct: float | None = None
    benchmark_pct: float | None = None

    @property
    def alpha_pct(self) -> float | None:
        if self.benchmark_pct is None:
            return None
        return round(self.twrr_pct - self.benchmark_pct, 4)


@dataclass
class FeeAccrual:
    as_of: date
    mgmt_fee_paise: int
    perf_fee_paise: int

    @property
    def total_paise(self) -> int:
        return self.mgmt_fee_paise + self.perf_fee_paise


# TWRR (Time-Weighted Rate of Return)

def compute_twrr(
    valuations: Sequence[ValuationPoint],
    cash_flows: Sequence[CashFlow],
) -> float:
    """
    Compute TWRR by linking sub-period returns (Modified Dietz).

    Each cash flow date creates a sub-period boundary. Returns the cumulative
    return as a decimal fraction (0.12 = 12%). Returns 0.0 if fewer than 2 points.
    """
    if len(valuations) < 2:
        return 0.0

    sorted_vals = sorted(valuations, key=lambda v: v.date)
    sorted_flows = sorted(cash_flows, key=lambda c: c.date)

    boundaries = sorted(
        {v.date for v in sorted_vals} | {c.date for c in sorted_flows}
    )
    boundaries = [b for b in boundaries
                  if sorted_vals[0].date <= b <= sorted_vals[-1].date]

    def _interp_value(d: date) -> int:
        before = [v for v in sorted_vals if v.date <= d]
        after = [v for v in sorted_vals if v.date >= d]
        if not before:
            return sorted_vals[0].total_value_paise
        if not after:
            return sorted_vals[-1].total_value_paise
        v0, v1 = before[-1], after[0]
        if v0.date == v1.date:
            return v0.total_value_paise
        frac = (d - v0.date).days / max((v1.date - v0.date).days, 1)
        return int(v0.total_value_paise + frac * (v1.total_value_paise - v0.total_value_paise))

    linked = 1.0
    for i in range(len(boundaries) - 1):
        start_date, end_date = boundaries[i], boundaries[i + 1]
        bmv = _interp_value(start_date)
        emv = _interp_value(end_date)

        period_days = max((end_date - start_date).days, 1)
        period_flows = [c for c in sorted_flows if start_date <= c.date < end_date]
        weighted_flows = sum(
            c.amount_paise * ((end_date - c.date).days / period_days)
            for c in period_flows
        )
        denominator = bmv + weighted_flows
        if denominator <= 0:
            continue
        sub_return = (emv - bmv - sum(c.amount_paise for c in period_flows)) / denominator
        linked *= (1 + sub_return)

    return round(linked - 1, 6)


# MWRR / XIRR (Money-Weighted Rate of Return)

def compute_mwrr(
    inception_value_paise: int,
    inception_date: date,
    cash_flows: Sequence[CashFlow],
    terminal_value_paise: int,
    terminal_date: date,
    max_iterations: int = 200,
    tolerance: float = 1e-8,
) -> float | None:
    """
    Solve for IRR (XIRR) using Newton-Raphson — annualised.

    Sign convention from the investor's perspective:
      - inception investment: investor pays out → negative
      - contributions (positive CashFlow): investor pays more → negative
      - withdrawals (negative CashFlow): investor receives → positive
      - terminal value: investor receives back → positive

    Returns annualised IRR as a decimal fraction, or None if it fails to converge.
    """
    if terminal_date <= inception_date:
        return None

    t_end = (terminal_date - inception_date).days / 365.25
    if t_end <= 0:
        return None

    # Build flows from investor perspective
    all_flows: list[tuple[float, float]] = []
    all_flows.append((0.0, float(-inception_value_paise)))
    for cf in cash_flows:
        if inception_date <= cf.date <= terminal_date:
            t = (cf.date - inception_date).days / 365.25
            # Contributions are cash-out for the investor (flip sign)
            all_flows.append((t, float(-cf.amount_paise)))
    all_flows.append((t_end, float(terminal_value_paise)))

    def _npv(r: float) -> float:
        return sum(amt / ((1 + r) ** t) for t, amt in all_flows)

    def _dnpv(r: float) -> float:
        return sum(-t * amt / ((1 + r) ** (t + 1)) for t, amt in all_flows)

    # Initial guess: (total received / total invested)^(1/years) - 1
    total_invested = abs(sum(a for _, a in all_flows if a < 0)) or 1.0
    total_received = sum(a for _, a in all_flows if a > 0) or 1.0
    r = (total_received / total_invested) ** (1.0 / t_end) - 1.0
    r = max(min(r, 10.0), -0.99)

    for _ in range(max_iterations):
        n = _npv(r)
        d = _dnpv(r)
        if abs(d) < 1e-12:
            return None
        r_new = r - n / d
        r_new = max(min(r_new, 10.0), -0.99)
        if abs(r_new - r) < tolerance:
            return round(r_new, 6)
        r = r_new

    return None  # did not converge


# Fee accrual

def compute_mgmt_fee(
    aum_paise: int,
    fee_schedule: FeeSchedule,
    days: int = 1,
) -> int:
    """Accrual = AUM x (annual_rate / 365) x days."""
    if fee_schedule.mgmt_fee_pct <= 0 or aum_paise <= 0:
        return 0
    daily_rate = (fee_schedule.mgmt_fee_pct / 100.0) / 365.0
    return int(aum_paise * daily_rate * days)


def compute_perf_fee(
    current_value_paise: int,
    high_water_mark_paise: int,
    fee_schedule: FeeSchedule,
    period_days: int = 365,
) -> tuple[int, int]:
    """
    Performance fee above high-water mark and hurdle.

    Returns (fee_paise, new_high_water_mark_paise).
    """
    if fee_schedule.perf_fee_pct <= 0:
        return 0, max(current_value_paise, high_water_mark_paise)

    hurdle_value = high_water_mark_paise * (
        (1 + fee_schedule.hurdle_rate_pct / 100.0) ** (period_days / 365.0)
    )
    gain_above_hurdle = current_value_paise - hurdle_value
    if gain_above_hurdle <= 0:
        return 0, max(current_value_paise, high_water_mark_paise)

    fee = int(gain_above_hurdle * fee_schedule.perf_fee_pct / 100.0)
    new_hwm = current_value_paise - fee
    return fee, max(new_hwm, high_water_mark_paise)


# NAV per unit

@dataclass
class NavPoint:
    date: date
    total_value_paise: int
    units_outstanding: float
    nav_paise: float = field(init=False)

    def __post_init__(self) -> None:
        self.nav_paise = (
            self.total_value_paise / self.units_outstanding
            if self.units_outstanding > 0 else 0.0
        )


def compute_nav_series(
    valuations: Sequence[ValuationPoint],
    initial_units: float,
    cash_flows: Sequence[CashFlow],
    initial_nav_paise: float = 1000.0,
) -> list[NavPoint]:
    """
    Track NAV per unit over time.
    Contributions buy units at the prevailing NAV; withdrawals redeem them.
    """
    if not valuations:
        return []

    sorted_vals = sorted(valuations, key=lambda v: v.date)
    sorted_flows = sorted(cash_flows, key=lambda c: c.date)

    units = initial_units
    current_nav = initial_nav_paise
    result: list[NavPoint] = []
    flow_idx = 0

    for val in sorted_vals:
        while flow_idx < len(sorted_flows) and sorted_flows[flow_idx].date <= val.date:
            cf = sorted_flows[flow_idx]
            if current_nav > 0:
                units += cf.amount_paise / current_nav
            flow_idx += 1
        if units > 0:
            current_nav = val.total_value_paise / units
        result.append(NavPoint(
            date=val.date,
            total_value_paise=val.total_value_paise,
            units_outstanding=units,
        ))

    return result


# Annualisation helper

def annualise(cumulative_return: float, days: int) -> float:
    """Convert a cumulative return to an annualised rate."""
    if days <= 0:
        return 0.0
    if cumulative_return <= -1:
        return -1.0
    return round((1 + cumulative_return) ** (365.25 / days) - 1, 6)


# Multi-period return computation

PERIODS = {
    "1M": 30,
    "3M": 91,
    "6M": 182,
    "1Y": 365,
    "3Y": 1095,
}


def compute_period_returns(
    valuations: Sequence[ValuationPoint],
    cash_flows: Sequence[CashFlow],
    as_of: date,
    inception_date: date,
) -> list[ReturnResult]:
    """
    Compute TWRR for standard periods (1M, 3M, 6M, 1Y, 3Y) and since inception (SI).
    Returns annualised figures for periods > 1Y, cumulative for <= 1Y.
    """
    results: list[ReturnResult] = []
    sorted_vals = sorted(valuations, key=lambda v: v.date)
    if not sorted_vals:
        return results

    def _twrr_for_window(start: date) -> float:
        window_vals = [v for v in sorted_vals if v.date >= start]
        window_flows = [c for c in cash_flows if c.date >= start]
        if len(window_vals) < 2:
            return 0.0
        return compute_twrr(window_vals, window_flows)

    for period_label, days in PERIODS.items():
        start = as_of - timedelta(days=days)
        if start < inception_date:
            continue
        raw = _twrr_for_window(start)
        display = annualise(raw, days) if days > 365 else raw
        results.append(ReturnResult(
            period=period_label,
            as_of=as_of,
            twrr_pct=round(display * 100, 4),
        ))

    # Since inception
    raw_si = compute_twrr(sorted_vals, list(cash_flows))
    si_days = (as_of - inception_date).days
    display_si = annualise(raw_si, si_days) if si_days > 365 else raw_si
    results.append(ReturnResult(
        period="SI",
        as_of=as_of,
        twrr_pct=round(display_si * 100, 4),
    ))

    return results
