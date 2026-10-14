"""Sales Order Item Link query with exact barcode matching."""

from collections import defaultdict

import frappe
from frappe import scrub
from frappe.query_builder import Case, Criterion, DocType
from frappe.query_builder.functions import Concat, Length, Locate, Lower, Substring
from frappe.utils import nowdate
from pypika import Order


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(
    doctype: str,
    txt: str,
    searchfield: str,
    start: int,
    page_len: int,
    filters: dict | str | None = None,
    as_dict: bool = False,
):
    """Keep ERPNext Item search behavior, but require an exact barcode."""
    doctype = "Item"
    filters = frappe.parse_json(filters)

    if filters and isinstance(filters, dict):
        if filters.get("customer") or filters.get("supplier"):
            party_type = "Customer" if filters.get("customer") else "Supplier"
            party = filters.get("customer") or filters.get("supplier")
            group = "Customer Group" if filters.get("customer") else "Supplier Group"
            item_rules = frappe.get_all(
                "Party Specific Item",
                filters={"party_type": party_type},
                fields=["party", "restrict_based_on", "based_on_value"],
            )
            group_rules = frappe.get_all(
                "Party Specific Item",
                filters={"party_type": group},
                fields=["party", "restrict_based_on", "based_on_value"],
            )
            current_group = frappe.get_value(party_type, party, scrub(group))
            restricted = defaultdict(set)
            allowed = defaultdict(set)
            for rule in item_rules:
                field = "name" if rule.restrict_based_on == "Item" else rule.restrict_based_on
                (allowed if rule.party == party else restricted)[field].add(rule.based_on_value)
            for rule in group_rules:
                field = "name" if rule.restrict_based_on == "Item" else rule.restrict_based_on
                (allowed if current_group == rule.party else restricted)[field].add(rule.based_on_value)
            for field, values in restricted.items():
                excluded = values - allowed[field]
                if excluded:
                    filters[scrub(field)] = ["not in", list(excluded)]
            filters.pop("customer", None)
            filters.pop("supplier", None)
        else:
            filters.pop("customer", None)
            filters.pop("supplier", None)

    item = DocType(doctype)
    eol = item.end_of_life
    date_conditions = [eol > nowdate(), eol.isnull()]
    if frappe.db.db_type not in ["postgres"]:
        date_conditions.append(eol == "0000-00-00")
    date_condition = Criterion.any(date_conditions)

    meta = frappe.get_meta("Item", cached=True)
    meta_searchfields = meta.get_search_fields()
    searchfields = [field for field in meta_searchfields if field not in {"description", "item_group"}]
    query_select = [item[field] for field in meta_searchfields if field not in ["name", "description", "item_group"]]
    if "description" in meta_searchfields:
        query_select.append(
            Case()
            .when(Length(item.description) > 40, Concat(Substring(item.description, 1, 40), "..."))
            .else_(item.description)
            .as_("description")
        )

    fields_to_process = list(
        dict.fromkeys(
            searchfields
            + [field for field in [searchfield or "name", "item_code", "item_name"] if field not in searchfields]
        )
    )
    db_fields = [field.fieldname for field in meta.fields] + ["name"]
    search_str = f"%{txt}%"
    search_conditions = [item[field].like(search_str) for field in fields_to_process if field in db_fields]

    barcode_tbl = DocType("Item Barcode")
    exact_barcode = frappe.qb.from_(barcode_tbl).select(barcode_tbl.parent).where(barcode_tbl.barcode == txt)
    search_conditions.append(item.item_code.isin(exact_barcode))

    txt_no_percent = txt.replace("%", "")
    query = (
        frappe.get_query(doctype, filters=filters, ignore_permissions=False)
        .select(*query_select)
        .where(item.docstatus < 2)
        .where(item.disabled == 0)
        .where(item.has_variants == 0)
        .where(date_condition)
        .where(Criterion.any(search_conditions))
        .orderby(Case().when(Locate(Lower(txt_no_percent), Lower(item.name)) > 0, Locate(Lower(txt_no_percent), Lower(item.name))).else_(99999))
        .orderby(Case().when(Locate(Lower(txt_no_percent), Lower(item.item_name)) > 0, Locate(Lower(txt_no_percent), Lower(item.item_name))).else_(99999))
        .orderby(item.idx, order=Order.desc)
        .orderby(item.name)
        .orderby(item.item_name)
        .limit(page_len)
        .offset(start)
    )
    return query.run(as_dict=as_dict)
