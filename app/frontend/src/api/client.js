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
