"""Solua profitability report with opening stock receipts excluded from P&L."""

import frappe
from frappe import _, qb
from frappe.query_builder import Criterion
from frappe.utils import cstr, flt

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.report.financial_statements import filter_accounts, filter_out_zero_value_rows
from erpnext.accounts.report.profitability_analysis import profitability_analysis as standard_report
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters
from erpnext.accounts.utils import get_zero_cutoff


def is_opening_stock_receipt_adjustment(account_name, voucher_type, stock_entry_purpose):
	return (
		cstr(account_name).strip().casefold() == "stock adjustment"
		and voucher_type == "Stock Entry"
		and stock_entry_purpose == "Material Receipt"
	)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.get("based_on") == "Accounting Dimension" and not filters.get("accounting_dimension"):
		frappe.throw(_("Select Accounting Dimension."))

	based_on = (
		filters.based_on if filters.based_on != "Accounting Dimension" else filters.accounting_dimension
	)
	validate_filters(filters)
	accounts = standard_report.get_accounts_data(based_on, filters.get("company"))
	data = get_data(accounts, filters, based_on)
	return standard_report.get_columns(filters), data


def get_data(accounts, filters, based_on):
	if not accounts:
		return []

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)
	gl_entries_by_account = {}
	accounting_dimensions = get_dimensions(with_cost_center_and_project=True)[0]
	fieldname = ""
	for dimension in accounting_dimensions:
		if dimension["document_type"] == based_on:
			fieldname = dimension["fieldname"]

	set_gl_entries_by_account(
		filters.get("company"),
		filters.get("from_date"),
		filters.get("to_date"),
		fieldname,
		gl_entries_by_account,
		ignore_closing_entries=not flt(filters.get("with_period_closing_entry")),
	)

	total_row = standard_report.calculate_values(accounts, gl_entries_by_account, filters)
	standard_report.accumulate_values_into_parents(accounts, accounts_by_name)
	data = standard_report.prepare_data(accounts, filters, total_row, parent_children_map, based_on)
	return filter_out_zero_value_rows(
		data, parent_children_map, show_zero_values=filters.get("show_zero_values")
	)


def set_gl_entries_by_account(
	company, from_date, to_date, based_on, gl_entries_by_account, ignore_closing_entries=False
):
	"""Load GL entries while excluding opening stock receipt balancing entries."""
	gl = qb.DocType("GL Entry")
	acc = qb.DocType("Account")
	stock_entry = qb.DocType("Stock Entry")

	conditions = [
		gl.company.eq(company),
		gl[based_on].notnull(),
		gl.is_cancelled.eq(0),
	]
	if from_date and to_date:
		conditions.append(gl.posting_date.between(from_date, to_date))
	elif from_date:
		conditions.append(gl.posting_date.gte(from_date))
	elif to_date:
		conditions.append(gl.posting_date.lte(to_date))
	if ignore_closing_entries:
		conditions.append(gl.voucher_type.ne("Period Closing Voucher"))

	root_subquery = qb.from_(acc).select(acc.root_type).where(acc.name.eq(gl.account))
	gl_entries = (
		qb.from_(gl)
		.inner_join(acc)
		.on(acc.name == gl.account)
		.left_join(stock_entry)
		.on((stock_entry.name == gl.voucher_no) & gl.voucher_type.eq("Stock Entry"))
		.select(
			gl.posting_date,
			gl[based_on].as_("based_on"),
			gl.debit,
			gl.credit,
			gl.is_opening,
			gl.voucher_type,
			acc.account_name,
			stock_entry.purpose.as_("stock_entry_purpose"),
			root_subquery.as_("type"),
		)
		.where(Criterion.all(conditions))
		.orderby(gl[based_on], gl.posting_date)
		.run(as_dict=True)
	)

	for entry in gl_entries:
		if is_opening_stock_receipt_adjustment(
			entry.account_name, entry.voucher_type, entry.stock_entry_purpose
		):
			continue
		gl_entries_by_account.setdefault(entry.based_on, []).append(entry)
