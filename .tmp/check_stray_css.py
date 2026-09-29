"""Verify the stray CSS issue: read get_solua_print_css() output and check logo_css/logo_html placement."""
import os, sys, logging
os.chdir('/home/frappe/frappe-bench/sites')
import frappe, frappe.utils.logger as _flog
_flog.create_handler = lambda *a,**k:[logging.StreamHandler()]
frappe.init(site='erp.solua.one', sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
from solua_home.printing.wholesale import get_solua_print_css
css = get_solua_print_css()
print("CSS len:", len(css))
# Check if logo_css/logo_html are inside <style> or outside
import re
style_close = css.rfind('</style>')
print("Last </style> at pos:", style_close)
logo_css = ".print-format{position:relative}.solua-global-logo{position:absolute;left:0;top:0;width:24mm;height:16mm;object-fit:contain;}"
logo_html = '<img class="solua-global-logo" src="...">'
print("logo_css in css:", logo_css in css)
print("logo_css after </style>:", logo_css in css[style_close+10:] if style_close >= 0 else False)
print("logo_html after </style>:", 'class="solua-global-logo"' in css[style_close+10:] if style_close >= 0 else False)

# Check the current api/a4_designer.py to see if it adds logo_css/logo_html
import re
api_src = open('/home/frappe/frappe-bench/apps/solua_home/solua_home/api/a4_designer.py', encoding='utf-8').read()
print("\n--- api/a4_designer.py: does it add logo_css/logo_html?")
print("has logo_css:", "logo_css" in api_src)
print("has logo_html:", "logo_html" in api_src)
print("has solua-global-logo:", "solua-global-logo" in api_src)
print(".company-logo in api:", ".company-logo" in api_src)
