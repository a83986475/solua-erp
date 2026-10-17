"""Pick List submit behavior for explicit warehouse shortage reporting."""

from erpnext.stock.doctype.pick_list.pick_list import PickList


class CustomPickList(PickList):
    """Do not silently turn an unreported shortage into a full pick."""

    def validate_picked_items(self):
        import frappe

        if self.purpose != "Delivery" or not frappe.get_meta("Pick List").has_field("custom_pick_result"):
            return super().validate_picked_items()

        from solua_home.api.stock import validate_pick_list_result

        validate_pick_list_result(self, require_result=True)
