import os, re, json, logging, hashlib

os.chdir("/home/frappe/frappe-bench/sites")
import frappe
import frappe.utils.logger as _flog
_flog.create_handler = lambda *a, **k: [logging.StreamHandler()]
frappe.init(site="erp.solua.one", sites_path="/home/frappe/frappe-bench/sites")
frappe.connect()
frappe.set_user("Administrator")

REPO = "/home/frappe/frappe-bench/apps/solua_home/solua_home/print_format"


def norm(s):
    return (s or "").replace("\r\n", "\n")


def h(s):
    return hashlib.md5(norm(s).encode()).hexdigest()[:10]


rows = frappe.get_all("Print Format", filters={"module": "Solua Wholesale"},
                      fields=["name", "doc_type", "disabled"], order_by="doc_type, name")

out = {}
for r in rows:
    pf = frappe.get_doc("Print Format", r.name)
    rec = {"doc_type": r.doc_type, "disabled": r.disabled,
           "db": {"html_len": len(pf.html or ""), "css_len": len(pf.css or ""),
                  "html_md5": h(pf.html), "css_md5": h(pf.css)}}
    rec["db_flags"] = {
        "company_header": "company-header" in (pf.html or ""),
        "brand_table": 'class="brand"' in (pf.html or ""),
        "own_page": "@page" in (pf.css or ""),
        "h2_center": bool(re.search(r"h2\s*\{[^}]*text-align\s*:\s*center", pf.css or "")),
        "h2_color_gold": "#99732c" in (pf.css or ""),
        "hide_global_logo": "solua-global-logo" in (pf.css or ""),
    }
    # disk file with the same name?
    disk = None
    if os.path.isdir(REPO):
        for d in os.listdir(REPO):
            f = os.path.join(REPO, d, d + ".json")
            if os.path.isfile(f):
                try:
                    with open(f, encoding="utf-8") as fh:
                        j = json.load(fh)
                except Exception:
                    continue
                if j.get("name") == r.name:
                    disk = {"folder": d, "html_md5": h(j.get("html")), "css_md5": h(j.get("css")),
                            "html_len": len(j.get("html") or ""), "css_len": len(j.get("css") or "")}
    rec["disk"] = disk
    if disk:
        rec["diverged"] = (disk["html_md5"] != rec["db"]["html_md5"]) or (disk["css_md5"] != rec["db"]["css_md5"])
    out[r.name] = rec

print(json.dumps(out, ensure_ascii=True, indent=1, default=str))
frappe.db.rollback()
