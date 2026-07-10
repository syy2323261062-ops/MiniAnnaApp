export interface AnnaStorageApi {
  get<T = unknown>(request: { key: string }): Promise<{ value?: T | null }>;
  set<T = unknown>(request: { key: string; value: T }): Promise<unknown>;
}

export interface AnnaToolsApi {
  invoke<T = unknown>(request: {
    tool_id: string;
    method: string;
    args: Record<string, unknown>;
  }): Promise<T>;
}

export interface AnnaClient {
  storage: AnnaStorageApi;
  tools: AnnaToolsApi;
}

declare global {
  interface Window {
    __ANNA_TOOL_IDS__?: Record<string, string>;
  }
}

