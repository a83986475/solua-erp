from solua_home.solua_wholesale.report.solua_business_totals.solua_business_totals import execute as business_report


def execute(filters=None):
    filters = filters or {}
    return business_report({"company": filters.get("company"), "metric": "delivered", "period": "custom", "from_date": filters.get("from_date"), "to_date": filters.get("to_date")})
