const API_BASE = "http://localhost:8000";

export async function postTriage(payload) {
  const r = await fetch(`${API_BASE}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    let detail = "";
    try {
      detail = await r.text();
    } catch {
      detail = "";
    }
    throw new Error(detail || `Triage failed (${r.status})`);
  }
  return r.json();
}

export async function postPdf(payload) {
  const r = await fetch(`${API_BASE}/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error("PDF failed");
  return r.blob();
}

export async function getTriageQueue(limit = 50) {
  const r = await fetch(`${API_BASE}/triage?limit=${limit}`);
  if (!r.ok) throw new Error("Queue fetch failed");
  return r.json();
}

export async function getTriageSession(sessionId) {
  const r = await fetch(`${API_BASE}/triage/${sessionId}`);
  if (!r.ok) throw new Error("Session fetch failed");
  return r.json();
}

export async function postSpeech(text) {
  const r = await fetch(`${API_BASE}/speech`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!r.ok) throw new Error("Speech failed");
  return r.blob();
}
