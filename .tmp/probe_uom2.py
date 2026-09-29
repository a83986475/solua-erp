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

# 1. existing UOMs
names = [u.name for u in frappe.get_all("UOM", fields=["name"], limit_page_length=0)]
out["uom_total"] = len(names)
out["uom_hits"] = [n for n in names if any(k in n.lower() for k in ("箱", "caixa", "box", "carton", "cart"))]

# 2. UOM Conversion Factor schema + rows
ucf_cols = [d[0] for d in frappe.db.sql("desc `tabUOM Conversion Factor`")]
out["ucf_cols"] = ucf_cols
out["ucf_rows"] = frappe.db.sql("select * from `tabUOM Conversion Factor` limit 10", as_dict=True)

# 3. Item Variant Settings (single) and its child tables
ivs = frappe.get_single("Item Variant Settings")
out["ivs_meta"] = [[df.fieldname, df.fieldtype, df.options] for df in ivs.meta.fields]
ivs_data = {}
for df in ivs.meta.fields:
    if df.fieldtype == "Table":
        ivs_data[df.fieldname] = frappe.get_all(df.options, fields=["*"], limit_page_length=30)
    elif df.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Script", "Detach"):
        ivs_data[df.fieldname] = ivs.get(df.fieldname)
out["ivs_data"] = ivs_data

# 4. Item meta: uoms field
item_meta = frappe.get_meta("Item")
uom_df = item_meta.get_field("uoms")
out["item_uoms_field"] = [uom_df.fieldname, uom_df.fieldtype, uom_df.options] if uom_df else None
out["item_uom_child_meta"] = [[df.fieldname, df.fieldtype] for df in frappe.get_meta("Item UOM").fields]

# 5. items and their templates
tpl_set, item_rows = set(), []
for code in ITEMS:
    if not frappe.db.exists("Item", code):
        item_rows.append({"code": code, "exists": False})
        continue
    it = frappe.get_doc("Item", code)
    if it.variant_of:
        tpl_set.add(it.variant_of)
    item_rows.append({
        "code": code,
        "variant_of": it.variant_of,
        "stock_uom": it.stock_uom,
        "uoms": [[r.uom, r.conversion_factor] for r in (it.uoms or [])],
    })
out["items"] = item_rows

tpl_rows = []
for t in sorted(tpl_set):
    it = frappe.get_doc("Item", t)
    tpl_rows.append({
        "code": t,
        "has_variants": it.has_variants,
        "stock_uom": it.stock_uom,
        "uoms": [[r.uom, r.conversion_factor] for r in (it.uoms or [])],
        "variant_count": frappe.db.count("Item", {"variant_of": t}),
    })
out["templates"] = tpl_rows

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
