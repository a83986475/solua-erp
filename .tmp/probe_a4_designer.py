import os, logging, json, re, base64

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

out = {}
MARK = "SOLUA_A4_DESIGNER:v1:"

rows = frappe.get_all("Print Format", filters={"html": ["like", f"%{MARK}%"]},
                      fields=["name", "doc_type", "module", "creation", "modified", "disabled",
                              "standard", "custom_format", "owner"],
                      order_by="modified desc")
out["designer_formats"] = rows

def decode_config(html):
    m = re.search(r"<!--SOLUA_A4_DESIGNER:v1:([A-Za-z0-9_\-=]+)-->", html or "")
    if not m:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(m.group(1).encode()).decode())
    except Exception as exc:
        return {"decode_error": str(exc)[:120]}

for row in rows:
    html = frappe.db.get_value("Print Format", row.name, "html") or ""
    cfg = decode_config(html)
    row["config"] = cfg
    row["html_len"] = len(html)

out["recent_modified_all_formats"] = frappe.get_all(
    "Print Format", filters={"modified": [">", "2026-09-24 00:00:00"]},
    fields=["name", "doc_type", "modified"], order_by="modified desc", limit=20)

out["designer_page_asset"] = {
    "hooks_jinja_a4_provider": "solua_home.printing.a4.get_a4_print_data" in (frappe.get_hooks("jinja") or {}).get("methods", []),
    "api_importable": bool(frappe.get_attr("solua_home.api.a4_designer.get_access")) if True else False,
}

out["renders"] = {}
for row in rows[:3]:
    doctype = row.doc_type
    doc = frappe.get_all(doctype, filters={"docstatus": 1}, fields=["name"], order_by="creation desc", limit=1)
    if not doc:
        out["renders"][row.name] = {"skipped": "no submitted doc"}
        continue
    try:
        html = frappe.get_print(doctype, doc[0].name, print_format=row.name, as_pdf=False)
        out["renders"][row.name] = {
            "ok": True, "doc": doc[0].name, "len": len(html),
            "no_jinja": "{%" not in html,
            "columns": re.findall(r'<th[^>]*>([^<]*)</th>', html)[:20],
            "rows": len(re.findall(r"<tr>", html)),
        }
        if row is rows[0]:
            with open("/tmp/a4_designer_preview.html", "w", encoding="utf-8") as fh:
                fh.write(html)
    except Exception as exc:
        out["renders"][row.name] = {"ok": False, "error": str(exc)[:200]}

out["error_logs_a4"] = frappe.get_all(
    "Error Log", filters={"error": ["like", "%a4_designer%"]},
    fields=["creation", "method"], order_by="creation desc", limit=5)

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
