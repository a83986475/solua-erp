# solua_home/override/desk_page.py
# =========================================
# 强制 Page 文档不缓存进浏览器 localStorage
#
# 背景：Frappe 的 pageview.js（frappe/views/pageview.js）在生产模式下会把
# Page 文档（含 page_js 自定义脚本，如 pos_custom.js）整个缓存到
# localStorage["_page:<name>"]。之后每次打开该页面都直接用缓存、
# 不再请求服务器 —— 导致我们修改 pos_custom.js 后收银员永远看到旧代码
# （硬刷新 Ctrl+Shift+R 也清不掉 localStorage）。
#
# 方案：通过 override_whitelisted_methods 包装 frappe.desk.desk_page.getpage，
# 给返回文档打上 _dynamic_page=1 标记 —— pageview.js 见到该标记就跳过
# localStorage 缓存，每次打开页面都从服务器拉取最新文档。
# 影响：每个页面打开多一次小请求（Page 文档很小），换来自定义脚本更新
# 即时生效，对本项目（少量用户的门店系统）完全可接受。
# =========================================

import frappe
from frappe.desk import desk_page


@frappe.whitelist(allow_guest=True)
def getpage(name: str):
	"""包装 frappe.desk.desk_page.getpage：强制不缓存 Page 文档。

	必须带 @frappe.whitelist()：override 解析后 handler 会对**替换后**的
	函数做 is_whitelisted 校验（whitelisted 集合在模块 import 时由装饰器
	登记），不带装饰器会报「方法未申明 @frappe.whitelist()」403。
	"""
	doc = desk_page.get(name)
	doc._dynamic_page = 1
	frappe.response.docs.append(doc)
