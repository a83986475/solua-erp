"""Sales Order behavior overrides for Solua Home."""

from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class CustomSalesOrder(SalesOrder):
    """Allow sales orders without delivery dates."""

    def validate_delivery_date(self):
        # ERPNext raises when both the header and every item date are blank.
        # Keep its normal propagation and date checks whenever a date exists.
        no_delivery_date = not self.delivery_date and not any(
            row.delivery_date for row in self.get("items")
        )
        if not no_delivery_date:
            return super().validate_delivery_date()

        original_skip_delivery_note = self.skip_delivery_note
        self.skip_delivery_note = 1
        try:
            return super().validate_delivery_date()
        finally:
            self.skip_delivery_note = original_skip_delivery_note
