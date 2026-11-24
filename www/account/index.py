from solua_home.www.employee_account.index import get_context as get_employee_account_context


def get_context(context):
    context.template = "www/employee_account/index.html"
    return get_employee_account_context(context)
