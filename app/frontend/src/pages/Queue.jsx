import { useCallback, useEffect, useRef, useState } from "react";

import { getTriageQueue, getTriageSession } from "../api/client";

const LEVEL_LABELS = {
  RED: "Urgent review now",
  ORANGE: "Prompt same-day review",
  GREEN: "Lower immediate risk",
};

// New kiosk arrivals show up without anyone pressing Refresh.
const AUTO_REFRESH_MS = 20000;

// SQLite CURRENT_TIMESTAMP is UTC without a zone marker.
function parseUtc(value) {
  return value ? new Date(`${value.replace(" ", "T")}Z`) : null;
}

function formatTime(value) {
  const date = parseUtc(value);
  return date ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "unknown time";
}

function waitingFor(value, now) {
  const date = parseUtc(value);
  if (!date) return "";
  const minutes = Math.max(0, Math.floor((now - date.getTime()) / 60000));
  if (minutes < 1) return "Just arrived";
  if (minutes < 60) return `Waiting ${minutes} min`;
  return `Waiting ${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

function shortComplaint(text) {
  if (!text) return "No complaint recorded";
  return text.length > 110 ? `${text.slice(0, 110)}...` : text;
}

export default function Queue({ staff, notice, onBack, onLogout, onAuthExpired, onOpenSummary }) {
  const [tab, setTab] = useState("waiting");
  const [waiting, setWaiting] = useState([]);
  const [seen, setSeen] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [now, setNow] = useState(Date.now());
  // Kept in a ref so a new callback from the parent doesn't restart the refresh timer.
  const authExpiredRef = useRef(onAuthExpired);
  authExpiredRef.current = onAuthExpired;

  const loadQueue = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    setError("");
    try {
      const [waitingItems, seenItems] = await Promise.all([
        getTriageQueue(100, "waiting"),
        getTriageQueue(50, "done"),
      ]);
      setWaiting(waitingItems);
      setSeen(seenItems);
      setNow(Date.now());
    } catch (e) {
      if (e?.status === 401) return authExpiredRef.current();
      setError(e instanceof Error ? e.message : "Could not load queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
    const timer = setInterval(() => loadQueue(true), AUTO_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadQueue]);

  async function openSummary(sessionId) {
    setError("");
    try {
      onOpenSummary(await getTriageSession(sessionId));
    } catch (e) {
      if (e?.status === 401) return onAuthExpired();
      setError(e instanceof Error ? e.message : "Could not open summary.");
    }
  }

  const items = tab === "waiting" ? waiting : seen;

  return (
    <main className="shell">
      <section className="card queue-card">
        <div className="queue-head">
          <div>
            <span className="tag">Clinician Queue</span>
            <h2 className="section-title">Patients</h2>
            <p className="muted-line">
              Most urgent first, then whoever has waited longest. Logged in as {staff?.display_name}.
            </p>
          </div>
          <div className="cta-row">
            <button className="btn-secondary" onClick={() => loadQueue()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <button className="btn-secondary" onClick={onBack}>Back</button>
            <button className="btn-secondary" onClick={onLogout}>Log Out</button>
          </div>
        </div>

        {notice && <p className="queue-notice" role="status">{notice}</p>}

        <div className="queue-toolbar">
          <div className="queue-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={tab === "waiting"}
              className={`queue-tab ${tab === "waiting" ? "active" : ""}`}
              onClick={() => setTab("waiting")}
            >
              Waiting <span className="count">{waiting.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={tab === "done"}
              className={`queue-tab ${tab === "done" ? "active" : ""}`}
              onClick={() => setTab("done")}
            >
              Seen <span className="count">{seen.length}</span>
            </button>
          </div>
          {waiting.length > 0 && (
            <button className="btn-primary" onClick={() => openSummary(waiting[0].session_id)}>
              Call Next Patient: {waiting[0].patient_name || "Unnamed"} ({waiting[0].triage_level})
            </button>
          )}
        </div>

        {error && <p className="error-text">{error}</p>}
        {loading && !items.length && <p className="muted-line">Loading queue...</p>}

        {!loading && !items.length && (
          <p className="muted-line">
            {tab === "waiting" ? "Nobody is waiting. All patients have been seen." : "No patients marked as seen yet."}
          </p>
        )}

        <div className="queue-list">
          {items.map((item, index) => (
            <article
              key={item.session_id}
              className={`queue-item level-${item.triage_level.toLowerCase()} ${item.status === "done" ? "is-done" : ""}`}
            >
              <div className="queue-main">
                <span className="queue-level">{item.triage_level}</span>
                <div>
                  <h3>
                    {tab === "waiting" && <span className="queue-position">#{index + 1}</span>}
                    {item.patient_name || "Unnamed patient"}
                  </h3>
                  <p>{shortComplaint(item.chief_complaint_text)}</p>
                  <div className="queue-meta">
                    <span>{LEVEL_LABELS[item.triage_level]}</span>
                    {item.status === "done" ? (
                      <span>Seen by {item.completed_by || "staff"} at {formatTime(item.completed_at)}</span>
                    ) : (
                      <span className="queue-wait">{waitingFor(item.arrived_at || item.created_at, now)}</span>
                    )}
                    <span>Arrived {formatTime(item.arrived_at || item.created_at)}</span>
                    <span>Session {item.session_id}</span>
                    {item.entered_by && <span>Entered by {item.entered_by}</span>}
                  </div>
                </div>
              </div>
              <button className={tab === "waiting" ? "btn-primary" : "btn-secondary"} onClick={() => openSummary(item.session_id)}>
                Open Summary
              </button>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
