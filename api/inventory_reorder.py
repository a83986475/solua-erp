import json
import math

import frappe
from frappe.utils import cint, flt


DEFAULT_WAREHOUSE = "Receiving - SH"


def _bounded_int(value, default, minimum, maximum):
    try:
        parsed = cint(value)
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


@frappe.whitelist()
def get_inventory_reorder_rows(warehouse=DEFAULT_WAREHOUSE, lead_days=60, buffer_days=14):
    warehouse = (warehouse or DEFAULT_WAREHOUSE).strip()
    lead_days = _bounded_int(lead_days, 60, 1, 365)
    buffer_days = _bounded_int(buffer_days, 14, 0, 90)

    rows = frappe.db.sql(
        """
        WITH params AS (
            SELECT %(warehouse)s AS warehouse, %(lead_days)s AS lead_days, %(buffer_days)s AS buffer_days
        ),
        sales AS (
            SELECT
                sle.item_code,
                SUM(CASE WHEN sle.posting_date >= DATE_SUB(CURRENT_DATE, INTERVAL 29 DAY) THEN -sle.actual_qty ELSE 0 END) AS sold_30,
                SUM(CASE WHEN sle.posting_date >= DATE_SUB(CURRENT_DATE, INTERVAL 59 DAY) THEN -sle.actual_qty ELSE 0 END) AS sold_60,
                SUM(-sle.actual_qty) AS sold_90
            FROM `tabStock Ledger Entry` sle
            JOIN params p ON p.warehouse = sle.warehouse
            WHERE sle.is_cancelled = 0
              AND sle.posting_date >= DATE_SUB(CURRENT_DATE, INTERVAL 89 DAY)
              AND sle.voucher_type IN ('Delivery Note', 'Sales Invoice', 'POS Invoice')
            GROUP BY sle.item_code
        ),
        reorder AS (
            SELECT
                parent AS item_code,
                warehouse,
                MAX(warehouse_reorder_level) AS current_reorder_level,
                MAX(warehouse_reorder_qty) AS current_reorder_qty
            FROM `tabItem Reorder`
            WHERE material_request_type = 'Purchase'
            GROUP BY parent, warehouse
        )
        SELECT
            i.name AS item_code,
            i.item_name,
            i.stock_uom,
            COALESCE(s.sold_30, 0) AS sold_30,
            COALESCE(s.sold_60, 0) AS sold_60,
            COALESCE(s.sold_90, 0) AS sold_90,
            ROUND(COALESCE(s.sold_90, 0) / 90, 3) AS daily_sales,
            COALESCE(b.actual_qty, 0) AS actual_qty,
            COALESCE(b.reserved_qty, 0) AS reserved_qty,
            COALESCE(b.ordered_qty, 0) AS ordered_qty,
            COALESCE(b.projected_qty, 0) AS projected_qty,
            COALESCE(r.current_reorder_level, 0) AS current_reorder_level,
            COALESCE(r.current_reorder_qty, 0) AS current_reorder_qty,
            CEIL(GREATEST(COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days), 0)) AS suggested_warning,
            CEIL(GREATEST(
                COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days) - COALESCE(b.projected_qty, 0),
                0
            )) AS suggested_order_qty,
            CASE
                WHEN COALESCE(s.sold_90, 0) <= 0 THEN '暂无近90天净出库'
                WHEN COALESCE(b.actual_qty, 0) - COALESCE(b.reserved_qty, 0) <= 0 THEN '缺货或已被预留'
                WHEN COALESCE(b.actual_qty, 0) <= CEIL(GREATEST(COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days), 0))
                    THEN '达到建议预警线'
                WHEN COALESCE(b.projected_qty, 0) < CEIL(GREATEST(COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days), 0))
                    THEN '预计补货前不足'
                ELSE '库存充足'
            END AS status
        FROM `tabItem` i
        CROSS JOIN params p
        LEFT JOIN sales s ON s.item_code = i.name
        LEFT JOIN `tabBin` b ON b.item_code = i.name AND b.warehouse = p.warehouse
        LEFT JOIN reorder r ON r.item_code = i.name AND r.warehouse = p.warehouse
        WHERE i.disabled = 0
          AND i.is_stock_item = 1
          AND (
              COALESCE(s.sold_90, 0) > 0
              OR COALESCE(b.actual_qty, 0) <> 0
              OR r.item_code IS NOT NULL
          )
        ORDER BY
            CASE
                WHEN COALESCE(s.sold_90, 0) <= 0 THEN 5
                WHEN COALESCE(b.actual_qty, 0) - COALESCE(b.reserved_qty, 0) <= 0 THEN 1
                WHEN COALESCE(b.actual_qty, 0) <= CEIL(GREATEST(COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days), 0)) THEN 2
                WHEN COALESCE(b.projected_qty, 0) < CEIL(GREATEST(COALESCE(s.sold_90, 0) / 90 * (p.lead_days + p.buffer_days), 0)) THEN 3
                ELSE 4
            END,
            COALESCE(s.sold_90, 0) DESC,
            i.name
        LIMIT 5000
        """,
        {
            "warehouse": warehouse,
            "lead_days": lead_days,
            "buffer_days": buffer_days,
        },
        as_dict=True,
    )

    return {
        "warehouse": warehouse,
        "lead_days": lead_days,
        "buffer_days": buffer_days,
        "rows": rows,
    }


@frappe.whitelist()
def apply_inventory_reorder_changes(changes, warehouse=DEFAULT_WAREHOUSE):
    if isinstance(changes, str):
        try:
            changes = json.loads(changes)
        except json.JSONDecodeError:
            frappe.throw("提交的修改数据格式不正确")

    if not isinstance(changes, list) or not changes:
        frappe.throw("请至少选择一条物料")
    if len(changes) > 500:
        frappe.throw("单次最多修改 500 条物料")

    warehouse = (warehouse or DEFAULT_WAREHOUSE).strip()
    results = []

    for change in changes:
        item_code = str(change.get("item_code") or "").strip()
        target_warehouse = str(change.get("warehouse") or warehouse).strip()
        if not item_code or not target_warehouse:
            frappe.throw("物料和仓库不能为空")

        new_level = max(0, flt(change.get("reorder_level")))
        new_qty = max(0, flt(change.get("reorder_qty")))

        item = frappe.get_doc("Item", item_code)
        if not frappe.has_permission("Item", "write", doc=item):
            frappe.throw(f"没有修改物料 {item_code} 的权限")

        reorder_row = next(
            (
                row
                for row in item.get("reorder_levels", [])
                if row.warehouse == target_warehouse and row.material_request_type == "Purchase"
            ),
            None,
        )

        if reorder_row:
            before_level = flt(reorder_row.warehouse_reorder_level)
            before_qty = flt(reorder_row.warehouse_reorder_qty)
            reorder_row.db_set(
                {
                    "warehouse_reorder_level": new_level,
                    "warehouse_reorder_qty": new_qty,
                },
                update_modified=True,
            )
        else:
            before_level = 0
            before_qty = 0
            item.append(
                "reorder_levels",
                {
                    "warehouse": target_warehouse,
                    "material_request_type": "Purchase",
                    "warehouse_reorder_level": new_level,
                    "warehouse_reorder_qty": new_qty,
                },
            )
            item.save()

        results.append(
            {
                "item_code": item_code,
                "warehouse": target_warehouse,
                "before_level": before_level,
                "after_level": new_level,
                "before_qty": before_qty,
                "after_qty": new_qty,
            }
        )

    return {"updated": len(results), "results": results}
