<script setup lang="ts">
import { cn } from "@/lib/utils";
import { TooltipContent, type TooltipContentProps, TooltipPortal } from "radix-vue";
import { computed, type HTMLAttributes } from "vue";

const props = withDefaults(defineProps<TooltipContentProps & { class?: HTMLAttributes["class"] }>(), {
	sideOffset: 6,
});

const delegatedProps = computed(() => {
	const { class: _, ...delegated } = props;
	return delegated;
});
</script>

<template>
	<TooltipPortal>
		<TooltipContent
			v-bind="delegatedProps"
			:class="
				cn(
					// Layout & shape
					'z-50 overflow-hidden rounded-lg select-none',
					// Dark glass style
					'border border-white/10 bg-gray-900/95 backdrop-blur-sm',
					'px-3 py-2 text-xs font-medium leading-snug tracking-wide text-gray-50',
					// Depth
					'shadow-xl shadow-black/30 ring-1 ring-black/10',
					// GPU-composited enter animation (150 ms)
					'transform-gpu',
					'animate-in fade-in-0 zoom-in-95 duration-150 ease-out',
					// Fast exit (100 ms)
					'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=closed]:duration-100',
					// Directional slide-in
					'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
					props.class,
				)
			"
		>
			<slot />
		</TooltipContent>
	</TooltipPortal>
</template>
