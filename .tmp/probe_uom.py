import os, logging, json

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

ITEMS = [
    "SH151138-2MS-1", "SH151138-2MS-2", "SH151138-2MS-3", "SH151138-2MS-4", "SH151138-2MS-5",
    "SH151145-2MD-1", "SH151145-2MD-2", "SH151145-2MD-3", "SH151145-2MD-4", "SH151145-2MD-5",
    "SH151152-3MS-1", "SH151152-3MS-2", "SH151152-3MS-3", "SH151152-3MS-4", "SH151152-3MS-5",
    "SH151169-3MD-1", "SH151169-3MD-2", "SH151169-3MD-3", "SH151169-3MD-4", "SH151169-3MD-5",
]

out = {}

# 1. UOMs matching 箱/Caixa/Box
uoms = frappe.get_all("UOM", fields=["name"], limit_page_length=0)
names = [u["name"] for u in uoms]
out["uom_count"] = len(names)
out["uom_matches"] = [n for n in names if any(k in n.lower() for k in ("箱", "caixa", "box", "cart"))]
out["uom_sample"] = names[:40]

# 2. UOM Conversion Factor doctype fields
out["ucf_meta"] = [df.fieldname for df in frappe.get_meta("UOM Conversion Factor").fields]
out["ucf_all"] = frappe.get_all("UOM Conversion Factor",
    fields=["name", "from_uom", "to_uom", "conversion_factor"], limit_page_length=0)

# 3. Items state
item_rows = []
for code in ITEMS:
    exists = frappe.db.exists("Item", code)
    row = {"code": code, "exists": bool(exists)}
    if exists:
        it = frappe.get_doc("Item", code)
        row["stock_uom"] = it.stock_uom
        row["is_stock_item"] = it.is_stock_item
        row["uoms"] = [{"uom": r.uom, "conversion_factor": r.conversion_factor} for r in (it.uoms or [])]
        row["sales_uoms"] = {"selling": it.selling_uom, "purchase": it.purchase_uom}
    item_rows.append(row)
out["items"] = item_rows

# 4. Item UOM child doctype meta
out["item_uom_meta"] = [df.fieldname for df in frappe.get_meta("Item UOM").fields]

print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
frappe.db.rollback()
