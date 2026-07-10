import type { Note } from "./storage";
import type { AnnaClient } from "./types";

export const EXECUTA_HANDLE = "mini-notes-summary";
export const DEV_TOOL_ID = "tool-test-mini-notes-summary-12345678";
export const TOOL_METHOD = "summarize_notes";

interface SummaryPayload {
  summary?: unknown;
}

interface InvokeEnvelope {
  data?: SummaryPayload;
  summary?: unknown;
}

function resolveToolId(): string {
  return window.__ANNA_TOOL_IDS__?.[EXECUTA_HANDLE] || DEV_TOOL_ID;
}

export async function summarizeNotes(
  anna: AnnaClient,
  notes: Note[],
): Promise<string> {
  const response = await anna.tools.invoke<InvokeEnvelope>({
    tool_id: resolveToolId(),
    method: TOOL_METHOD,
    args: {
      notes: notes.map(({ id, order, content }) => ({ id, order, content })),
    },
  });

  const summary = response?.data?.summary ?? response?.summary;
  if (typeof summary !== "string" || !summary.trim()) {
    throw new Error("Executa returned no summary text.");
  }
  return summary.trim();
}

