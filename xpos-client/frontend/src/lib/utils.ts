import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// Re-export translate function for convenience
export { __, _lt, format, hasTranslation } from "./translate";
