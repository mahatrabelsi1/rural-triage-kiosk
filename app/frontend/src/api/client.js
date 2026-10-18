const API_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "triage-staff-session";

// Staff session lives in sessionStorage so closing the browser logs out.
// Storage can be unavailable (private mode, kiosk lockdown), so never rely on it.
export function loadStaffSession() {
  try {
    const raw = window.sessionStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);
    if (!session?.token || session.expires_at * 1000 < Date.now()) return null;
    return session;
  } catch {
    return null;
  }
}

export function saveStaffSession(session) {
  try {
    if (session) window.sessionStorage.setItem(TOKEN_KEY, JSON.stringify(session));
    else window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore: session simply won't survive a reload
  }
}

let staffToken = loadStaffSession()?.token || "";

export function setStaffToken(token) {
  staffToken = token || "";
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function readError(r, fallback) {
  try {
    const body = await r.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) return body.detail.map((d) => d.msg).join("; ");
  } catch {
    // not JSON
  }
  return fallback;
}

async function request(path, { method = "GET", body, auth = false, as = "json", fallback } = {}) {
  const headers = {};
  if (body !== undefined && !(body instanceof Blob)) headers["Content-Type"] = "application/json";
  if (body instanceof Blob) headers["Content-Type"] = body.type || "application/octet-stream";
  if (auth && staffToken) headers.Authorization = `Bearer ${staffToken}`;

  let r;
  try {
    r = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : body instanceof Blob ? body : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the kiosk server. Check that the backend is running.", 0);
  }
  if (!r.ok) {
    const message = r.status === 401 && auth ? "Your staff login has expired. Please log in again." : await readError(r, fallback || `Request failed (${r.status})`);
    throw new ApiError(message, r.status);
  }
  return as === "blob" ? r.blob() : r.json();
}

export function login(username, password) {
  return request("/auth/login", { method: "POST", body: { username, password }, fallback: "Login failed" });
}

export function postTriage(payload) {
  return request("/triage", { method: "POST", body: payload, fallback: "Triage failed" });
}

export function downloadPdf(sessionId) {
  return request(`/pdf/${encodeURIComponent(sessionId)}`, { auth: true, as: "blob", fallback: "PDF failed" });
}

// status: "waiting" (default), "done" (seen), or "all"
export function getTriageQueue(limit = 50, status = "waiting") {
  return request(`/triage?limit=${limit}&status=${status}`, { auth: true, fallback: "Queue fetch failed" });
}

export function completeSession(sessionId) {
  return request(`/triage/${encodeURIComponent(sessionId)}/complete`, { method: "POST", auth: true, fallback: "Could not mark as seen" });
}

export function reopenSession(sessionId) {
  return request(`/triage/${encodeURIComponent(sessionId)}/reopen`, { method: "POST", auth: true, fallback: "Could not reopen" });
}

export function getTriageSession(sessionId) {
  return request(`/triage/${encodeURIComponent(sessionId)}`, { auth: true, fallback: "Session fetch failed" });
}

export function postSpeech(text) {
  return request("/speech", { method: "POST", body: { text }, as: "blob", fallback: "Speech failed" });
}

export function postTranscription(wavBlob) {
  return request("/speech/transcribe", { method: "POST", body: wavBlob, fallback: "Transcription failed" });
}
