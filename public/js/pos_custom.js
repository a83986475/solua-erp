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

	// 启动
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", () => apply_custom_barcode_handler());
	} else {
		apply_custom_barcode_handler();
	}
})();
