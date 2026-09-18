<template>
	<div class="flex items-center gap-2" data-testid="language-selector">
		<label for="xpos-language" class="text-xs text-muted-foreground">{{ __("Language") }}</label>
		<select
			id="xpos-language"
			:value="language"
			:disabled="isChanging"
			class="h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground"
			data-testid="language-select"
			@change="changeLanguage"
		>
			<option v-for="option in languages" :key="option.value" :value="option.value">
				{{ option.label }}
			</option>
		</select>
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import __ from "@/lib/translate";
import { getLanguage, languages, setLanguage } from "@/lib/locale";

const language = ref("en");
const isChanging = ref(false);

onMounted(async () => {
	language.value = await getLanguage();
});

async function changeLanguage(event: Event): Promise<void> {
	const next = (event.target as HTMLSelectElement).value;
	const previous = language.value;
	language.value = next;
	isChanging.value = true;
	try {
		await setLanguage(next);
		window.location.reload();
	} catch (error) {
		language.value = previous;
		console.error("[XPOS] Language switch failed", error);
	} finally {
		isChanging.value = false;
	}
}
</script>
