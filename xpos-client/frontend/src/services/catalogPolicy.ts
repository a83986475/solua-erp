export const SELLABLE_ITEM_SQL = "i.`has_variants` = 0";

export function shouldShowCatalogItem(hasVariants: unknown): boolean {
	return Number(hasVariants || 0) === 0;
}

export function resolveStockWarehouse(requested: string, available: string[]): string {
	const candidates = [...new Set(available.filter(Boolean))];
	if (!requested || candidates.includes(requested) || candidates.length !== 1) {
		return requested;
	}
	return candidates[0];
}
