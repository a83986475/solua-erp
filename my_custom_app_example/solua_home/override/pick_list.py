"""Pick List submit behavior for explicit warehouse shortage reporting."""

from erpnext.stock.doctype.pick_list.pick_list import PickList


def _reconcile_sales_order_locations(doc):
    """Restore a source order's own Sales Order reservation before planning picks."""
    import frappe
    from frappe.utils import flt

    if doc.purpose != "Delivery":
        return

    order_names = {row.sales_order for row in doc.get("locations") or [] if row.sales_order}
    if doc.get("custom_sales_order"):
        order_names.add(doc.custom_sales_order)
    if len(order_names) != 1:
        return

    order = frappe.get_doc("Sales Order", next(iter(order_names)))
    if order.docstatus != 1:
        return

    from erpnext.stock.doctype.packed_item.packed_item import is_product_bundle
    from erpnext.stock.get_item_details import get_bin_details
    from erpnext.stock.stock_balance import get_reserved_qty

    direct_rows = {}
    for row in doc.get("locations") or []:
        if row.sales_order == order.name and row.sales_order_item and not row.product_bundle_item:
            direct_rows.setdefault(row.sales_order_item, []).append(row)

    for source in order.get("items") or []:
        if source.delivered_by_supplier or is_product_bundle(source.item_code):
            continue

        factor = flt(source.conversion_factor) or 1
        remaining_uom = max(
            flt(source.qty) - max(flt(source.picked_qty) / factor, flt(source.delivered_qty)),
            0,
        )
        required_stock = remaining_uom * factor
        if required_stock <= 0:
            continue

        warehouse = source.warehouse or doc.parent_warehouse
        if not warehouse:
            continue

        actual_qty = flt(get_bin_details(source.item_code, warehouse, order.company).get("actual_qty"))
        total_reserved = flt(get_reserved_qty(source.item_code, warehouse))
        other_reserved = max(total_reserved - required_stock, 0)
        planned_stock = min(required_stock, max(actual_qty - other_reserved, 0))
        rows = direct_rows.get(source.name, [])

        if rows:
            row = rows[0]
            row.qty = planned_stock / factor
            row.stock_qty = planned_stock
            row.actual_qty = actual_qty
            for duplicate in rows[1:]:
                if not duplicate.picked_qty:
                    doc.remove(duplicate)
        elif planned_stock > 0:
            doc.append(
                "locations",
                {
                    "item_code": source.item_code,
                    "item_name": source.item_name,
                    "description": source.description,
                    "warehouse": warehouse,
                    "uom": source.uom,
                    "stock_uom": source.stock_uom,
                    "conversion_factor": factor,
                    "qty": planned_stock / factor,
                    "stock_qty": planned_stock,
                    "actual_qty": actual_qty,
                    "sales_order": order.name,
                    "sales_order_item": source.name,
                },
            )


class CustomPickList(PickList):
    """Do not silently turn an unreported shortage into a full pick."""

    def set_item_locations(self, save=False):
        # Let ERPNext allocate first, then correct only a single-order Delivery Pick List.
        super().set_item_locations(save=False)
        _reconcile_sales_order_locations(self)
        if save:
            self.save()

    def validate_picked_items(self):
        import frappe

        if self.purpose != "Delivery" or not frappe.get_meta("Pick List").has_field("custom_pick_result"):
            return super().validate_picked_items()

        from solua_home.api.stock import validate_pick_list_result

        validate_pick_list_result(self, require_result=True)
