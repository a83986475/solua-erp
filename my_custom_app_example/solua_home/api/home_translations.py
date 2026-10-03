"""Repeatable native report title translations for the Solua homepage release."""
import frappe


def install():
    titles = {"Solua Business Totals": "经营金额报表", "Solua Delivery Summary": "送货汇总"}
    for source, translated in titles.items():
        names = frappe.get_all("Translation", filters={"language": "zh", "source_text": source}, pluck="name")
        if names:
            if any(frappe.get_doc("Translation", name).translated_text != translated for name in names):
                frappe.throw(f"已有不同的报表翻译，请先核对：{source}")
            continue
        frappe.get_doc({"doctype": "Translation", "language": "zh", "source_text": source,
                        "translated_text": translated}).insert()
    frappe.db.commit()
    return titles
