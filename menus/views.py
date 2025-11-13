# views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .srwto_dscr import compute_dscr_and_breakdown, find_adjustments_for_target_dscr
from django.conf import settings
from django.templatetags.static import static
import os
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from django.http import HttpResponse
from io import BytesIO
from rest_framework.decorators import api_view


@api_view(['POST'])
def dscr_calculate(request):
    payload = request.data


    target = float(payload.get("target_dscr", 2.5))
    payload.pop("target_dscr", None)

   
    breakdown = compute_dscr_and_breakdown(**payload)
    suggestion = find_adjustments_for_target_dscr(payload, target_dscr=target)

    return Response({
        "baseline": breakdown,
        "suggestion": suggestion
    })








def fmt(v):
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return "0.00"

def monthly_from_annual(a):
    try:
        return float(a) / 12.0
    except Exception:
        return 0.0

@api_view(["POST"])
def dscr_pdf_table(request):
    data = request.data.copy()
    target = float(data.pop("target_dscr", 2.5))

    
    baseline = compute_dscr_and_breakdown(**data)
    suggestion = find_adjustments_for_target_dscr(data, target_dscr=target)

    
    def safe(k, default=0.0):
        v = data.get(k)
        try:
            return float(v)
        except Exception:
            return default

    days_per_month = safe("days_per_month", 0)
    km_per_day = safe("km_per_day", 0)
    fare_per_km = safe("fare_per_km", 0)
    fuel_cost_per_litre = safe("fuel_cost_per_litre", 0)
    vehicle_kmpl = safe("vehicle_kmpl", 1)

  
    oil_spares_annual = safe("oil_spares_annual", 0)
    taxes_annual = safe("taxes_annual", 0)
    insurance_annual = safe("insurance_annual", 0)
    maintenance_annual = safe("maintenance_annual", 0)
    staff_salary_annual = safe("staff_salary_annual", 0)
    drawings_annual = safe("drawings_annual", 0)
    garage_rent_annual = safe("garage_rent_annual", 0)
    others_annual = safe("others_annual", 0)
    interest_on_loan_annual = safe("interest_on_loan_annual", 0)
    tax_provision_annual = safe("tax_provision_annual", 0)
    repayment_obligation_annual = safe("repayment_obligation_annual", 0)
    depreciation_rate_pct = safe("depreciation_rate_pct", 0)

    
    gross_operating_income = baseline.get("gross_operating_income", 0.0)
    fuel_expense_annual = baseline.get("fuel_expense_annual", 0.0)
    depreciation_annual = baseline.get("depreciation_annual", 0.0)
    total_expenditures_including_depr = baseline.get("total_expenditures_including_depr", 0.0)
    total_expenses_plus_interest_tax = baseline.get("total_expenses_plus_interest_tax", 0.0)
    net_income_annual = baseline.get("net_income_annual", 0.0)
    net_surplus_for_dscr = baseline.get("net_surplus_for_dscr", 0.0)
    dscr = baseline.get("dscr", 0.0)

    
    gross_per_month = gross_operating_income / 12.0
    fuel_per_month = fuel_expense_annual / 12.0
    depreciation_per_month = depreciation_annual / 12.0
    total_expenditures_per_month = total_expenditures_including_depr / 12.0
    total_expenses_plus_interest_tax_per_month = total_expenses_plus_interest_tax / 12.0
    net_income_per_month = net_income_annual / 12.0
    net_surplus_per_month = net_surplus_for_dscr / 12.0
    repayment_per_month = repayment_obligation_annual / 12.0 if repayment_obligation_annual else 0.0


    dscr_monthly = 0.0
    if repayment_per_month > 0:
        dscr_monthly = (net_surplus_for_dscr / 12.0) / repayment_per_month

    
    table_data = [
        ["Sl.No", "Particulars", "Per Month", "Per Year"],
        ["1", "No. of days the vehicle will be on the road", str(int(days_per_month)), str(int(days_per_month * 12))],
        ["2", "No. of kilometers plied per day", str(int(km_per_day)), str(int(km_per_day * days_per_month * 12))],
        ["3", "Fare/Rate per kilometer", fmt(fare_per_km), "-"],
        ["4", "Gross operating Income (1x2x3)", fmt(gross_per_month), fmt(gross_operating_income)],

        ["5", "Fuel (Diesel/petrol) expenses*", fmt(fuel_per_month), fmt(fuel_expense_annual)],
        ["6", "Cost of oil/spares etc", fmt(monthly_from_annual(oil_spares_annual)), fmt(oil_spares_annual)],
        ["7", "Taxes", fmt(monthly_from_annual(taxes_annual)), fmt(taxes_annual)],
        ["8", "Insurance", fmt(monthly_from_annual(insurance_annual)), fmt(insurance_annual)],
        ["9", "Maintenance expenses", fmt(monthly_from_annual(maintenance_annual)), fmt(maintenance_annual)],

        ["10", "Staff salary", fmt(monthly_from_annual(staff_salary_annual)), fmt(staff_salary_annual)],
        ["11", "Drawings of the operators", fmt(monthly_from_annual(drawings_annual)), fmt(drawings_annual)],
        ["12", "Garage rent", fmt(monthly_from_annual(garage_rent_annual)), fmt(garage_rent_annual)],
        ["13", "Others", fmt(monthly_from_annual(others_annual)), fmt(others_annual)],
        ["14", f"Depreciation ({depreciation_rate_pct}%)", fmt(depreciation_per_month), fmt(depreciation_annual)],

        ["15", "Total", fmt(total_expenditures_per_month), fmt(total_expenditures_including_depr)],
        ["16", "Interest on the SRWTO Loan", fmt(monthly_from_annual(interest_on_loan_annual)), fmt(interest_on_loan_annual)],
        ["17", "Tax Provision", fmt(monthly_from_annual(tax_provision_annual)), fmt(tax_provision_annual)],
        ["18", "Total Expenses (15 +16+17)", fmt(total_expenses_plus_interest_tax_per_month), fmt(total_expenses_plus_interest_tax)],

        ["19", "Net Income (4 - 18)", fmt(net_income_per_month), fmt(net_income_annual)],
        ["20", "Net surplus (for DSCR purpose) (19 +14+ 16)", fmt(net_surplus_per_month), fmt(net_surplus_for_dscr)],
        ["21", "Repayment obligation per year(Install+Interest)", fmt(repayment_per_month), fmt(repayment_obligation_annual)],
        ["22", "Debt service Coverage Ratio (DSCR) (20 / 21)", f"{dscr_monthly:.2f}", fmt(dscr if dscr is not None else 0.0)],

    ]

   
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("<b>7. Assessment of Income</b>", styles["Heading2"]))
    story.append(Spacer(1, 8))

    table = Table(table_data, colWidths=[40, 290, 100, 100])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("LEFTPADDING", (1,1), (1,-1), 6),
    ]))

    story.append(table)
    story.append(Spacer(1, 12))


    sugg_text = f"Suggestion (target DSCR: {target}): success={suggestion.get('success')} final_dscr={suggestion.get('final_dscr')}"
    story.append(Paragraph(sugg_text, styles["Normal"]))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="srwto_table_full.pdf"'
    return response
