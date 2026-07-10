import type { AnnaClient } from "./types";

const RUNTIME_SDK_URL = "/static/anna-apps/_sdk/latest/index.js";

interface AnnaRuntimeModule {
  AnnaAppRuntime: {
    connect(): Promise<AnnaClient>;
  };
}

let connection: Promise<AnnaClient> | null = null;

export function connectAnna(): Promise<AnnaClient> {
  if (!connection) {
    connection = import(/* @vite-ignore */ RUNTIME_SDK_URL).then(
      (runtime: AnnaRuntimeModule) => runtime.AnnaAppRuntime.connect(),
    );
  }
  return connection;
}

