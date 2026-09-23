import { describe, expect, it } from "vitest";
import {
	resolveStockWarehouse,
	SELLABLE_ITEM_SQL,
	shouldShowCatalogItem,
} from "@/services/catalogPolicy";
import { getQueryableFields, type DoctypeMeta } from "@/services/doctypeMeta";

describe("catalog policy", () => {
	it("keeps concrete items and hides variant templates", () => {
		expect(SELLABLE_ITEM_SQL).toBe("i.`has_variants` = 0");
		expect(shouldShowCatalogItem(0)).toBe(true);
		expect(shouldShowCatalogItem(1)).toBe(false);
	});

	it("uses the requested warehouse unless a single local warehouse is available", () => {
		expect(resolveStockWarehouse("Stores - SH", ["Stores - SH"])).toBe("Stores - SH");
		expect(resolveStockWarehouse("Finished Goods - SH", ["Stores - SH"])).toBe("Stores - SH");
		expect(resolveStockWarehouse("Finished Goods - SH", ["Stores - SH", "Finished Goods - SH"])).toBe(
			"Finished Goods - SH",
		);
	});

	it("omits optional FBR list fields absent or hidden in Sales Invoice metadata", () => {
		const meta: DoctypeMeta = {
			name: "Sales Invoice",
			fields: [
				{ fieldname: "customer", fieldtype: "Link" },
				{ fieldname: "custom_fbr_invoice_no", fieldtype: "Data", hidden: 1 },
			],
		};

		expect(
			getQueryableFields(
				["name", "customer", "custom_fbr_invoice_no", "fbr_invoice_number"],
				meta,
			),
		).toEqual(["name", "customer"]);
	});
});
