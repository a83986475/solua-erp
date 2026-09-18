import { call } from "@/services/api";
import { getSetting, setSetting } from "@/services/dbBridge";
import { isOnline } from "@/utils";

const LANGUAGE_KEY = "ui_language";
const MESSAGE_KEY = "ui_messages_";
const DEFAULT_LANGUAGE = "en";

export const languages = [
	{ value: "en", label: "English" },
	{ value: "zh", label: "Chinese" },
	{ value: "pt", label: "Portuguese" },
] as const;

function isSupportedLanguage(value: string): boolean {
	return languages.some((language) => language.value === value);
}

function readMessages(raw: string | null): Record<string, string> {
	if (!raw) return {};
	try {
		const parsed = JSON.parse(raw);
		return parsed && typeof parsed === "object" ? (parsed as Record<string, string>) : {};
	} catch {
		return {};
	}
}

function apply(language: string, messages: Record<string, string>): void {
	window.xpos = window.xpos || {};
	window.xpos._messages = messages;
	document.documentElement.lang = language;
}

export async function getLanguage(): Promise<string> {
	try {
		const stored = await getSetting(LANGUAGE_KEY);
		return stored && isSupportedLanguage(stored) ? stored : DEFAULT_LANGUAGE;
	} catch {
		return DEFAULT_LANGUAGE;
	}
}

export async function loadLanguage(): Promise<void> {
	const language = await getLanguage();
	let messages: Record<string, string> = {};
	try {
		messages = readMessages(await getSetting(MESSAGE_KEY + language));
	} catch {
		/* The English source strings remain the safe fallback. */
	}
	apply(language, messages);
}

export async function setLanguage(language: string): Promise<void> {
	if (!isSupportedLanguage(language)) return;

	let messages: Record<string, string> = {};
	if (language !== DEFAULT_LANGUAGE) {
		try {
			messages = readMessages(await getSetting(MESSAGE_KEY + language));
		} catch {
			/* Continue with the cached/English fallback. */
		}

		if (isOnline()) {
			try {
				const remote = await call<Record<string, string>>(
					"xpos.api.settings.get_xpos_translations",
					{ language },
				);
				if (remote && typeof remote === "object") {
					messages = remote;
					await setSetting(MESSAGE_KEY + language, JSON.stringify(messages), "language");
				}
			} catch (error) {
				console.warn(`[XPOS] Translation refresh failed for ${language}; using cached messages`, error);
			}
		}
	}

	try {
		await setSetting(LANGUAGE_KEY, language, "language");
	} catch (error) {
		console.warn("[XPOS] Could not persist language selection", error);
	}
	apply(language, messages);
}
