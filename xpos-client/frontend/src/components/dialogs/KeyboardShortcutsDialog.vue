<template>
	<Dialog
		:open="open"
		@update:open="
			(val: boolean) => {
				if (!val) $emit('close');
			}
		"
	>
		<DialogContent class="max-w-2xl max-h-[85vh]">
			<DialogHeader>
				<DialogTitle class="flex items-center gap-2">
					<Keyboard class="w-5 h-5" />
					{{ __("Keyboard Shortcuts") }}
				</DialogTitle>
				<DialogDescription>
					{{ __("Use these keyboard shortcuts to navigate faster") }}
				</DialogDescription>
			</DialogHeader>

			<ScrollArea class="max-h-[60vh]">
				<div class="space-y-6 pe-4">
					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<Monitor class="w-4 h-4" />
							{{ __("General") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem
								:shortcut="['Ctrl', 'N']"
								:description="__('New Sale / Clear Cart')"
							/>
							<ShortcutItem
								:shortcut="['Ctrl', 'K']"
								:description="__('Open Command Search')"
							/>
							<ShortcutItem
								:shortcut="['Ctrl', '/']"
								:description="__('Show Keyboard Shortcuts')"
							/>
							<ShortcutItem :shortcut="['Ctrl', ',']" :description="__('Open Settings')" />
							<ShortcutItem :shortcut="['F11']" :description="__('Toggle Full Screen')" />
							<ShortcutItem :shortcut="['Escape']" :description="__('Close Dialog / Cancel')" />
						</div>
					</div>

					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<Navigation class="w-4 h-4" />
							{{ __("Navigation") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem :shortcut="['Alt', '1']" :description="__('Go to POS')" />
							<ShortcutItem :shortcut="['Alt', '2']" :description="__('Go to Orders')" />
							<ShortcutItem
								:shortcut="['Alt', '3']"
								:description="__('Go to Purchase Order')"
							/>
							<ShortcutItem
								:shortcut="['Alt', '4']"
								:description="__('Go to Purchase Invoice')"
							/>
							<ShortcutItem
								:shortcut="['Alt', '5']"
								:description="__('Go to Stock Receiving')"
							/>
							<ShortcutItem :shortcut="['Alt', '6']" :description="__('Go to Expenses')" />
							<ShortcutItem :shortcut="['Alt', '7']" :description="__('Go to Bank Drops')" />
						</div>
					</div>

					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<ShoppingCart class="w-4 h-4" />
							{{ __("POS Actions") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem :shortcut="['F1']" :description="__('Focus Barcode Input')" />
							<ShortcutItem :shortcut="['F2']" :description="__('Focus Search Input')" />
							<ShortcutItem :shortcut="['F4']" :description="__('Process Payment')" />
							<ShortcutItem
								:shortcut="['F5']"
								:description="__('Toggle Item View (Grid/List)')"
							/>
							<ShortcutItem :shortcut="['F6']" :description="__('Select Customer')" />
							<ShortcutItem
								:shortcut="['F8']"
								:description="__('Toggle Held/Draft Invoices')"
							/>
							<ShortcutItem
								:shortcut="['Ctrl', 'G']"
								:description="__('Repeat Last Invoice')"
							/>
							<ShortcutItem :shortcut="['Ctrl', 'R']" :description="__('Return Invoice')" />
							<ShortcutItem :shortcut="['Ctrl', 'P']" :description="__('Print Last Receipt')" />
							<ShortcutItem :shortcut="['Ctrl', 'D']" :description="__('Apply Discount')" />
							<ShortcutItem
								:shortcut="['Ctrl', 'H']"
								:description="__('Hold / Park Invoice')"
							/>
						</div>
					</div>

					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<Package class="w-4 h-4" />
							{{ __("Item Selection") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem :shortcut="['↑', '↓']" :description="__('Navigate Items')" />
							<ShortcutItem
								:shortcut="['Enter']"
								:description="__('Add Selected Item to Cart')"
							/>
							<ShortcutItem :shortcut="['Type any letter']" :description="__('Start Search')" />
						</div>
					</div>

					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<List class="w-4 h-4" />
							{{ __("Cart Actions") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem
								:shortcut="['Delete']"
								:description="__('Remove Selected Item from Cart')"
							/>
							<ShortcutItem
								:shortcut="['Ctrl', 'Delete']"
								:description="__('Clear All Items from Cart')"
							/>
							<ShortcutItem
								:shortcut="['+', '-']"
								:description="__('Increase/Decrease Quantity (in cart)')"
							/>
						</div>
					</div>

					<div>
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<Clock class="w-4 h-4" />
							{{ __("Shift Management") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem
								:shortcut="['Ctrl', 'Shift', 'O']"
								:description="__('Close Shift')"
							/>
							<ShortcutItem :shortcut="['Ctrl', 'E']" :description="__('Cash Expense')" />
							<ShortcutItem
								:shortcut="['Ctrl', 'Shift', 'D']"
								:description="__('Cash Deposit')"
							/>
						</div>
					</div>

					<div v-if="isElectronEnv">
						<h3 class="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
							<RefreshCw class="w-4 h-4" />
							{{ __("Data Sync") }}
						</h3>
						<div class="space-y-1.5">
							<ShortcutItem
								:shortcut="['Ctrl', 'Shift', 'S']"
								:description="__('Trigger Manual Sync')"
							/>
						</div>
					</div>
				</div>
			</ScrollArea>

			<DialogFooter>
				<Button variant="outline" @click="$emit('close')">
					{{ __("Close") }}
				</Button>
			</DialogFooter>
		</DialogContent>
	</Dialog>
</template>

<script setup lang="ts">
import { h } from "vue";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
	DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { isElectron } from "@/services/electronBridge";
import { __ } from "@/lib/translate";
import {
	Keyboard,
	Monitor,
	Navigation,
	ShoppingCart,
	Package,
	List,
	Clock,
	RefreshCw,
} from "lucide-vue-next";

defineProps<{
	open: boolean;
}>();

defineEmits<{
	close: [];
}>();

const isElectronEnv = isElectron();

const ShortcutItem = (props: { shortcut: string[]; description: string }) => {
	return h("div", { class: "flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/50" }, [
		h("span", { class: "text-sm text-muted-foreground" }, props.description),
		h(
			"div",
			{ class: "flex items-center gap-1" },
			props.shortcut.map((key, index) =>
				h(
					"span",
					{
						key: index,
						class: "inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 text-xs font-medium bg-muted border border-border rounded",
					},
					key,
				),
			),
		),
	]);
};
</script>
