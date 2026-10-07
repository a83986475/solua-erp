// Solua daily wholesale forms; xPos and actual POS invoices keep their controls.
(() => {
    const shared = ["project", "sales_partner", "commission_section", "commission_rate",
        "total_commission", "amount_eligible_for_commission", "is_internal_customer",
        "inter_company_order_reference", "inter_company_reference", "inter_company_invoice_reference"];
    const tax = ["apply_tds", "ignore_tax_withholding_threshold",
        "override_tax_withholding_entries", "tax_withholding_entries", "tax_withholding_group",
        "tax_withholding_category", "section_tax_withholding_entry",
        "purchase_tax_withholding_category", "sales_tax_withholding_category"];
    function hide(frm, fields) {
        fields.forEach(field => {
            if (frm.fields_dict[field]) frm.set_df_property(field, "hidden", 1);
        });
    }
    function simplify(frm) {
        if (frm.doc.doctype === "Sales Invoice" && (frm.doc.is_pos || frm.doc.is_created_using_pos)) return;
        hide(frm, shared);
        hide(frm, ["is_subcontracted", "has_subcontracted"]);
        hide(frm, ["subcontracting_receipt", "subcontracting_order", "subcontracting_inward_order",
            "is_old_subcontracting_flow", "inspection_required", "quality_inspection"]);
        if (frm.doc.doctype === "Stock Entry") {
            frm.set_query?.("stock_entry_type", () => ({filters: {purpose: ["not in", [
                "Manufacture", "Send to Subcontractor", "Material Transfer for Manufacture",
                "Material Consumption for Manufacture", "Receive from Customer",
                "Return Raw Material to Customer", "Subcontracting Delivery", "Subcontracting Return", "Repack", "Disassemble",
            ]]}}));
        }
        if (frm.doc.doctype === "Item") {
            frm.set_df_property("valuation_rate", "label", __("默认入库成本"));
            frm.set_df_property("custom_rate_cost", "label", __("定价参考成本"));
            hide(frm, ["manufacturing", "include_item_in_manufacturing", "default_bom",
                "is_fixed_asset", "auto_create_assets", "is_grouped_asset", "asset_category", "asset_naming_series",
                "serial_nos_and_batches", "has_batch_no", "create_new_batch", "batch_number_series",
                "has_serial_no", "serial_no_series", "use_serial_no_wise_valuation", "quality_tab",
                "inspection_required_before_purchase", "inspection_required_before_delivery", "quality_inspection_template"]);
            frm.$wrapper?.find('[role="tab"][data-fieldname="quality_tab"], [role="tab"][data-fieldname="manufacturing"]').hide();
        }
        if (["Sales Order", "Purchase Order", "Purchase Receipt", "Delivery Note", "Item"].includes(frm.doc.doctype)) {
            hide_buttons(frm, ["Project", "Work Order", "Production Plan", "Subcontracting Inward Order",
                "Subcontracting Order", "Subcontracting Receipt", "Quality Inspection", "Asset", "BOM"]);
        }
        if (frm.doc.doctype === "Sales Order") {
            if (!frm.doc.order_type || frm.doc.order_type === "Sales") hide(frm, ["order_type"]);
            hide_buttons(frm, ["Work Order", "Production Plan", "Subcontracting Inward Order",
                "Subcontracting Order", "Request for Raw Materials"]);
        }
        hide(frm, tax);
        if (frm.doc.doctype === "Sales Invoice") {
            hide(frm, ["is_pos", "pos", "custom_is_topup", "custom_sales_invoice_approval_tab"]);
            frm.$wrapper?.find('[role="tab"][data-fieldname="custom_sales_invoice_approval_tab"]').hide();
            frm.$wrapper?.find('[role="tab"][data-fieldname="pos"]').hide();
        }
        if (frm.doc.doctype === "Delivery Note") {
            hide(frm, ["issue_credit_note"]);
            if (frm.doc.docstatus === 0 && frm.doc.issue_credit_note) frm.set_value("issue_credit_note", 0);
            hide_buttons(frm, ["Shipment", "Installation Note", "Delivery Trip"]);
        }
    }
    function hide_buttons(frm, buttons) {
            buttons.forEach(button => frm.remove_custom_button(__(button), __("Create")));
            // Frappe can rebuild dropdown entries when the menu opens.
            const wrapper = frm.page?.wrapper;
            if (wrapper) {
                const scope = "solua-simple-" + frm.doc.doctype.toLowerCase().replaceAll(" ", "-");
                wrapper.addClass(scope);
                const selectors = buttons.map(button =>
                    `.${scope} .dropdown-item[data-label="${encodeURIComponent(__(button))}"]`);
                const rule = `${selectors.join(",")} { display:none!important; }`;
                const style = wrapper.find("style.solua-delivery-menu");
                if (!style.length) wrapper.append(`<style class="solua-delivery-menu">${rule}</style>`);
                else if (!style.text().includes(rule)) style.text(style.text() + rule);
            }
    }
    ["Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry", "Purchase Order",
        "Purchase Receipt", "Purchase Invoice", "Item", "Stock Entry"].forEach(doctype =>
        frappe.ui.form.on(doctype, {
            refresh(frm) {
                simplify(frm);
                frappe.after_ajax(() => simplify(frm));
                setTimeout(() => simplify(frm), 0);
            },
            onload_post_render: simplify,
        }));
})();
