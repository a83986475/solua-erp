// Native-form helpers for wholesale color receiving and mobile stock counting.
(() => {
	const variant_api = "solua_home.api.home.get_color_variants";
	const print_formats = { "Sales Order": "客户订单确认单（颜色版）", "Delivery Note": "Guia de Remessa" };

	function open_color_picker(frm, kind) {
		const is_receipt = kind === "receipt";
		const dialog = new frappe.ui.Dialog({
			title: is_receipt ? __("按色扫码收货") : __("按色扫码盘点"),
			fields: [
				{ fieldname: "barcode", label: __("款式/原包装条码"), fieldtype: "Data", reqd: 1, description: __("共用条码只识别款式，颜色必须人工选择") },
				{ fieldname: "variant", label: __("固定色号/颜色"), fieldtype: "Select", options: "", hidden: 1 },
				{ fieldname: "variant_preview", fieldtype: "HTML", hidden: 1 },
				{ fieldname: "qty", label: is_receipt ? __("收货数量（正整数）") : __("本次实盘数量（可为 0）"), fieldtype: "Data", hidden: 1 },
				{ fieldname: "warehouse", label: __("明确仓库"), fieldtype: "Link", options: "Warehouse", default: frm.doc.set_warehouse || frm.doc.last_scanned_warehouse || "", reqd: 1 },
				...(is_receipt ? [{ fieldname: "rate", label: __("最终单位成本"), fieldtype: "Currency", hidden: 1, min: 0.0001, description: __("直接输入外部算好的最终成本，不在系统内分摊到岸费用") }] : []),
				{ fieldname: "duplicate_mode", label: __("已有同色同仓行"), fieldtype: "Select", options: [{ label: __("覆盖数量"), value: "replace" }, { label: __("追加数量"), value: "append" }], default: "replace", hidden: 1 },
				{ fieldname: "hint", fieldtype: "HTML", options: `<div class="text-muted small">${__("没有新增行 = 尚未盘点；明确输入 0 = 实盘为 0。扫码后可连续录入。")}</div>` },
			],
			primary_action_label: __("查询颜色"),
		});
		let variants = [];
		let request_id = 0;
		let busy = false;
		let selected_barcode = "";
		const reset_selection = () => {
			++request_id;
			selected_barcode = "";
			variants = [];
			for (const field of ["variant", "qty", ...(is_receipt ? ["rate"] : [])]) {
				dialog.set_df_property(field, "reqd", 0);
				dialog.set_df_property(field, "hidden", 1);
			}
			dialog.set_value("variant", "");
			dialog.set_value("qty", "");
			if (is_receipt) dialog.set_value("rate", "");
			dialog.fields_dict.variant_preview.$wrapper.empty();
			dialog.set_primary_action(__("查询颜色"), lookup);
		};

		const render_preview = () => {
			const selected = variants.find((row) => row.name === dialog.get_value("variant"));
			const image = selected?.image ? `<img src="${frappe.utils.escape_html(selected.image)}" alt="" style="max-width:120px;max-height:120px;object-fit:contain">` : `<span class="text-muted">${__("无图片")}</span>`;
			dialog.fields_dict.variant_preview.$wrapper.html(`<div class="solua-wholesale-variant-preview">${image}<span>${frappe.utils.escape_html(selected?.color_code || selected?.color || selected?.item_name || "")}</span></div>`);
		};

		const show_variants = (data) => {
			variants = (data.templates || []).flatMap((group) => group.variants || []);
			if (!variants.length) {
				frappe.msgprint({ message: __("未找到可选颜色或无权查看该物料"), indicator: "orange" });
				return;
			}
			const options = [{label: __("请选择颜色/规格"), value: ""}, ...variants.map((row) => ({ label: `${row.color_code || "—"} · ${row.color || row.item_name} · ${row.item_code}`, value: row.name }))];
			dialog.set_df_property("variant", "options", options);
			dialog.set_value("variant", "");
			dialog.set_df_property("variant", "hidden", 0);
			dialog.set_df_property("variant_preview", "hidden", 0);
			dialog.set_df_property("qty", "hidden", 0);
			dialog.set_df_property("duplicate_mode", "hidden", 0);
			if (is_receipt) dialog.set_df_property("rate", "hidden", 0);
			for (const field of ["variant", "qty", ...(is_receipt ? ["rate"] : [])]) dialog.set_df_property(field, "reqd", 1);
			dialog.set_primary_action(__("加入单据"), add_row);
			dialog.fields_dict.variant.$input?.focus();
			render_preview();
		};

		const lookup = async () => {
			if (busy) return;
			const barcode = (dialog.get_value("barcode") || "").trim();
			if (!barcode) return;
			reset_selection();
			const current_request = ++request_id;
			dialog.set_primary_action(__("查询中…"), () => {});
			try {
				const response = await frappe.call({ method: variant_api, args: { barcode } });
				if (current_request === request_id && barcode === (dialog.get_value("barcode") || "").trim()) {
					selected_barcode = barcode;
					show_variants(response.message || {});
				}
			} catch (error) {
				if (current_request === request_id) frappe.msgprint(__("查询失败，请重试"));
			} finally {
				if (current_request === request_id && !variants.length) dialog.set_primary_action(__("查询颜色"), lookup);
			}
		};

		const add_row = async () => {
			if (busy) return;
			const item_code = dialog.get_value("variant");
			const qty = Number(dialog.get_value("qty"));
			const rate = Number(dialog.get_value("rate"));
			const warehouse = dialog.get_value("warehouse");
			const raw_qty = dialog.get_value("qty");
			if (frm.doc.docstatus !== 0 || !selected_barcode || selected_barcode !== (dialog.get_value("barcode") || "").trim()
				|| !variants.some((row) => row.name === item_code) || !warehouse || raw_qty == null || String(raw_qty).trim() === ""
				|| !Number.isFinite(qty) || qty < 0 || !Number.isInteger(qty) || (is_receipt && (qty === 0 || !Number.isFinite(rate) || rate <= 0))) {
				frappe.msgprint(__("请完整填写仓库、颜色、整数数量；收货还需要最终单位成本"));
				return;
			}
			busy = true;
			dialog.set_primary_action(__("写入中…"), () => {});
			try {
				const existing = (frm.doc.items || []).find((row) => row.item_code === item_code && row.warehouse === warehouse);
				if (existing) {
					const next_qty = dialog.get_value("duplicate_mode") === "append" ? Number(existing.qty || 0) + qty : qty;
					await Promise.resolve(frappe.model.set_value(existing.doctype, existing.name, "qty", next_qty));
					if (is_receipt) await Promise.resolve(frappe.model.set_value(existing.doctype, existing.name, "rate", rate));
				} else {
					const row = frm.add_child("items");
					await frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
					await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "item_code", item_code));
					await frappe.model.set_value(row.doctype, row.name, "warehouse", warehouse);
					await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "qty", qty));
					if (is_receipt) await Promise.resolve(frappe.model.set_value(row.doctype, row.name, "rate", rate));
				}
				frm.refresh_field("items");
				frappe.show_alert({message: __("已加入当前草稿，请保存单据；可继续扫描"), indicator: "green"});
				await dialog.set_value("barcode", "");
				reset_selection();
				dialog.fields_dict.barcode.$input.focus();
			} catch (error) {
				// A native field trigger may have partly filled a row; require review
				// before a retry so append mode cannot silently repeat that write.
				reset_selection();
				frm.refresh_field("items");
				frappe.msgprint(__("录入未完成，请先检查单据行后重新扫描"));
			} finally {
				busy = false;
			}
		};

		dialog.fields_dict.variant.$input.on("change", render_preview);
		dialog.set_primary_action(__("查询颜色"), lookup);
		dialog.show();
		dialog.fields_dict.barcode.$input.on("input", () => { if (!busy) reset_selection(); });
		dialog.$wrapper.on("hidden.bs.modal", () => { ++request_id; });
		dialog.fields_dict.barcode.$input.on("keydown", (event) => {
			if (event.key === "Enter") { event.preventDefault(); lookup(); }
		});
		dialog.fields_dict.barcode.$input.focus();
	}

	function print_wholesale(frm) {
		const format = print_formats[frm.doctype];
		const dialog = new frappe.ui.Dialog({
			title: __("打印选项"),
			fields: [
				{ fieldname: "show_images", label: __("显示颜色图片"), fieldtype: "Check", default: frm.doc.custom_print_color_images ? 1 : 0 },
				{ fieldname: "show_qr", label: __("显示色卡二维码"), fieldtype: "Check", default: frm.doc.custom_print_color_qr ? 1 : 0 },
			],
			primary_action_label: __("保存并打开预览"),
			async primary_action(values) {
				if (dialog.__printing) return;
				dialog.__printing = true;
				try {
				const changes = {};
				if (frm.fields_dict.custom_print_color_images) changes.custom_print_color_images = values.show_images ? 1 : 0;
				if (frm.fields_dict.custom_print_color_qr) changes.custom_print_color_qr = values.show_qr ? 1 : 0;
				if (Object.keys(changes).length) await frm.set_value(changes);
				if (frm.is_dirty()) await frm.save(frm.doc.docstatus === 1 ? "Update" : undefined);
				const params = new URLSearchParams({ doctype: frm.doctype, name: frm.doc.name, format, no_letterhead: "0", trigger_print: "1" });
				window.open(`/printview?${params.toString()}`, "_blank");
				dialog.hide();
				} finally {
					dialog.__printing = false;
				}
			},
		});
		dialog.show();
	}

	["Sales Order", "Delivery Note"].forEach((doctype) => frappe.ui.form.on(doctype, {
		refresh(frm) {
			const label = __(doctype === "Sales Order" ? "客户订单确认单" : "Guia de Remessa");
			if (!frm.is_new()) frm.add_custom_button(label, () => print_wholesale(frm), __("打印"));
		},
	}));

	frappe.ui.form.on("Purchase Receipt", { refresh(frm) { if (frm.doc.docstatus === 0) frm.add_custom_button(__("按色扫码收货"), () => open_color_picker(frm, "receipt"), __("工具")); } });
	frappe.ui.form.on("Stock Reconciliation", { refresh(frm) {
			if (frm.doc.docstatus === 0) frm.add_custom_button(__("手机扫码盘点"), () => open_color_picker(frm, "reconciliation"), __("工具"));
			if (!frm.__solua_count_note) { frm.__solua_count_note = true; frm.dashboard.add_comment(__("未列出的物料表示尚未盘点；明确列出并输入 0 才表示实盘为 0。"), "blue"); }
		} });
})();
