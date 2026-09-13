// solua_home：业务数量统一为正整数（最小 1）。

(function () {
    "use strict";

    const DOCTYPES = [
        "Sales Invoice",
        "Sales Order",
        "Quotation",
        "Delivery Note",
        "Purchase Order",
        "Purchase Receipt",
        "Purchase Invoice",
        "Material Request",
        "Pick List",
        "Packing Slip",
        "Request for Quotation",
        "Supplier Quotation",
        "Stock Entry",
    ];

    function validate_rows(frm) {
        for (const row of frm.doc.items || []) {
            if (!row.item_code || row.qty === undefined || row.qty === null || row.qty === "") continue;
            let qty = Number(row.qty);
            if (frm.doc.is_return && qty < 0) qty = Math.abs(qty);
            if (!Number.isFinite(qty) || !Number.isInteger(qty) || qty < 1) {
                frappe.throw(__("物料 {0} 的数量必须是大于等于 1 的整数，当前值为 {1}", [row.item_code, row.qty]));
            }
        }
    }

    function configure_qty_field(frm) {
        const grid = frm.fields_dict.items && frm.fields_dict.items.grid;
        const field = grid && grid.get_field("qty");
        if (field && field.df) {
            field.df.precision = 0;
            field.df.min = 1;
            field.df.step = 1;
        }

        const wrapper = grid && grid.wrapper;
        if (wrapper) {
            wrapper.find('[data-fieldname="qty"] input').attr({
                min: 1,
                step: 1,
                inputmode: "numeric",
                pattern: "[0-9]*",
            });
        }
    }

    DOCTYPES.forEach((doctype) => {
        frappe.ui.form.on(doctype, {
            refresh(frm) {
                configure_qty_field(frm);
            },
            validate(frm) {
                validate_rows(frm);
            },
        });
    });

    function validate_optional_qty(frm, fieldnames, zeroIsDisabled) {
        for (const fieldname of fieldnames) {
            const value = frm.doc[fieldname];
            if (value === undefined || value === null || value === "" || (zeroIsDisabled && Number(value) === 0)) continue;
            const qty = Number(value);
            if (!Number.isFinite(qty) || !Number.isInteger(qty) || qty < 1) {
                frappe.throw(__("{0} 必须是大于等于 1 的整数，当前值为 {1}", [fieldname, value]));
            }
        }
    }

    frappe.ui.form.on("Pricing Rule", {
        refresh(frm) {
            ["min_qty", "max_qty", "free_qty"].forEach((fieldname) => {
                const input = frm.fields_dict[fieldname] && frm.fields_dict[fieldname].$input;
                if (input) input.attr({ min: 1, step: 1, inputmode: "numeric", pattern: "[0-9]*" });
            });
        },
        validate(frm) {
            validate_optional_qty(frm, ["min_qty", "max_qty", "free_qty"], true);
        },
    });

    frappe.ui.form.on("Product Bundle Definition", {
        refresh(frm) {
            const input = frm.fields_dict.quantity && frm.fields_dict.quantity.$input;
            if (input) input.attr({ min: 1, step: 1, inputmode: "numeric", pattern: "[0-9]*" });
        },
        validate(frm) {
            validate_optional_qty(frm, ["quantity"], false);
        },
    });

    // Grid 行进入编辑状态后才生成输入框，因此用事件委托补上原生输入约束。
    $(document)
        .off("focusin.solua_home_qty", '[data-fieldname="items"] [data-fieldname="qty"] input')
        .on("focusin.solua_home_qty", '[data-fieldname="items"] [data-fieldname="qty"] input', function () {
            $(this).attr({ min: 1, step: 1, inputmode: "numeric", pattern: "[0-9]*" });
        })
        .off("keydown.solua_home_qty", '[data-fieldname="items"] [data-fieldname="qty"] input, [data-fieldname="min_qty"] input, [data-fieldname="max_qty"] input, [data-fieldname="free_qty"] input, [data-fieldname="quantity"] input')
        .on("keydown.solua_home_qty", '[data-fieldname="items"] [data-fieldname="qty"] input, [data-fieldname="min_qty"] input, [data-fieldname="max_qty"] input, [data-fieldname="free_qty"] input, [data-fieldname="quantity"] input', function (event) {
            if ([".", ",", "-", "+", "e", "E"].includes(event.key)) event.preventDefault();
        });
})();
