import os, logging, json

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}
out["allow_uom_from_item"] = frappe.get_cached_value(
    "Stock Settings", None, "allow_uom_with_conversion_rate_defined_in_item")
out["box_uom_enabled"] = frappe.get_cached_value("UOM", "\u7bb1/Caixa", "enabled")
out["box_whole_number"] = frappe.get_cached_value("UOM", "\u7bb1/Caixa", "must_be_whole_number")

rows = frappe.get_all("Pick List", fields=["name", "docstatus", "pick_manually", "status"],
                      order_by="creation desc", limit=5)
out["pick_lists"] = rows
out["pick_manually_counts"] = frappe.db.sql(
    "select pick_manually, docstatus, count(*) from `tabPick List` group by 1,2", as_list=True)

target = next((r for r in rows if r.docstatus == 0), rows[0] if rows else None)
out["probe_target"] = target and target.name
if target:
    doc = frappe.get_doc("Pick List", target.name)
    before = [{"item": r.item_code, "uom": r.uom, "qty": r.qty, "sf": r.conversion_factor,
               "stock_qty": r.stock_qty} for r in doc.locations[:3]]
    out["before"] = before
    # 只改内存：把第一行单位换成「箱/Caixa」，看 ERPNext 自己会不会重算
    doc.locations[0].uom = "\u7bb1/Caixa"
    try:
        doc.run_method("set_item_locations") if not doc.pick_manually else None
        out["set_item_locations_ran"] = not bool(doc.pick_manually)
    except Exception as exc:
        out["set_item_locations_ran"] = "error: " + str(exc)[:120]
    out["after_set_item_locations"] = [{"item": r.item_code, "uom": r.uom, "qty": r.qty,
                                        "sf": r.conversion_factor, "stock_qty": r.stock_qty}
                                       for r in doc.locations[:3]]
    from erpnext.stock.doctype.pick_list.pick_list import get_item_details
    out["manual_uom_details"] = {
        k: v for k, v in get_item_details(doc.locations[0].item_code, "\u7bb1/Caixa",
                                          doc.locations[0].warehouse, doc.company).items()
        if k in ("uom", "conversion_factor", "stock_qty", "qty")}
    out["box_factors"] = {
        code: frappe.db.get_value("UOM Conversion Detail", {"parent": code, "uom": "\u7bb1/Caixa"},
                                  "conversion_factor")
        for code in ("SH151138-2MS-1", "SH151145-2MD-3", "SH151152-3MS-5", "SH151169-3MD-2")}

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
