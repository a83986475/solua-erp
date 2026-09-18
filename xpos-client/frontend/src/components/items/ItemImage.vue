<template>
	<img
		v-if="resolvedSrc"
		:src="resolvedSrc"
		:alt="alt"
		:class="className"
		loading="lazy"
		@error="handleError"
	/>
	<slot v-else />
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { isElectron } from "@/services/electronBridge";
import { get_full_url } from "@/utils";

const props = withDefaults(
	defineProps<{
		source?: string;
		alt?: string;
		className?: string;
	}>(),
	{ source: "", alt: "" },
);

const resolvedSrc = ref("");
let loadSequence = 0;

async function resolveSource(): Promise<void> {
	const sequence = ++loadSequence;
	resolvedSrc.value = "";
	if (!props.source) return;

	if (isElectron() && window.electronAPI?.loadImage) {
		const cached = await window.electronAPI.loadImage(props.source).catch(() => null);
		if (sequence !== loadSequence) return;
		if (cached) {
			resolvedSrc.value = cached;
			return;
		}
	}

	if (sequence === loadSequence) resolvedSrc.value = get_full_url(props.source);
}

function handleError(): void {
	resolvedSrc.value = "";
}

watch(() => props.source, resolveSource);
onMounted(resolveSource);
</script>
