// ============================================================================
// solua_home / public/js/pos_custom.js
// POS 扫码颜色选择器
//
// 功能：扫码模板商品条码（如 CR-001，条码挂在模板上）→ 弹窗列出所有颜色
//       Variant → 点击颜色后直接把对应 Variant 加入 POS 购物车。
//       普通商品 / 已含颜色的 Variant 条码 → 保持 ERPNext 标准扫码行为。
//
// 注册方式（hooks.py）：
//   page_js = {
//       "point-of-sale": "public/js/pos_custom.js",
//   }
// ============================================================================

frappe.provide("solua_home.pos");

(function () {
	"use strict";

	let applied = false;
	let styles_injected = false;
	let active_dialog = null;

	// ------------------------------------------------------------------
	// 颜色选择弹窗
	// ------------------------------------------------------------------
	function show_color_picker(data) {
		inject_styles();

		const colors = data.colors || [];
		if (!colors.length) {
			frappe.show_alert({
				message: __("该商品暂无可售的颜色规格"),
				indicator: "orange",
			});
			frappe.utils.play_sound("error");
			return;
		}

		// 若已有弹窗未关闭，先关闭避免堆叠
		if (active_dialog) active_dialog.hide();

		const dialog = new frappe.ui.Dialog({
			title: __("选择颜色"),
			static: true,
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "color_picker_html",
					options: build_color_picker_html(data),
				},
			],
			primary_action_label: __("取消"),
			primary_action() {
				dialog.hide();
			},
		});
		active_dialog = dialog;
		dialog.onhide = () => {
			if (active_dialog === dialog) active_dialog = null;
		};

		dialog.show();

		// 点击色块 → 把对应 Variant 加入购物车
		dialog.$wrapper.find(".color-picker-item").on("click", function () {
			const variant_code = $(this).attr("data-variant-code");
			if (!variant_code) return;
			dialog.hide();
			add_variant_to_cart(variant_code);
		});
	}

	function build_color_picker_html(data) {
		const template_name = frappe.utils.escape_html(data.template_name || "");
		let items_html = "";

		(data.colors || []).forEach((c) => {
			const name = frappe.utils.escape_html(c.cor || c.variant_name || c.variant_code || "");
			const image = c.swatch || c.image || "";
			const swatch_html = image
				? `<img class="color-swatch-img" src="${frappe.utils.escape_html(image)}" alt="${name}">`
				: `<div class="color-swatch-abbr">${frappe.utils.escape_html(frappe.get_abbr(name))}</div>`;

			items_html += `
				<div class="color-picker-item"
					data-variant-code="${frappe.utils.escape_html(c.variant_code)}"
					title="${name}">
					<div class="color-swatch">${swatch_html}</div>
					<div class="color-name">${name}</div>
				</div>`;
		});

		return `
			<div class="color-picker-dialog">
				<div class="color-picker-template">${template_name}</div>
				<div class="color-picker-subtitle">${__("请选择颜色后加入购物车")}</div>
				<div class="color-picker-grid">${items_html}</div>
			</div>`;
	}

	// ------------------------------------------------------------------
	// 把 Variant 加入购物车
	// 复用标准 POS「搜索 → 渲染 → 点击 .item-wrapper」流程，
	// 这样价格 / UOM / 税率等都会由 ERPNext 标准逻辑自动带出。
	// ------------------------------------------------------------------
	function add_variant_to_cart(variant_code) {
		const item_selector = window.cur_pos && window.cur_pos.item_selector;
		if (!item_selector || !item_selector.set_search_value) {
			frappe.show_alert({
				message: __("POS 组件尚未就绪，请重试"),
				indicator: "orange",
			});
			return;
		}

		item_selector.set_search_value(variant_code);

		let attempts = 0;
		const timer = setInterval(() => {
			attempts++;

			const $exact = item_selector.$items_container.find(".item-wrapper").filter(function () {
				return $(this).attr("data-item-code") === variant_code;
			});

			if ($exact.length) {
				clearInterval(timer);
				$exact.trigger("click");
				item_selector.set_search_value("");
				frappe.utils.play_sound("submit");
			} else if (attempts > 20) {
				clearInterval(timer);
				item_selector.set_search_value("");
				frappe.show_alert({
					message: __("未找到商品 {0}，请检查价格表设置", [variant_code]),
					indicator: "orange",
				});
				frappe.utils.play_sound("error");
			}
		}, 300);
	}

	// ------------------------------------------------------------------
	// 自定义扫码处理：先问后端，模板 → 弹窗选颜色；否则走标准行为
	// ------------------------------------------------------------------
	function handle_barcode_scan(barcode) {
		const item_selector = this; // ItemSelector 实例
		if (!item_selector || !item_selector.search_field || !item_selector.$component.is(":visible")) {
			return;
		}

		frappe.call({
			method: "solua_home.api.pos.scan_barcode_for_pos",
			args: { barcode: barcode },
			callback: (r) => {
				// 后端异常（网络/权限/数据库错误）——详情已由后端 log_error 记录
				if (r.exc) {
					item_selector.search_field.set_focus();
					frappe.show_alert({
						message: __("扫码查询失败，请稍后重试"),
						indicator: "red",
					});
					frappe.utils.play_sound("error");
					return;
				}
				const res = r.message;

				// 后端明确返回错误
				if (res && res.type === "error") {
					item_selector.search_field.set_focus();
					frappe.show_alert({
						message: __("扫码查询失败，请稍后重试"),
						indicator: "red",
					});
					frappe.utils.play_sound("error");
					return;
				}

				// 模板商品（条码挂模板上）→ 弹窗选颜色
				if (res && res.type === "template") {
					show_color_picker(res);
					return;
				}

				// 未找到
				if (!res || res.type === "not_found") {
					item_selector.search_field.set_focus();
					frappe.show_alert({
						message: __("未找到条码 {0} 对应的商品", [barcode]),
						indicator: "orange",
					});
					frappe.utils.play_sound("error");
					return;
				}

				// Variant 或普通商品 → 保持 ERPNext 标准扫码行为
				item_selector.search_field.set_focus();
				item_selector.set_search_value(res.item_code || barcode);
				item_selector.barcode_scanned = true;
			},
		});
	}

	// ------------------------------------------------------------------
	// 判断单据是否含任何折扣（行折扣/整单折扣）
	// ------------------------------------------------------------------
	function has_unapproved_discount(doc) {
		if (!doc) return false;
		if (flt(doc.additional_discount_percentage) > 0) return true;
		if (flt(doc.discount_amount) > 0) return true;
		for (const it of doc.items || []) {
			if (flt(it.discount_percentage) > 0) return true;
			if (flt(it.discount_amount) > 0) return true;
		}
		return false;
	}

	// ------------------------------------------------------------------
	// POS 折扣审批密码对话框：提交时弹窗输入密码，验证通过才继续提交。
	// 返回 Promise：resolve(密码) 表示通过；resolve(null) 表示取消。
	// ------------------------------------------------------------------
	function show_pos_discount_approval(frm) {
		return new Promise((resolve) => {
			const dialog = new frappe.ui.Dialog({
				title: __("折扣审批"),
				static: true,
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "info",
						options: `<div style="margin-bottom:6px;color:var(--text-muted);font-size:0.9rem;">${__("本单据含折扣，提交前需管理员输入审批密码")}</div>`,
					},
					{
						fieldtype: "Password",
						fieldname: "approval_password",
						label: __("审批密码"),
						reqd: 1,
					},
				],
				primary_action_label: __("确认提交"),
				primary_action(values) {
					const password = (values.approval_password || "").trim();
					if (!password) return;
					frappe.call({
						method: "solua_home.api.sales.verify_discount_approval_password",
						args: { password, company: frm.doc.company },
						callback: (r) => {
							if (r.message && r.message.ok) {
								dialog.hide();
								resolve(password);
							} else {
								frappe.show_alert({
									message: __("审批密码错误，请重新输入"),
									indicator: "red",
								});
								frappe.utils.play_sound("error");
								dialog.get_field("approval_password").$input.focus();
							}
						},
					});
				},
				secondary_action() {
					dialog.hide();
					resolve(null);
				},
			});
			dialog.show();
			dialog.get_field("approval_password").$input.focus();
		});
	}

	// ------------------------------------------------------------------
	// 拦截模板物料的「点击/自动加购」：不直接加（模板无价会报
	// 「未设置物料价格」），改为弹颜色选择框让收银员选具体颜色。
	// 覆盖场景：手工输入条码回车、原生扫码路径（搜索→自动加购）、
	// 直接在结果列表点模板卡片。
	// ------------------------------------------------------------------
	function attach_template_click_interceptor(selector) {
		if (!selector || !selector.$component || !selector.$component[0]) return;
		if (selector._template_click_bound) return; // 同一实例只绑一次
		selector._template_click_bound = true;

		const me = selector;
		// capture 阶段先于原生 bubble 处理执行；stopPropagation 阻止原生加购
		selector.$component[0].addEventListener(
			"click",
			function (e) {
				const $item = $(e.target).closest(".item-wrapper");
				if (!$item.length) return;
				const item_code = $item.attr("data-item-code");
				if (!item_code) return;
				const item = (me.items || []).find((i) => i.item_code === item_code);
				if (!item || !item.has_variants) return; // 非模板：交给原生处理

				e.preventDefault();
				e.stopPropagation();
				frappe.call({
					method: "solua_home.api.pos.scan_barcode_for_pos",
					args: { barcode: item_code },
					callback: (r) => {
						const res = r.message;
						if (res && res.type === "template") show_color_picker(res);
					},
				});
			},
			true
		);
	}

	// ------------------------------------------------------------------
	// 绑定：把 ItemSelector 的默认扫码监听替换成自定义实现
	// ------------------------------------------------------------------
	let poll_attempts = 0;

	function apply_custom_barcode_handler() {
		if (applied) return;

		// 等待 POS bundle 加载完成（ItemSelector 类定义于 point-of-sale.bundle.js）
		// 最多轮询 60 次（约 30 秒），超时则静默放弃，避免后台空转
		if (!window.erpnext || !window.erpnext.PointOfSale || !window.erpnext.PointOfSale.ItemSelector) {
			if (poll_attempts++ < 60) {
				setTimeout(apply_custom_barcode_handler, 500);
			}
			return;
		}

		applied = true;

		const original_bind_events = erpnext.PointOfSale.ItemSelector.prototype.bind_events;
		const original_get_items = erpnext.PointOfSale.ItemSelector.prototype.get_items;
		const original_filter_items = erpnext.PointOfSale.ItemSelector.prototype.filter_items;

		// 搜索命中「唯一模板」→ 自动弹颜色选择框。
		// 覆盖：手工输入条码回车、原生扫码路径（搜索→展示）——
		// POS Profile auto_add_item_to_cart=0 时原生路径只显示模板卡片不会弹框。
				erpnext.PointOfSale.ItemSelector.prototype.filter_items = function (opts = {}) {
			const me = this;
			original_filter_items.call(this, opts);

			const search_term = (opts.search_term || "").toString().trim();
			if (!search_term) return;

			// 等原生异步渲染完成（fetch + render）后再检查结果
			setTimeout(() => {
				const items = me.items || [];
				if (items.length !== 1 || !items[0].has_variants) return;
				// 搜索框内容已变（用户继续输入/已清空）则跳过，避免误弹
				const cur =
					me.search_field && me.search_field.get_value && me.search_field.get_value();
				if (cur !== search_term) return;

				frappe.call({
					method: "solua_home.api.pos.scan_barcode_for_pos",
					args: { barcode: items[0].item_code },
					callback: (r) => {
						const res = r.message;
						if (res && res.type === "template") show_color_picker(res);
					},
				});
			}, 500);
		};

		// POS 提交拦截：带未审批折扣时弹审批密码对话框（仅 POS 发票）
		const original_form_savesubmit = frappe.ui.form.Form.prototype.savesubmit;
		frappe.ui.form.Form.prototype.savesubmit = function (btn, callback, on_error) {
			const me = this;
			const doc = me.doc;
			const is_pos =
				window.cur_pos && window.cur_pos.frm === me && doc && doc.is_pos;
			if (is_pos && has_unapproved_discount(doc)) {
				return show_pos_discount_approval(me).then((password) => {
					if (password) doc.custom_approval_password = password;
					return original_form_savesubmit.call(me, btn, callback, on_error);
				});
			}
			return original_form_savesubmit.call(me, btn, callback, on_error);
		};

		// ------------------------------------------------------------------
		// 收银完成后：静默小票打印（无信头、不弹新标签页）+ 打印完成后自动开新单
		// ------------------------------------------------------------------
		// 默认行为：POS Profile 勾了「打印收据」后，收银完成会走 frappe.utils.print
		// 在【新标签页】打开带正式信头的 printview —— 太慢太正式。
		// 这里替换为：隐藏 iframe 加载 printview（no_letterhead=1）→ 调 window.print()
		// （阻塞到打印对话框关闭）→ 自动开始新订单，像超市收银台一样无缝衔接。

		// 静默小票打印：返回 Promise，打印对话框关闭后 resolve
		function pos_silent_print(doctype, docname, print_format) {
			return new Promise((resolve) => {
				const url =
					"/printview?doctype=" +
					encodeURIComponent(doctype) +
					"&name=" +
					encodeURIComponent(docname) +
					"&trigger_print=0" +
					"&format=" +
					encodeURIComponent(print_format || "") +
					"&no_letterhead=1" +
					"&_lang=" +
					encodeURIComponent(frappe.boot.lang || "zh");

				const iframe = document.createElement("iframe");
				// 移到屏幕外但保留真实尺寸，保证打印版式正常计算
				iframe.style.cssText =
					"position:absolute;left:-9999px;top:0;width:595px;height:842px;border:0;opacity:0;";
				let done = false;
				const finish = () => {
					if (done) return;
					done = true;
					setTimeout(() => {
						if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
						resolve();
					}, 200);
				};

				iframe.onload = () => {
					try {
						iframe.contentWindow.focus();
						iframe.contentWindow.print(); // 阻塞直到打印对话框关闭
					} catch (e) {
						console.error("[solua_home] 小票打印失败:", e);
					}
					finish();
				};
				iframe.onerror = finish;
				// 兜底：15 秒内未完成也继续，避免卡住收银
				setTimeout(finish, 15000);
				iframe.src = url;
				document.body.appendChild(iframe);
			});
		}

		// 手动「打印小票」按钮也走静默打印（不再弹新标签页）
		const original_print_receipt =
			erpnext.PointOfSale.PastOrderSummary.prototype.print_receipt;
		erpnext.PointOfSale.PastOrderSummary.prototype.print_receipt = function () {
			const frm = this.events.get_frm();
			pos_silent_print(this.doc.doctype, this.doc.name, frm.pos_print_format);
		};

		// 独立开关「收银后自动开新单」（与自动打印分开控制）：
		// settings 由 get_pos_profile_data 返回完整 POS Profile 文档（含自定义字段）。
		// 透明包装构造函数（保留原型链），把 custom_auto_new_order 存到实例上，
		// 字段不存在时默认 1（保持原「打印后自动开新单」行为）。
		const OriginalPastOrderSummary = erpnext.PointOfSale.PastOrderSummary;
		function PosPastOrderSummary(...args) {
			const inst = Reflect.construct(OriginalPastOrderSummary, args, PosPastOrderSummary);
			// 原生构造函数签名是单对象 { wrapper, settings, events }——settings 在 args[0].settings
			const opts = (args && args[0]) || {};
			const settings = opts.settings || {};
			inst.auto_new_order_on_complete =
				settings.custom_auto_new_order === undefined
					? 1
					: Number(settings.custom_auto_new_order) === 1;
			return inst;
		}
		PosPastOrderSummary.prototype = OriginalPastOrderSummary.prototype;
		erpnext.PointOfSale.PastOrderSummary = PosPastOrderSummary;

		// 收银成功后：正常渲染收据摘要（临时关掉默认 new-tab 打印）→ 静默打印 → 自动开新单
		// 两个开关独立控制：
		//   打印开 + 开新单开 → 静默打印，打印完成（对话框关闭）后自动开新单
		//   打印开 + 开新单关 → 只静默打印，停留在收据摘要页
		//   打印关 + 开新单开 → 不打印，短暂显示摘要后自动开新单
		//   打印关 + 开新单关 → 原生行为（停留摘要页，手动点新订单）
		const original_load_summary_of =
			erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of;
		erpnext.PointOfSale.PastOrderSummary.prototype.load_summary_of = function (doc, after_submission = false) {
			const should_print = after_submission && this.print_receipt_on_order_complete;
			const auto_new = after_submission && this.auto_new_order_on_complete;
			if (should_print || auto_new) {
				const frm = this.events.get_frm();
				if (should_print) {
					this.print_receipt_on_order_complete = 0; // 阻止默认 new-tab 打印
					original_load_summary_of.call(this, doc, after_submission);
					this.print_receipt_on_order_complete = 1;
					pos_silent_print(doc.doctype || frm.doctype, doc.name, frm.pos_print_format).then(() => {
						// 打印完成 → 自动开始新订单（超市收银模式）
						if (auto_new && this.events && this.events.new_order) this.events.new_order();
					});
				} else {
					// 打印关、开新单开：短暂显示收据摘要后自动开新单
					original_load_summary_of.call(this, doc, after_submission);
					setTimeout(() => {
						if (this.events && this.events.new_order) this.events.new_order();
					}, 1200);
				}
				return;
			}
			return original_load_summary_of.call(this, doc, after_submission);
		};

		// POS 商品数据带 has_variants：换用 solua_home 包装器
		// （附加模板标记后转发原生查询，前端据此拦截模板直加）
		erpnext.PointOfSale.ItemSelector.prototype.get_items = function (args) {
			const { start = 0, page_length = 40, search_term = "" } = args || {};
			const doc = this.events.get_frm().doc;
			const price_list = (doc && doc.selling_price_list) || this.price_list;
			const { item_group, pos_profile } = this;
			return frappe.call({
				method: "solua_home.api.pos.get_items",
				freeze: true,
				args: { start, page_length, price_list, item_group, search_term, pos_profile },
			});
		};

		// POS 每次刷新（如新建开单、重新进入）都会重建 ItemSelector 并重新执行
		// bind_events，所以把替换逻辑挂在原型方法上，保证始终生效。
		erpnext.PointOfSale.ItemSelector.prototype.bind_events = function () {
			original_bind_events.call(this);

			attach_template_click_interceptor(this);

			if (!window.onScan) return;
			window.onScan.detachFrom(document);
			window.onScan.attachTo(document, {
				onScan: (sScancode) => handle_barcode_scan.call(this, sScancode),
			});
		};

				// 初始不加载商品列表（后端 get_items 无搜索词返回空），未搜索时显示扫码提示
		const original_set_items_not_found_banner =
			erpnext.PointOfSale.ItemSelector.prototype.set_items_not_found_banner;
		erpnext.PointOfSale.ItemSelector.prototype.set_items_not_found_banner = function () {
			const searching =
				this.search_field && this.search_field.get_value && this.search_field.get_value();
			if (searching) {
				return original_set_items_not_found_banner.call(this);
			}
			this.$items_container.removeClass(this.item_display_class);
			this.$items_container.addClass("items-not-found");
			this.$items_container.html(
				`<div style="text-align:center;padding:48px 16px;color:var(--text-muted);">
					<div style="font-size:1.1rem;font-weight:600;margin-bottom:6px;">${__("请扫码或搜索商品")}</div>
					<div style="font-size:0.85rem;">${__("扫描条码或输入商品名称/编码")}</div>
				</div>`
			);
		};

// 极端时序兜底：如果组件在脚本加载前已构建完成，立即对当前实例生效
		if (window.cur_pos && window.cur_pos.item_selector && window.onScan) {
			window.onScan.detachFrom(document);
			window.onScan.attachTo(document, {
				onScan: (sScancode) => handle_barcode_scan.call(window.cur_pos.item_selector, sScancode),
			});
			attach_template_click_interceptor(window.cur_pos.item_selector);
		}
	}

	// ------------------------------------------------------------------
	// 弹窗样式
	// ------------------------------------------------------------------
	function inject_styles() {
		if (styles_injected) return;
		styles_injected = true;

		const css = `
			.color-picker-dialog { padding: 4px 0 8px; }
			.color-picker-template {
				font-size: 1.05rem;
				font-weight: 600;
				color: var(--text-color);
				margin-bottom: 2px;
			}
			.color-picker-subtitle {
				font-size: 0.85rem;
				color: var(--text-muted);
				margin-bottom: 12px;
			}
			.color-picker-grid {
				display: grid;
				grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
				gap: 10px;
				max-height: 46vh;
				overflow-y: auto;
				padding-right: 4px;
			}
			.color-picker-item {
				cursor: pointer;
				border: 1px solid var(--border-color);
				border-radius: 10px;
				padding: 10px 6px;
				text-align: center;
				background: var(--bg-color);
				transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
			}
			.color-picker-item:hover {
				border-color: var(--primary);
				box-shadow: 0 3px 10px rgba(0, 0, 0, 0.14);
				transform: translateY(-2px);
			}
			.color-picker-item:active { transform: translateY(0); }
			.color-swatch {
				width: 54px;
				height: 54px;
				margin: 0 auto 8px;
				border-radius: 50%;
				overflow: hidden;
				display: flex;
				align-items: center;
				justify-content: center;
				background: var(--control-bg);
				border: 1px solid var(--border-color);
			}
			.color-swatch-img { width: 100%; height: 100%; object-fit: cover; }
			.color-swatch-abbr { font-size: 1.15rem; font-weight: 700; color: var(--text-muted); }
			.color-name { font-size: 0.8rem; color: var(--text-color); word-break: break-all; line-height: 1.3; }
		`;

		$("<style>").attr("type", "text/css").text(css).appendTo("head");
	}

	// ------------------------------------------------------------------
	// 开店对话框自动预填唯一 POS Profile
	// ------------------------------------------------------------------
	function prefill_pos_profile() {
		// 等对话框真正显示（frappe.ui.open_dialogs 已 push）
		setTimeout(() => {
			const dialog = frappe.ui.open_dialogs.find(
				(d) => d.fields_dict && d.fields_dict.pos_profile && d.fields_dict.balance_details
			);
			if (!dialog) return;
			if (dialog.get_value("pos_profile")) return; // 已有值（用户手动选择过）

			const company =
				dialog.get_value("company") || frappe.defaults.get_default("company");
			if (!company) return;

			// 与 POS Profile Link 下拉同源：调用 whitelisted pos_profile_query
			// （收银员角色对子表 POS Profile User 无读权限，frappe.db.get_list 会
			// 抛 Insufficient Permission 导致预填静默失败，2026-08-16 修复）
			frappe.call({
				method:
					"erpnext.accounts.doctype.pos_profile.pos_profile.pos_profile_query",
				args: {
					doctype: "POS Profile",
					txt: "",
					searchfield: "name",
					start: 0,
					page_len: 5,
					filters: { company },
				},
				callback: (r) => {
					const profiles = r.message || [];
					if (profiles.length === 1) {
						// 返回格式 [[name], ...]（Link 查询方法的标准格式）
						const name = Array.isArray(profiles[0])
							? profiles[0][0]
							: profiles[0];
						dialog.set_value("pos_profile", name);
						// set_value 触发字段 onchange → 自动带出付款方式表
					}
				},
			});
		}, 300);
	}

	let opening_poll = 0;
	function wrap_opening_dialog() {
		if (
			!window.erpnext ||
			!window.erpnext.PointOfSale ||
			!window.erpnext.PointOfSale.Controller
		) {
			if (opening_poll++ < 60) setTimeout(wrap_opening_dialog, 300);
			return;
		}
		const proto = erpnext.PointOfSale.Controller.prototype;
		if (proto._opening_prefill_bound) return;
		proto._opening_prefill_bound = true;
		const original = proto.create_opening_voucher;
		proto.create_opening_voucher = function () {
			original.call(this);
			prefill_pos_profile();
		};
	}

	// 启动
	wrap_opening_dialog();
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", () => apply_custom_barcode_handler());
	} else {
		apply_custom_barcode_handler();
	}
})();
