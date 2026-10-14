(() => {
  const itemQuery = "solua_home.api.sales_order_item_query.item_query";

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
  });
})();
