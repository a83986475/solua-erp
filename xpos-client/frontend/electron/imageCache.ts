import { app, ipcMain, net, session } from "electron";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";
import { getMeta } from "./database/dbService";
import { createLogger } from "./logger";

const log = createLogger("ImageCache");
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;

function cacheDir(): string {
	return path.join(app.getPath("userData"), "image-cache");
}

function cachePaths(url: string): { body: string; type: string } {
	const key = crypto.createHash("sha256").update(url).digest("hex");
	const root = cacheDir();
	return { body: path.join(root, `${key}.bin`), type: path.join(root, `${key}.type`) };
}

function asDataUrl(body: Buffer, contentType: string): string {
	return `data:${contentType};base64,${body.toString("base64")}`;
}

async function readCached(url: string): Promise<string | null> {
	const paths = cachePaths(url);
	try {
		const [body, type] = await Promise.all([fs.readFile(paths.body), fs.readFile(paths.type, "utf8")]);
		return asDataUrl(body, type.trim() || "application/octet-stream");
	} catch {
		return null;
	}
}

async function getServerUrl(): Promise<string> {
	const configured = await getMeta("server_url").catch(() => null);
	return (configured || process.env.XPOS_SERVER_URL || "http://localhost:8000").replace(/\/$/, "");
}

async function getAuthHeaders(serverUrl: string): Promise<Record<string, string>> {
	const apiKey = await getMeta("api_key").catch(() => null);
	const apiSecret = await getMeta("api_secret").catch(() => null);
	if (apiKey && apiSecret) {
		return { Authorization: `token ${apiKey}:${apiSecret}` };
	}

	const cookies = await session.defaultSession.cookies.get({ url: serverUrl }).catch(() => []);
	return cookies.length ? { Cookie: cookies.map((cookie) => `${cookie.name}=${cookie.value}`).join("; ") } : {};
}

function resolveImageUrl(source: string, serverUrl: string): string | null {
	if (source.startsWith("data:image/")) return source;

	const server = new URL(serverUrl);
	const resolved = new URL(source, `${server.origin}/`);
	if (resolved.protocol !== "http:" && resolved.protocol !== "https:") return null;
	if (resolved.origin !== server.origin) return null;
	return resolved.href;
}

async function download(url: string, headers: Record<string, string>): Promise<{ body: Buffer; type: string }> {
	return new Promise((resolve, reject) => {
		const request = net.request({ method: "GET", url });
		request.setHeader("Accept", "image/*");
		for (const [name, value] of Object.entries(headers)) request.setHeader(name, value);

		const chunks: Buffer[] = [];
		let bytes = 0;
		request.on("response", (response: Electron.IncomingMessage) => {
			response.on("data", (chunk: Uint8Array) => {
				const buffer = Buffer.from(chunk);
				bytes += buffer.length;
				if (bytes <= MAX_IMAGE_BYTES) chunks.push(buffer);
			});
			response.on("end", () => {
				const status = response.statusCode ?? 0;
				if (status < 200 || status >= 300) {
					reject(new Error(`HTTP ${status}`));
					return;
				}
				if (bytes > MAX_IMAGE_BYTES) {
					reject(new Error(`image exceeds ${MAX_IMAGE_BYTES} bytes`));
					return;
				}
				const header = response.headers["content-type"];
				const type = (Array.isArray(header) ? header[0] : header || "image/*").split(";", 1)[0];
				resolve({ body: Buffer.concat(chunks), type: type.startsWith("image/") ? type : "image/*" });
			});
		});
		request.on("error", reject);
		request.end();
	});
}

async function loadImage(source: string): Promise<string | null> {
	if (!source) return null;
	if (source.startsWith("data:image/")) return source;

	const serverUrl = await getServerUrl();
	const url = resolveImageUrl(source, serverUrl);
	if (!url) return null;

	if (net.isOnline()) {
		try {
			const result = await download(url, await getAuthHeaders(serverUrl));
			const paths = cachePaths(url);
			await fs.mkdir(cacheDir(), { recursive: true });
			await Promise.all([fs.writeFile(paths.body, result.body), fs.writeFile(paths.type, result.type)]);
			return asDataUrl(result.body, result.type);
		} catch (error) {
			log.warn(`Image download failed endpoint=${url} error=${error instanceof Error ? error.message : String(error)}`);
		}
	}

	return readCached(url);
}

export function registerImageCacheHandler(): void {
	ipcMain.handle("images:load", async (_event, source: string) => loadImage(source));
}
