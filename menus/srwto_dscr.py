# srwto_dscr.py
from typing import Dict, Any, Optional, Tuple
import math

def annual_from_monthly(value_monthly: float) -> float:
    return float(value_monthly) * 12.0

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def compute_dscr_and_breakdown(
    *,
    days_per_month: float,
    km_per_day: float,
    fare_per_km: float,
    fuel_cost_per_litre: float,
    vehicle_kmpl: float,
    oil_spares_annual: float,
    taxes_annual: float,
    insurance_annual: float,
    maintenance_annual: float,
    staff_salary_annual: float,
    drawings_annual: float,
    garage_rent_annual: float,
    others_annual: float,
    depreciation_rate_pct: float,   # e.g. 10 for 10%
    interest_on_loan_annual: float,
    tax_provision_annual: float,
    repayment_obligation_annual: float
) -> Dict[str, Any]:
    """
    Compute annual amounts and DSCR according to the worksheet.
    Returns dict with breakdown and DSCR (float or None if repayment_obligation_annual <= 0).
    All inputs are treated as annual amounts where indicated; income is computed from days/km/fare.
    """
    # sanitize
    days_per_month = safe_float(days_per_month)
    km_per_day = safe_float(km_per_day)
    fare_per_km = safe_float(fare_per_km)
    fuel_cost_per_litre = safe_float(fuel_cost_per_litre)
    vehicle_kmpl = max(1e-6, safe_float(vehicle_kmpl))  # avoid divide by zero

    # annual gross operating income = days_per_month * km_per_day * fare_per_km * 12
    gross_operating_income = days_per_month * km_per_day * fare_per_km * 12.0

    # Fuel expense formula: total_km_per_year / kmpl * cost_per_litre
    total_km_per_year = days_per_month * km_per_day * 12.0
    fuel_expense_annual = (total_km_per_year / vehicle_kmpl) * fuel_cost_per_litre

    # Other expenditures are provided as annual values already
    # Depreciation as percent of gross operating income
    depreciation_annual = gross_operating_income * (safe_float(depreciation_rate_pct) / 100.0)

    # Total expenditures (excluding interest/tax provision which are added separately in lines 16 & 17)
    total_expenditures = (
        fuel_expense_annual
        + safe_float(oil_spares_annual)
        + safe_float(taxes_annual)
        + safe_float(insurance_annual)
        + safe_float(maintenance_annual)
        + safe_float(staff_salary_annual)
        + safe_float(drawings_annual)
        + safe_float(garage_rent_annual)
        + safe_float(others_annual)
        + depreciation_annual
    )

    # From worksheet: Total Expenses (15 + 16 + 17) where 16 = interest_on_loan_annual, 17 = tax_provision_annual
    total_expenses_plus_interest_tax = total_expenditures + safe_float(interest_on_loan_annual) + safe_float(tax_provision_annual)

    # Net income (4 - 18)
    net_income_annual = gross_operating_income - total_expenses_plus_interest_tax

    # Net surplus for DSCR (19 + 14 + 16) => Net income + Depreciation + Interest on loan
    net_surplus_for_dscr = net_income_annual + depreciation_annual + safe_float(interest_on_loan_annual)

    # DSCR = net_surplus_for_dscr / repayment_obligation_annual
    repayment = safe_float(repayment_obligation_annual)
    dscr = None
    if repayment > 0:
        dscr = net_surplus_for_dscr / repayment

    return {
        "gross_operating_income": gross_operating_income,
        "fuel_expense_annual": fuel_expense_annual,
        "depreciation_annual": depreciation_annual,
        "total_expenditures_including_depr": total_expenditures,
        "interest_on_loan_annual": interest_on_loan_annual,
        "tax_provision_annual": tax_provision_annual,
        "total_expenses_plus_interest_tax": total_expenses_plus_interest_tax,
        "net_income_annual": net_income_annual,
        "net_surplus_for_dscr": net_surplus_for_dscr,
        "repayment_obligation_annual": repayment,
        "dscr": dscr
    }


def find_adjustments_for_target_dscr(
    inputs: Dict[str, Any],
    *,
    target_dscr: float = 2.5,
    days_max: int = 30,
    depreciation_min_pct: float = 5.0,
    depreciation_max_pct: float = 15.0,
    step_days: int = 1,
    step_depr_pct: float = 1.0,
    step_reduce: float = 0.05
) -> Dict[str, Any]:
    """
    Try to find adjusted inputs that reach DSCR >= target_dscr.
    Strategy (greedy):
      1. Increase days_per_month up to days_max (in steps of step_days).
      2. If still short, increase depreciation rate up to depreciation_max_pct (in steps).
      3. If still short, proportionally reduce drawings and others down to zero in steps (each step reduces by step_reduce fraction).
    Returns dictionary with:
      - success (bool),
      - dscr (float) final,
      - adjusted_inputs (dict),
      - breakdown (dict)
      - attempted_steps (int)
    """
    # copy base inputs
    base = dict(inputs)  # shallow copy
    # normalize numeric fields
    for k, v in base.items():
        base[k] = safe_float(v)

    original_days = int(math.ceil(base.get("days_per_month", 0)))
    original_depr = safe_float(base.get("depreciation_rate_pct", depreciation_min_pct))
    original_drawings = safe_float(base.get("drawings_annual", 0.0))
    original_others = safe_float(base.get("others_annual", 0.0))

    best = None
    attempts = 0

    # iterate days
    for days in range(original_days, days_max + 1, step_days if step_days>0 else 1):
        base["days_per_month"] = days
        # iterate depreciation
        depr = original_depr
        while depr <= depreciation_max_pct + 1e-9:
            base["depreciation_rate_pct"] = depr
            # try reducing drawings/others in steps
            reduce_fraction = 0.0
            while reduce_fraction <= 1.000001:
                attempts += 1
                base["drawings_annual"] = original_drawings * (1.0 - reduce_fraction)
                base["others_annual"] = original_others * (1.0 - reduce_fraction)
                breakdown = compute_dscr_and_breakdown(**base)
                dscr = breakdown["dscr"]
                if dscr is not None and dscr >= target_dscr:
                    # success - return first minimal-change solution by this search order
                    adjusted_inputs = {
                        "days_per_month": base["days_per_month"],
                        "depreciation_rate_pct": base["depreciation_rate_pct"],
                        "drawings_annual": base["drawings_annual"],
                        "others_annual": base["others_annual"]
                    }
                    return {
                        "success": True,
                        "attempts": attempts,
                        "final_dscr": dscr,
                        "adjusted_inputs": adjusted_inputs,
                        "breakdown": breakdown
                    }
                reduce_fraction += step_reduce
            depr += step_depr_pct

    # if we exit loop, not found
    # return best (last evaluated)
    last_breakdown = compute_dscr_and_breakdown(**base)
    return {
        "success": False,
        "attempts": attempts,
        "final_dscr": last_breakdown.get("dscr"),
        "adjusted_inputs": {
            "days_per_month": base["days_per_month"],
            "depreciation_rate_pct": base["depreciation_rate_pct"],
            "drawings_annual": base.get("drawings_annual"),
            "others_annual": base.get("others_annual")
        },
        "breakdown": last_breakdown
    }
