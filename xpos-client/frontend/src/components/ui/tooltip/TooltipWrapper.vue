<script setup lang="ts">
import { TooltipArrow, TooltipProvider, TooltipTrigger } from "radix-vue";
import Tooltip from "./Tooltip.vue";
import TooltipContent from "./TooltipContent.vue";

withDefaults(
	defineProps<{
		content: string | number;
		side?: "top" | "right" | "bottom" | "left";
		delayDuration?: number;
		skipDelayDuration?: number;
	}>(),
	{
		side: "bottom",
		delayDuration: 200,
		skipDelayDuration: 100,
	},
);
</script>

<template>
	<TooltipProvider :delay-duration="delayDuration" :skip-delay-duration="skipDelayDuration">
		<Tooltip>
			<TooltipTrigger as-child>
				<slot />
			</TooltipTrigger>
			<TooltipContent :side="side">
				{{ content }}
				<TooltipArrow class="fill-gray-900" :width="8" :height="5" />
			</TooltipContent>
		</Tooltip>
	</TooltipProvider>
</template>
