import { describe, expect, it } from "vitest";
import { resolveStockWarehouse, shouldShowCatalogItem } from "@/services/catalogPolicy";

describe("catalog policy", () => {
	it("keeps concrete items and hides variant templates", () => {
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
});
