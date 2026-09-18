<template>
	<div ref="rootEl" class="relative">
		<div class="relative flex items-center">
			<Search class="absolute start-3.5 w-5 h-5 text-muted-foreground pointer-events-none" />
			<Input
				v-model="localSearch"
				class="ps-10 pe-10 sm:pe-14"
				:placeholder="__('Search items, scan barcode...')"
				@input="onInput"
				@keydown.enter.prevent="onEnter"
				@keydown.down.prevent="emit('navigate', 'down')"
				@keydown.up.prevent="emit('navigate', 'up')"
			/>
			<Button
				v-if="localSearch"
				variant="ghost"
				size="icon-sm"
				class="absolute end-3"
				@click="clearSearch"
			>
				<X class="w-4 h-4 text-muted-foreground" />
			</Button>
		</div>
		<div
			v-if="!localSearch"
			class="absolute end-2 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1"
		>
			<kbd
				class="px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground bg-muted rounded border border-border"
				>/</kbd
			>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { Button } from "@/components/ui/button";
import { Search, X } from "lucide-vue-next";
import Input from "../ui/input/Input.vue";
import __ from "@/lib/translate";

const emit = defineEmits(["search", "navigate", "enter"]);

const rootEl = ref<HTMLElement | null>(null);
const localSearch = ref("");
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

function getInputEl(): HTMLInputElement | null {
	return rootEl.value?.querySelector("input") || null;
}

function onInput() {
	if (debounceTimer) clearTimeout(debounceTimer);
	debounceTimer = setTimeout(() => {
		emit("search", localSearch.value);
	}, 300);
}

function onEnter() {
	if (debounceTimer) clearTimeout(debounceTimer);
	const val = localSearch.value.trim();
	emit("enter", val);
}

function clearSearch() {
	localSearch.value = "";
	emit("search", "");
	getInputEl()?.focus();
}

function focus() {
	getInputEl()?.focus();
}

function blur() {
	getInputEl()?.blur();
}

function clear() {
	localSearch.value = "";
}

function isFocused(): boolean {
	return document.activeElement === getInputEl();
}

function setValue(val: string) {
	localSearch.value = val;
}

function handleKeyboard(e: KeyboardEvent) {
	if (e.key === "/" && !isFocused()) {
		e.preventDefault();
		focus();
	}
	if (e.key === "Escape" && isFocused()) {
		clearSearch();
		blur();
	}
}

onMounted(() => {
	document.addEventListener("keydown", handleKeyboard);
});

onUnmounted(() => {
	document.removeEventListener("keydown", handleKeyboard);
});

defineExpose({ focus, blur, clear, isFocused, setValue });
</script>
