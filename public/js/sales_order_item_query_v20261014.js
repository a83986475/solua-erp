(() => {
  const itemQuery = "solua_home.api.sales_order_item_query.item_query";
  const sortOptions = [
    ["rate_desc", "单价：从高到低"],
    ["rate_asc", "单价：从低到高"],
    ["qty_desc", "数量：从高到低"],
    ["qty_asc", "数量：从低到高"],
    ["original", "恢复原顺序"],
  ];

  const numberValue = (row, field) => Number(row?.[field]) || 0;

  function sortItems(frm, mode) {
    const items = frm.doc.items || [];
    if (items.length < 2) {
      frappe.msgprint(__("至少需要两行物料才能排序"));
      return;
    }
    if (!Array.isArray(frm.__solua_original_item_order)) {
      frm.__solua_original_item_order = items.map((row) => row.name);
    }
    const original = new Map(frm.__solua_original_item_order.map((name, index) => [name, index]));
    const rows = [...items];
    if (mode === "original") {
      rows.sort((a, b) => (original.get(a.name) ?? Number.MAX_SAFE_INTEGER) - (original.get(b.name) ?? Number.MAX_SAFE_INTEGER));
    } else {
      const [field, direction] = mode.split("_");
      rows.sort((a, b) => {
        const difference = numberValue(a, field === "qty" ? "qty" : "rate") - numberValue(b, field === "qty" ? "qty" : "rate");
        return difference ? (direction === "desc" ? -difference : difference) : (original.get(a.name) ?? a.idx) - (original.get(b.name) ?? b.idx);
      });
    }
    frm.doc.items.splice(0, items.length, ...rows);
    rows.forEach((row, index) => { row.idx = index + 1; });
    frm.refresh_field("items");
    frm.dirty();
    frappe.show_alert({ message: __("物料顺序已调整，请保存订单"), indicator: "green" });
  }

  function openItemSortDialog(frm) {
    const dialog = new frappe.ui.Dialog({
      title: __("物料排序"),
      fields: [{
        fieldname: "sort_by",
        label: __("排序方式"),
        fieldtype: "Select",
        options: sortOptions.map(([, label]) => __(label)).join("\n"),
        default: __(sortOptions[0][1]),
      }],
      primary_action_label: __("应用排序"),
      primary_action(values) {
        const option = sortOptions.find(([, label]) => __(label) === values.sort_by) || sortOptions[0];
        sortItems(frm, option[0]);
        dialog.hide();
      },
    });
    dialog.show();
  }

  frappe.ui.form.on("Sales Order", {
    setup(frm) {
      if (!frm.fields_dict?.items?.grid?.get_field("item_code")) return;
      frm.set_query("item_code", "items", () => ({
        query: itemQuery,
        filters: {
          is_sales_item: 1,
          customer: frm.doc.customer,
          has_variants: 0,
        },
      }));
    },
    refresh(frm) {
      frm.remove_custom_button?.(__("物料排序"), __("工具"));
      if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__("物料排序"), () => openItemSortDialog(frm), __("工具"));
      }
    },
  });

  if (typeof window !== "undefined") {
    window.solua_home_sales_order_item_sort = { sortItems, sortOptions };
  }
})();
