import { useState } from "react";

import { login } from "../api/client";

export default function Login({ onBack, onLoggedIn }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      onLoggedIn(await login(username.trim(), password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="card login-card">
        <span className="tag">Clinic Staff</span>
        <h2 className="section-title">Staff Login</h2>
        <p className="muted-line">
          The clinic queue and doctor PDF contain patient information, so they are only available to logged-in staff.
        </p>
        <form onSubmit={submit} className="login-form">
          <div>
            <label htmlFor="staff-username">Username</label>
            <input
              id="staff-username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label htmlFor="staff-password">Password</label>
            <input
              id="staff-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <p className="error-text" role="alert">{error}</p>}
          <div className="cta-row">
            <button type="button" className="btn-secondary" onClick={onBack}>Back</button>
            <button type="submit" className="btn-primary" disabled={loading || !username || !password}>
              {loading ? "Checking..." : "Log In"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
