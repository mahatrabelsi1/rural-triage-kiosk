export default function Welcome({ role, onRoleChange, onNext, onQueue }) {
  return (
    <main className="shell">
      <section className="card hero">
        <span className="tag">Rural Triage Kiosk</span>
        <h1>Fast, Clear Patient Prioritization For Clinic Intake</h1>
        <p>
          This medical triage assistant helps staff capture key patient details,
          symptom severity, and urgency level before doctor review.
        </p>
        <p className="notice">
          Safety: This tool supports prioritization only. It does not provide diagnosis.
        </p>

        <div>
          <label>Current role</label>
          <div className="role-switcher">
            <button
              type="button"
              className={`btn-secondary ${role === "intake" ? "btn-choice-active" : ""}`}
              onClick={() => onRoleChange("intake")}
            >
              Intake Staff
            </button>
            <button
              type="button"
              className={`btn-secondary ${role === "clinician" ? "btn-choice-active" : ""}`}
              onClick={() => onRoleChange("clinician")}
            >
              Clinician
            </button>
          </div>
        </div>

        <div className="cta-row">
          {role === "intake" ? (
            <button className="btn-primary" onClick={onNext}>Start New Triage</button>
          ) : (
            <>
              <button className="btn-primary" onClick={onQueue}>Open Clinic Queue</button>
              <button className="btn-secondary" onClick={onNext}>Start New Triage</button>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
