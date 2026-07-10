import { FormEvent, useEffect, useState } from "react";
import { connectAnna } from "./anna/runtime";
import {
  addNote,
  loadNotes,
  removeNote,
  type Note,
} from "./anna/storage";
import { summarizeNotes } from "./anna/tools";
import type { AnnaClient } from "./anna/types";
import "./styles.css";

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function App() {
  const [anna, setAnna] = useState<AnnaClient | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState("");
  const [summary, setSummary] = useState("");
  const [status, setStatus] = useState("Connecting to Anna…");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const client = await connectAnna();
        const stored = await loadNotes(client);
        if (!active) return;
        setAnna(client);
        setNotes(stored.notes);
        setStatus("Connected");
      } catch (cause) {
        if (!active) return;
        setStatus("Connection failed");
        setError(messageFrom(cause));
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!anna || !draft.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const stored = await addNote(anna, draft);
      setNotes(stored.notes);
      setDraft("");
      setSummary("");
    } catch (cause) {
      setError(messageFrom(cause));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(noteId: string) {
    if (!anna || busy) return;
    setBusy(true);
    setError("");
    try {
      const stored = await removeNote(anna, noteId);
      setNotes(stored.notes);
      setSummary("");
    } catch (cause) {
      setError(messageFrom(cause));
    } finally {
      setBusy(false);
    }
  }

  async function onSummarize() {
    if (!anna || busy) return;
    setBusy(true);
    setError("");
    setSummary("");
    try {
      const stored = await loadNotes(anna);
      setNotes(stored.notes);
      if (!stored.notes.length) throw new Error("Add at least one note first.");
      setSummary(await summarizeNotes(anna, stored.notes));
    } catch (cause) {
      setError(messageFrom(cause));
    } finally {
      setBusy(false);
    }
  }

  const canWrite = Boolean(anna) && !busy;

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Anna App</p>
          <h1>Mini Notes</h1>
          <p className="subtitle">Capture a thought, then summarize the list through Executa.</p>
        </div>
        <span className={`connection ${anna ? "connected" : ""}`}>{status}</span>
      </header>

      <form className="note-form" onSubmit={onSubmit}>
        <label htmlFor="note-content">New note</label>
        <div className="composer">
          <textarea
            id="note-content"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="What do you want to remember?"
            rows={3}
            disabled={!canWrite}
          />
          <button type="submit" disabled={!canWrite || !draft.trim()}>
            Add note
          </button>
        </div>
      </form>

      {error && <div className="message error" role="alert">{error}</div>}

      <section className="notes-section" aria-labelledby="notes-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Stored through anna.storage</p>
            <h2 id="notes-title">Notes</h2>
          </div>
          <span>{notes.length} total</span>
        </div>

        {notes.length === 0 ? (
          <p className="empty-state">No notes yet. Add the first one above.</p>
        ) : (
          <ol className="notes-list">
            {notes.map((note) => (
              <li key={note.id}>
                <span className="order">{note.order}</span>
                <p>{note.content}</p>
                <button
                  className="delete-button"
                  type="button"
                  onClick={() => void onDelete(note.id)}
                  disabled={busy}
                  aria-label={`Delete note ${note.order}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="summary-section" aria-labelledby="summary-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">anna.tools.invoke → summarize_notes</p>
            <h2 id="summary-title">Summary</h2>
          </div>
          <button
            type="button"
            onClick={() => void onSummarize()}
            disabled={!anna || busy || notes.length === 0}
          >
            {busy ? "Working…" : "Summarize"}
          </button>
        </div>
        <p className={summary ? "summary-output" : "summary-output muted"}>
          {summary || "Your Executa-generated summary will appear here."}
        </p>
      </section>
    </main>
  );
}

