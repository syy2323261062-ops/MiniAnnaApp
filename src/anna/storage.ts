import type { AnnaClient } from "./types";

export const STORAGE_KEY = "mini-notes:notes:v1";

export interface Note {
  id: string;
  content: string;
  order: number;
}

export interface NotesStorageValue {
  version: 1;
  nextOrder: number;
  notes: Note[];
}

function emptyStorageValue(): NotesStorageValue {
  return { version: 1, nextOrder: 1, notes: [] };
}

function isNote(value: unknown): value is Note {
  if (!value || typeof value !== "object") return false;
  const note = value as Partial<Note>;
  return (
    typeof note.id === "string" &&
    typeof note.content === "string" &&
    Number.isInteger(note.order) &&
    (note.order ?? 0) > 0
  );
}

function normalizeStorageValue(value: unknown): NotesStorageValue {
  if (value == null) return emptyStorageValue();
  if (!value || typeof value !== "object") {
    throw new Error("Stored notes value is not an object.");
  }

  const candidate = value as Partial<NotesStorageValue>;
  if (
    candidate.version !== 1 ||
    !Number.isInteger(candidate.nextOrder) ||
    (candidate.nextOrder ?? 0) < 1 ||
    !Array.isArray(candidate.notes) ||
    !candidate.notes.every(isNote)
  ) {
    throw new Error("Stored notes value does not match schema version 1.");
  }

  const notes = [...candidate.notes].sort((left, right) => left.order - right.order);
  const highestOrder = notes.reduce((highest, note) => Math.max(highest, note.order), 0);
  if ((candidate.nextOrder ?? 0) <= highestOrder) {
    throw new Error("Stored notes nextOrder must be greater than every note order.");
  }

  return {
    version: 1,
    nextOrder: candidate.nextOrder as number,
    notes,
  };
}

function createNoteId(): string {
  return `note-${crypto.randomUUID()}`;
}

export async function loadNotes(anna: AnnaClient): Promise<NotesStorageValue> {
  const result = await anna.storage.get<unknown>({ key: STORAGE_KEY });
  return normalizeStorageValue(result?.value);
}

export async function addNote(
  anna: AnnaClient,
  rawContent: string,
): Promise<NotesStorageValue> {
  const content = rawContent.trim();
  if (!content) throw new Error("Note content cannot be empty.");

  const current = await loadNotes(anna);
  const next: NotesStorageValue = {
    version: 1,
    nextOrder: current.nextOrder + 1,
    notes: [
      ...current.notes,
      { id: createNoteId(), content, order: current.nextOrder },
    ],
  };
  await anna.storage.set({ key: STORAGE_KEY, value: next });
  return next;
}

export async function removeNote(
  anna: AnnaClient,
  noteId: string,
): Promise<NotesStorageValue> {
  const current = await loadNotes(anna);
  const next: NotesStorageValue = {
    ...current,
    notes: current.notes.filter((note) => note.id !== noteId),
  };
  await anna.storage.set({ key: STORAGE_KEY, value: next });
  return next;
}

