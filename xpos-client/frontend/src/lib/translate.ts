/**
 * Translation utility for frappe boot translations
 * Uses window.xpos._messages from frappe's boot data
 */

type TranslateArgs = (string | number)[];

/**
 * Get the translations dictionary from boot data
 */
function getMessages(): Record<string, string> {
	return window.xpos?._messages || {};
}

/**
 * Translate a string using frappe's boot translations
 * Supports format arguments like {0}, {1}, etc.
 *
 * @param txt - The text to translate
 * @param args - Optional format arguments for string interpolation
 * @returns Translated string or original if no translation found
 */
export function __(txt: string, args?: TranslateArgs): string {
	if (!txt) return txt;

	const messages = getMessages();
	let translated = messages[txt] || txt;

	// Handle string interpolation with {0}, {1}, etc.
	if (args && args.length > 0) {
		translated = translated.replace(/\{(\d+)\}/g, (match, index) => {
			const argIndex = parseInt(index, 10);
			return argIndex < args.length ? String(args[argIndex]) : match;
		});
	}

	return translated;
}

/**
 * Alias for __ function - matches frappe's _lt convention for lazy translation
 */
export const _lt = __;

/**
 * Format a string with arguments without translation lookup
 * Useful when you have already translated text but need interpolation
 *
 * @param txt - The text to format
 * @param args - Format arguments
 */
export function format(txt: string, args: TranslateArgs): string {
	if (!txt || !args || args.length === 0) return txt;

	return txt.replace(/\{(\d+)\}/g, (match, index) => {
		const argIndex = parseInt(index, 10);
		return argIndex < args.length ? String(args[argIndex]) : match;
	});
}

/**
 * Check if a translation exists for the given text
 * @param txt - The text to check
 */
export function hasTranslation(txt: string): boolean {
	const messages = getMessages();
	return txt in messages;
}

/**
 * Get all available translations (for debugging)
 */
export function getAllTranslations(): Record<string, string> {
	return { ...getMessages() };
}

// Default export for convenience
export default __;
