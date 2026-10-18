import { useEffect, useState } from "react";

import { getTriageQueue, getTriageSession } from "../api/client";

const LEVEL_LABELS = {
  RED: "Urgent review now",
  ORANGE: "Prompt same-day review",
  GREEN: "Lower immediate risk",
};

function formatDate(value) {
  if (!value) return "Unknown time";
  return new Date(`${value}Z`).toLocaleString();
}

function shortComplaint(text) {
  if (!text) return "No complaint recorded";
  return text.length > 110 ? `${text.slice(0, 110)}...` : text;
}

export default function Queue({ staff, onBack, onLogout, onAuthExpired, onOpenSummary }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadQueue() {
    setError("");
    setLoading(true);
    try {
      setItems(await getTriageQueue());
    } catch (e) {
      if (e?.status === 401) return onAuthExpired();
      const msg = e instanceof Error ? e.message : "Could not load queue.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function openSummary(sessionId) {
    setError("");
    try {
      const log = await getTriageSession(sessionId);
      onOpenSummary(log.request_payload, log.response_payload);
    } catch (e) {
      if (e?.status === 401) return onAuthExpired();
      const msg = e instanceof Error ? e.message : "Could not open summary.";
      setError(msg);
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  return (
    <main className="shell">
      <section className="card queue-card">
        <div className="queue-head">
          <div>
            <span className="tag">Clinician Queue</span>
            <h2 className="section-title">Recent Patients</h2>
            <p className="muted-line">Sorted by RED, ORANGE, GREEN, then newest first. Logged in as {staff?.display_name}.</p>
          </div>
          <div className="cta-row">
            <button className="btn-secondary" onClick={loadQueue} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
            <button className="btn-secondary" onClick={onBack}>Back</button>
            <button className="btn-secondary" onClick={onLogout}>Log Out</button>
          </div>
        </div>

        {error && <p className="error-text">{error}</p>}
        {loading && <p className="muted-line">Loading queue...</p>}

        {!loading && !items.length && (
          <p className="muted-line">No triage sessions have been logged yet.</p>
        )}

        <div className="queue-list">
          {items.map((item) => (
            <article key={item.session_id} className={`queue-item level-${item.triage_level.toLowerCase()}`}>
              <div className="queue-main">
                <span className="queue-level">{item.triage_level}</span>
                <div>
                  <h3>{item.patient_name || "Unnamed patient"}</h3>
                  <p>{shortComplaint(item.chief_complaint_text)}</p>
                  <div className="queue-meta">
                    <span>{LEVEL_LABELS[item.triage_level]}</span>
                    <span>{formatDate(item.created_at)}</span>
                    <span>Session {item.session_id}</span>
                    {item.entered_by && <span>Entered by {item.entered_by}</span>}
                  </div>
                </div>
              </div>
              <button className="btn-primary" onClick={() => openSummary(item.session_id)}>
                Open Summary
              </button>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
