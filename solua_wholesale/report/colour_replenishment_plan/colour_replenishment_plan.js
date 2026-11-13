frappe.query_reports["Colour Replenishment Plan"] = {
    filters: [
        {fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company", reqd: 1,
            default: frappe.defaults.get_user_default("Company")},
        {fieldname: "template", label: __("��ʽģ��"), fieldtype: "Link", options: "Item", reqd: 1,
            get_query: () => ({filters: {has_variants: 1, disabled: 0}})},
        {fieldname: "warehouse", label: __("�ֿ⣨��ѡ��"), fieldtype: "Link", options: "Warehouse",
            get_query: () => ({filters: {is_group: 0, disabled: 0, company: frappe.query_report.get_filter_value("company")}})},
        {fieldname: "history_days", label: __("�ؿ�����"), fieldtype: "Int", default: 90, reqd: 1},
        {fieldname: "lead_days", label: __("�������ڣ��죩"), fieldtype: "Int", reqd: 1},
        {fieldname: "cover_days", label: __("�����󱸻�����"), fieldtype: "Int", reqd: 1},
    ],
    formatter(value, row, column, data, default_formatter) {
        if (["suggested_qty", "daily_rate"].includes(column.fieldname) && data?.[column.fieldname] == null) {
            return "��";
        }
        return default_formatter(value, row, column, data);
    },
    onload(report) {
        report.page.set_title(__("����ɫ��������"));
        report.page.add_inner_button(__("�������ζ�����"), () => {
            const rows = (report.data || []).filter(row => row.item_code);
            if (!rows.length) {
                frappe.msgprint(__("����ѡ���ʽ�����б���"));
                return;
            }
            const template = rows[0].template || report.get_filter_value("template");
            const dialog = new frappe.ui.Dialog({
                title: __("�������ζ�����"),
                size: "large",
                fields: [{
                    fieldname: "items", fieldtype: "Table", in_place_edit: true,
                    cannot_add_rows: true, cannot_delete_rows: true,
                    data: rows.map(row => ({...row, planned_qty: row.suggested_qty || 0})),
                    fields: [
                        {fieldname: "item_code", label: __("��ɫ����"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 3},
                        {fieldname: "colour", label: __("ɫ��"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 2},
                        {fieldname: "stock_uom", label: __("��浥λ"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 1},
                        {fieldname: "suggested_qty", label: __("������"), fieldtype: "Data", read_only: 1, in_list_view: 1, columns: 2},
                        {fieldname: "planned_qty", label: __("���ζ�����"), fieldtype: "Int", non_negative: 1, in_list_view: 1, columns: 2},
                    ],
                }],
                primary_action_label: __("���������嵥��CSV��"),
                primary_action({items}) {
                    const planned = items.filter(row => Number(row.planned_qty) > 0);
                    if (!planned.length) {
                        frappe.msgprint(__("��������дһ����ɫ�Ķ�������"));
                        return;
                    }
                    const csvCell = value => {
                        let text = String(value ?? "");
                        if (/^\s*[=+@-]/.test(text)) text = "'" + text;
                        return `"${text.replace(/"/g, '""')}"`;
                    };
                    const data = [
                        [__("��ʽ"), __("��ɫ����"), __("ɫ��"), __("��浥λ"), __("������"), __("���ζ�����")],
                        ...planned.map(row => [template, row.item_code, row.colour, row.stock_uom, row.suggested_qty, row.planned_qty]),
                    ];
                    const csv = data.map(row => row.map(csvCell).join(",")).join("\r\n");
                    const url = URL.createObjectURL(new Blob(["\ufeff", csv], {type: "text/csv;charset=utf-8"}));
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `${__("��ɫ�����嵥")}-${template.replace(/[^\w.-]/g, "_")}.csv`;
                    link.click();
                    setTimeout(() => URL.revokeObjectURL(url), 1000);
                },
            });
            dialog.show();
        });
    },
};

