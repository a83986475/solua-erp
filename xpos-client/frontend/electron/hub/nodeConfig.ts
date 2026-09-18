export type NodeRole = "hub" | "till";

export interface HubConfig {
	role: "hub";
	erpnextUrl: string;
	hubApiPort: number;
}

export interface TillConfig {
	role: "till";
	hubUrl: string;
	tillId: string;
}

export type NodeConfig = HubConfig | TillConfig;

export const DEFAULT_HUB_PORT = 6789;

export function getDefaultConfig(): HubConfig {
	return {
		role: "hub",
		erpnextUrl: process.env.XPOS_SERVER_URL || "http://localhost:8000",
		hubApiPort: DEFAULT_HUB_PORT,
	};
}
