"""Delivery Note behavior that differs for stock-return documents."""

from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote


class CustomDeliveryNote(DeliveryNote):
    """Allow a return to repair an existing negative balance without opening normal sales."""

    def update_stock_ledger(self, allow_negative_stock=False):
        if self.is_return:
            allow_negative_stock = True
        return super().update_stock_ledger(allow_negative_stock=allow_negative_stock)
