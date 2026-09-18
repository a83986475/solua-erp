// ============================================================================
// solua_home / public/js/print_designer_zh.js
// Print Designer 界面汉化（运行时文本覆写）
//
// 背景：print_designer 的 UI 字符串大部分是硬编码英文（编译时固化为 label），
//       frappe 翻译文件（zh.csv）无法覆盖。此脚本在页面加载后用
//       MutationObserver 监听 DOM 变化，把已知英文文本替换为中文。
//
// 优点：不改 print_designer 源码、官方升级不冲突、无需重新 build。
// 局限：只能替换"纯文本"节点；若未来官方改用 __() 国际化，此脚本可移除。
//
// 注册方式（hooks.py）：
//   page_js = {
//       "point-of-sale": "public/js/pos_custom.js",
//       "print-designer": "public/js/print_designer_zh.js",
//   }
// ============================================================================

frappe.provide("solua_home.print_designer_zh");

(function () {
	"use strict";

	// 翻译映射（英文原文 -> 中文）
	// 来源：print_designer.bundle 中的 label 硬编码字符串 + __() 运行时字符串
	const ZH = {
		// ---- 页面/对话框 ----
		"Create or Edit Print Format": "创建或编辑打印格式",
		"Select Document Type": "选择单据类型",
		"Select Print Format": "选择打印格式",
		"Print Format Name": "打印格式名称",
		"Create New": "新建",
		"Edit Existing": "编辑现有",
		"Action": "操作",
		"Create": "创建",
		"Edit": "编辑",
		"Save": "保存",
		"Delete": "删除",
		"Cancel": "取消",
		"Refresh": "刷新",
		"Print": "打印",
		"PDF": "PDF",
		"Language": "语言",
		"Name": "名称",

		// ---- 工具栏元素 ----
		"Mouse Pointer (M)": "鼠标指针 (M)",
		"Rectangle (R)": "矩形 (R)",
		"Barcode (B)": "条码 (B)",
		"Image (I)": "图片 (I)",
		"Components (C)": "组件 (C)",
		"Table (A)": "表格 (A)",
		"Dynamic Text": "动态文本",
		"Static Text": "静态文本",
		"Label Element": "标签元素",
		"Main Element": "主体元素",
		"Column": "列",
		"Row": "行",
		"Rows": "行数",
		"Full Page": "整页",
		"Form": "表单",
		"Current Table": "当前表格",
		"Primary Table": "主表格",
		"Table Header": "表头",
		"All Rows": "所有行",
		"Alternate Rows": "交替行",
		"Field Labels": "字段标签",
		"Apply Style to Header": "将样式应用于表头",
		"Delete Page": "删除页面",
		"Current Page": "当前页",
		"Total Pages": "总页数",
		"Print Date": "打印日期",
		"Print Time": "打印时间",
		"First": "首页",
		"Last": "末页",
		"Odd": "奇数页",
		"Even": "偶数页",
		"Set as Default": "设为默认",
		"Try the new Print Designer": "试试新的打印设计器",
		"Edit Format": "编辑格式",
		"Loading Print Format": "正在加载打印格式",
		"Search Doctypes": "搜索单据类型",
		"Search Field by label, fieldname or fieldtype": "按标签、字段名或字段类型搜索",
		"Enter Label": "输入标签",
		"Please select DocType first": "请先选择单据类型",
		"Print Format not saved": "打印格式未保存",

		// ---- 属性面板 ----
		"Page Size": "页面尺寸",
		"Page UOM": "页面单位",
		"Height": "高度",
		"Weight": "粗细",
		"Width": "宽度",
		"Auto": "自动",
		"Auto ( min-height)": "自动（最小高度）",
		"Fixed": "固定",
		"Inline": "行内",
		"Z Index": "层级",
		"Font": "字体",
		"Thin": "细",
		"Extra Light": "特细",
		"Light": "细体",
		"Regular": "常规",
		"Medium": "中等",
		"Semi Bold": "半粗",
		"Bold": "粗体",
		"Extra Bold": "特粗",
		"Black": "特黑",
		"Border Color": "边框颜色",
		"Image Fit": "图片适配",
		"Contain (fit within bounds)": "包含（完整显示）",
		"Cover (fill entire area)": "覆盖（填满区域）",
		"Avoid Page Break": "避免分页",
		"Render Jinja": "渲染 Jinja",
		"Yes": "是",
		"Barcode Format": "条码格式",

		// ---- 单位 ----
		"Pixels (px)": "像素 (px)",
		"Milimeter (mm)": "毫米 (mm)",
		"Centimeter (cm)": "厘米 (cm)",
		"Inch (in)": "英寸 (in)",

		// ---- 条码格式 ----
		"QR Code": "二维码",
		"EAN": "EAN",
		"GTIN": "GTIN",
		"UPCA": "UPC-A",
		"ISBN": "ISBN",
		"ISSN": "ISSN",
		"ITF": "ITF",
		"JAN": "JAN",
		"PZN": "PZN",

		// ---- 动态文本弹窗：字段分组标题（fieldtype 名，裸渲染）----
		"Document": "文档",
		"Data": "文本",
		"Small Text": "小文本",
		"Text": "多行文本",
		"Text Editor": "富文本",
		"Markdown Editor": "Markdown",
		"Link": "链接",
		"Dynamic Link": "动态链接",
		"Table": "子表格",
		"Table MultiSelect": "多选子表",
		"Check": "勾选",
		"Select": "下拉选择",
		"Currency": "货币",
		"Float": "小数",
		"Int": "整数",
		"Percent": "百分比",
		"Code": "代码",
		"Date": "日期",
		"Datetime": "日期时间",
		"Time": "时间",
		"Barcode": "条码",
		"Attach Image": "附件图片",
		"Attach": "附件",
		"Button": "按钮",
		"Read Only": "只读",
		"Password": "密码",
		"Color": "颜色",
		"Rating": "评分",
		"Duration": "时长",
		"Geolocation": "定位",
		"Signature": "签名",
		"JSON": "JSON",
		"Dynamic Text": "动态文本",
		"Hidden Fields": "显示隐藏字段",

		// ---- 提示/状态 ----
		"Please enable pop-ups": "请启用弹窗",
		"Please resolve overlapping elements ": "请解决元素重叠问题",
		"Atleast 1 element is required inside body": "正文中至少需要 1 个元素",
		"Are you sure you want to delete the page?": "确定要删除这个页面吗？",
		"Do you want to save copy of it ?": "是否保存一份副本？",
		"Error Generating PDF...": "生成 PDF 出错...",
		"in header": "在页眉",
		"in footer": "在页脚",
		"in table, auto layout failed": "在表格中，自动布局失败",
		"Letter Head": "信纸抬头",
		"Loading...": "加载中...",
	};

	// ============================================================
	// 系统 zh 翻译字典（兜底翻译：覆盖字段标签等海量字符串）
	// ============================================================
	// 设计器字段列表裸渲染 {{ field.label }}（不走 __()），且会话语言可能是 en。
	// 这里从服务端拉取合并后的 zh 翻译字典（solua_home.api.common.get_zh_translations，
	// 服务端缓存 24h），用 sessionStorage 缓存避免每次访问都下载 685KB。
	const ZH_DICT_CACHE_KEY = "solua_home_zh_translations_v1";
	let zhDict = null;
	let zhDictReady = false;

	const loadZhDict = () => {
		try {
			const cached = sessionStorage.getItem(ZH_DICT_CACHE_KEY);
			if (cached) {
				zhDict = JSON.parse(cached);
				zhDictReady = true;
				return;
			}
		} catch (e) {
			/* ignore */
		}
		frappe.call({
			method: "solua_home.api.common.get_zh_translations",
			callback: (r) => {
				if (r && r.message) {
					zhDict = r.message;
					zhDictReady = true;
					try {
						sessionStorage.setItem(ZH_DICT_CACHE_KEY, JSON.stringify(zhDict));
					} catch (e) {
						/* ignore */
					}
					// 字典就绪后，把当前已渲染的文本再刷一遍（含打开着的弹窗）
					if (applied) applyToTree(document.body);
				}
			},
		});
	};

	// 只处理有实际翻译的文本：ZH 映射优先，其次系统 zh 字典兜底
	const translateText = (text) => {
		const trimmed = text.trim();
		if (ZH[trimmed]) return ZH[trimmed];
		if (zhDictReady && zhDict && zhDict[trimmed] && zhDict[trimmed] !== trimmed) {
			return zhDict[trimmed];
		}
		return null;
	};

	// 替换文本节点的内容（保留原节点的换行结构）
	const replaceInNode = (node) => {
		if (node.nodeType !== Node.TEXT_NODE) return;
		const parent = node.parentNode;
		if (!parent) return;
		// 跳过脚本/样式
		const tag = parent.tagName;
		if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA" || tag === "INPUT") return;

		const translated = translateText(node.nodeValue);
		if (translated) {
			node.nodeValue = node.nodeValue.replace(node.nodeValue.trim(), translated);
		}
	};

	let observer = null;
	let applyTimer = null;
	let pendingMutations = [];
	let applied = false;

	const applyToTree = (root) => {
		if (!root) return;
		// 处理根节点本身
		replaceInNode(root);
		// 遍历所有文本节点
		const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
		let n;
		while ((n = walker.nextNode())) {
			replaceInNode(n);
		}
	};

	// ============================================================
	// 顶栏注入「新建/编辑格式」按钮
	// ============================================================
	// 设计器顶栏（AppHeader）默认只有 Exit（回上一页），不能直接新建/编辑别的格式。
	// 这里在 Exit 按钮旁注入一个按钮：点击后回到基础路由 /app/print-designer，
	// 触发 on_page_show -> load_print_designer -> 自动弹出「创建或编辑打印格式」对话框。
	// 不动 print_designer 源码；按钮只注入一次（幂等）。
	const injectFormatButton = () => {
		const exitBtn = document.querySelector(".header .exit-btn");
		if (!exitBtn) return false; // 顶栏尚未渲染（未打开格式时）

		// 把 Exit 的默认行为（回上一页）改成回到打印格式列表/对话框。
		// 原理：AppHeader.vue 的 .exit-btn 由 Vue 绑定了 click -> goToLastPage()。
		// 这里追加的监听用 stopImmediatePropagation() 抢在 Vue handler 之前拦截，
		// 改为 frappe.set_route("print-designer") —— 回到基础路由自动弹对话框。
		// 幂等标记挂在按钮 DOM 上；若 Vue 重新渲染出新的 Exit 按钮（未带标记），
		// 观察器再次触发时会重新绑定，保证切换格式后行为不丢。
		if (!exitBtn.dataset.soluaExitBound) {
			exitBtn.addEventListener("click", (e) => {
				e.stopImmediatePropagation();
				e.preventDefault();
				frappe.set_route("print-designer");
			});
			exitBtn.dataset.soluaExitBound = "1";
		}

		if (document.querySelector(".header .solua-format-btn")) return true;
		const btn = document.createElement("button");
		btn.className = "btn btn-sm btn-default solua-format-btn";
		btn.type = "button";
		btn.style.marginRight = "8px";
		btn.textContent = "新建/编辑格式";
		btn.title = "新建或编辑其他打印格式";
		btn.addEventListener("click", () => {
			frappe.set_route("print-designer");
		});
		exitBtn.before(btn);
		return true;
	};

	const start = () => {
		if (applied) return;

		// 确认页面存在（print-designer 路由）；未就绪则不置 applied，稍后重试
		if (!frappe.pages["print-designer"] || !frappe.router || frappe.router.current_route[0] !== "print-designer") {
			return;
		}
		applied = true;

		// 初次应用
		applyToTree(document.body);
		injectFormatButton();

		// 监听后续 Vue 渲染产生的节点。注意：mutations 必须累积处理，
		// 否则节流期间新到的批次会被整体丢弃（弹窗字段列表渲染时丢批严重）
		observer = new MutationObserver((mutations) => {
			pendingMutations.push(...mutations);
			if (applyTimer) return;
			applyTimer = setTimeout(() => {
				applyTimer = null;
				const batch = pendingMutations;
				pendingMutations = [];
				for (const m of batch) {
					if (m.type === "characterData") {
						replaceInNode(m.target);
					}
					for (const added of m.addedNodes) {
						if (added.nodeType === Node.ELEMENT_NODE) {
							applyToTree(added);
						} else if (added.nodeType === Node.TEXT_NODE) {
							replaceInNode(added);
						}
					}
				}
				// 顶栏渲染后注入「新建/编辑格式」按钮（幂等）
				injectFormatButton();
			}, 80);
		});

		observer.observe(document.body, {
			childList: true,
			subtree: true,
			characterData: true,
		});
	};

	// ============================================================
	// 方案 A：过滤 DocType 下拉，只显示常用单据
	// ============================================================
	// print_designer 的新建对话框里「选择单据类型」是 Link 控件
	// （options: DocType, filters: {istable: 0}），会列出全部 459 个 DocType。
	//
	// 机制（frappe link.js）：每次搜索走 get_search_args() -> set_custom_query(args)，
	//   - df.get_query 为对象时合并其 filters（line 762-835）
	//   - df.filters 存在时直接合并进 args.filters（line 840-843）
	// print_designer 的对话框传的是 df.filters，所以在这里合并 name 白名单。
	// 只影响本页面（脚本经 page_js 只在 print-designer 加载）的 DocType 链接，
	// 其他页面的 DocType 下拉不受影响。
	const ALLOWED_DOCTYPES = [
		"Item", "Item Group", "Item Attribute", "Item Price",
		"Customer", "Customer Group", "Supplier", "Supplier Group",
		"Sales Invoice", "Sales Order", "Quotation", "Delivery Note",
		"Purchase Invoice", "Purchase Order", "Purchase Receipt", "Supplier Quotation",
		"Payment Entry", "Journal Entry", "Sales Partner", "Price List",
		"POS Profile", "POS Opening Entry", "POS Closing Entry",
		"Stock Entry", "Stock Reconciliation", "Warehouse",
		"Employee", "User", "Address", "Contact", "Project", "Task", "Company",
	];

	const applyDoctypeFilter = () => {
		if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.LinkControl) return false;
		const orig = frappe.ui.form.LinkControl.prototype.set_custom_query;
		if (!orig || orig.__solua_filtered) return true;

		frappe.ui.form.LinkControl.prototype.set_custom_query = function (args) {
			const isDocTypePicker = this.df && this.df.options === "DocType";
			if (isDocTypePicker) {
				// 路径 1（print_designer 实际用的）：df.filters 直接合并（line 840）
				if (this.df.filters && !this.df.filters.name) {
					// 浅拷贝后再加白名单，避免污染 Dialog 的原始 df 定义
					this.df.filters = { ...this.df.filters, name: ["in", ALLOWED_DOCTYPES] };
				}
				// 路径 2（兜底）：df.get_query / this.get_query 传 filters 的情况
				const gq = this.get_query || this.df.get_query;
				if (gq && $.isPlainObject(gq) && gq.filters && !gq.filters.name && !gq.__solua_patched) {
					gq.filters = { ...gq.filters, name: ["in", ALLOWED_DOCTYPES] };
					gq.__solua_patched = true; // 标记在 gq 外层，不会随 filters 发到服务器
				}
			}
			return orig.apply(this, arguments);
		};
		frappe.ui.form.LinkControl.prototype.set_custom_query.__solua_filtered = true;
		return true;
	};

	// LinkControl 可能在脚本加载时尚未就绪，轮询等它加载（最多 10 秒）
	// 注：「有内容时点击弹下拉」已迁移到全站脚本 solua_home_global.js（app_include_js）
	const ensureDoctypeFilter = () => {
		if (applyDoctypeFilter()) return;
		let tries = 0;
		const iv = setInterval(() => {
			tries++;
			if (applyDoctypeFilter() || tries > 20) clearInterval(iv);
		}, 500);
	};
	ensureDoctypeFilter();

	// ============================================================
	// 条码预览修复：模板值先渲染再生成
	// ============================================================
	// 现象：设计器里条码元素的值是 Jinja 模板（如 {{ doc.custom_label_barcode }}），
	// 弹窗/画布预览直接把模板原样发给 get_barcode → 服务端报
	// "Invalid barcode value {{ ... }} for format ean13"。
	//
	// 原因：BaseBarcode.vue / AppBarcodePreviewModal.vue 只在 parseJinja=true 时
	// 先调 render_user_text_withdoc 渲染，动态字段默认 parseJinja=false → 原值直发。
	//
	// 修复：拦截 frappe.call，
	//   1) 捕获 render_user_text_withdoc 的入参（doctype/docname/send_to_jinja）到 window，
	//      作为后续渲染模板的上下文；
	//   2) 若 get_barcode 收到的 barcode_value 含 "{{" 模板语法，先调用
	//      render_user_text_withdoc 渲染成真实值，再调用原 get_barcode。
	// 不改 print_designer 源码；幂等；只在设计器页面生效（page_js 加载）。
	const installBarcodeFixes = () => {
		if (!frappe.call || frappe.call.__soluaAllPatched) return;
		const outer = frappe.call;
		frappe.call = function (method, args, opts) {
			// 兼容两种调用方式：frappe.call("method", args, opts) / frappe.call({method, args, ...})
			let m, a;
			if (typeof method === "string") {
				m = method;
				a = args || {};
			} else {
				m = method && method.method;
				a = (method && method.args) || {};
			}
			// 1) 上下文捕获：记住最近一次渲染用到的 doctype/docname/jinja
			if (m && m.indexOf("render_user_text_withdoc") !== -1) {
				if (a.doctype) window.print_designer_doctype = a.doctype;
				if (a.docname) window.print_designer_docname = a.docname;
				if (a.send_to_jinja) window.print_designer_jinja = a.send_to_jinja;
			}
			// 2) 条码模板值先渲染
			if (
				m &&
				m.indexOf("get_barcode") !== -1 &&
				a &&
				typeof a.barcode_value === "string" &&
				a.barcode_value.indexOf("{{") !== -1
			) {
				const raw = a.barcode_value;
				const doctype = window.print_designer_doctype || "Item";
				// 保证有可用的渲染文档：优先用已捕获的 currentDoc，否则取该单据类型最新文档
				let renderPromise = Promise.resolve(
					window.print_designer_docname || ""
				);
				if (!window.print_designer_docname) {
					renderPromise = frappe.db
						.get_list(doctype, {
							fields: ["name"],
							order_by: "modified desc",
							limit_page_length: 1,
						})
						.then((rows) => (rows && rows[0] && rows[0].name) || "");
				}
				return renderPromise
					.then((docname) =>
						frappe.call({
							method:
								"print_designer.print_designer.page.print_designer.print_designer.render_user_text_withdoc",
							args: {
								string: raw,
								doctype: doctype,
								docname: docname || "",
								send_to_jinja: window.print_designer_jinja || {},
							},
						})
					)
					.then((r) => {
						const msg = r && r.message;
						if (msg && msg.success && msg.message && msg.message !== raw) {
							a = { ...a, barcode_value: msg.message };
						}
						if (typeof method === "string") {
							return outer.call(this, m, a, opts);
						}
						return outer.call(this, { ...method, args: a });
					})
					.catch(() => {
						// 渲染失败时退回原值（避免连环弹错）
						if (typeof method === "string") {
							return outer.call(this, m, a, opts);
						}
						return outer.call(this, method);
					});
			}
			return outer.apply(this, arguments);
		};
		frappe.call.__soluaAllPatched = true;
	};
	installBarcodeFixes();

	// print-designer 页面加载后启动：轮询等路由/DOM 就绪（最多 20 秒），
	// 不再依赖 on_page_load 包装（page 对象注册时机不可靠，之前经常接不上）
	let kickTries = 0;
	const kick = () => {
		if (applied) return;
		start();
		if (!applied && kickTries++ < 40) setTimeout(kick, 500);
	};
	kick();

	// 拉取系统 zh 翻译字典（幂等，页面加载即触发一次）
	loadZhDict();
})();
