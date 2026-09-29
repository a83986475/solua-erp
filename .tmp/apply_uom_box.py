import os, logging, json

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

UOM = "箱/Caixa"
FACTOR_BY_TEMPLATE = {
    "SH151138-2MS": 12,
    "SH151145-2MD": 6,
    "SH151152-3MS": 12,
    "SH151169-3MD": 6,
}
out = {"steps": []}

# 1. create UOM
if not frappe.db.exists("UOM", UOM):
    frappe.get_doc(
        {"doctype": "UOM", "uom_name": UOM, "symbol": "Cx", "enabled": 1}
    ).insert(ignore_permissions=True)
    out["steps"].append("UOM created: " + UOM)
else:
    out["steps"].append("UOM already exists: " + UOM)

# 2. set conversion row on each template and save (save triggers update_variants,
#    which copies the uoms table to all variants - "uoms" is in Variant Field allowlist)
for code, factor in FACTOR_BY_TEMPLATE.items():
    doc = frappe.get_doc("Item", code)
    row = next((r for r in (doc.uoms or []) if r.uom == UOM), None)
    if row:
        row.conversion_factor = factor
        action = "updated"
    else:
        doc.append("uoms", {"uom": UOM, "conversion_factor": factor})
        action = "added"
    doc.save(ignore_permissions=True)
    out["steps"].append(f"{code}: {action} {UOM} -> {factor} (saved, variants synced)")

frappe.db.commit()

# 3. readback
tpls = {}
for code in FACTOR_BY_TEMPLATE:
    it = frappe.get_doc("Item", code)
    tpls[code] = [[r.uom, r.conversion_factor] for r in (it.uoms or [])]
out["templates_uoms"] = tpls

variants = frappe.get_all(
    "Item",
    filters={"variant_of": ("in", list(FACTOR_BY_TEMPLATE))},
    fields=["name", "variant_of"],
    order_by="name",
)
vread = []
for v in variants:
    rows = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": v.name, "parenttype": "Item", "uom": UOM},
        fields=["conversion_factor"],
    )
    vread.append([v.name, v.variant_of, rows[0].conversion_factor if rows else None])
out["variants_uoms"] = vread

# 4. functional check: the actual lookup used by transactions
from erpnext.stock.get_item_details import get_conversion_factor
out["lookup_checks"] = {
    "SH151138-2MS-1": get_conversion_factor("SH151138-2MS-1", UOM)["conversion_factor"],
    "SH151145-2MD-3": get_conversion_factor("SH151145-2MD-3", UOM)["conversion_factor"],
    "SH151152-3MS-5": get_conversion_factor("SH151152-3MS-5", UOM)["conversion_factor"],
    "SH151169-3MD-2": get_conversion_factor("SH151169-3MD-2", UOM)["conversion_factor"],
}
out["ucd_total_box"] = frappe.db.count("UOM Conversion Detail", {"uom": UOM})

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
