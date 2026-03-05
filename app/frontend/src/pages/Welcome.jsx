export default function Welcome({ onNext }) {
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
        <div className="cta-row">
          <button className="btn-primary" onClick={onNext}>Start New Triage</button>
        </div>
      </section>
    </main>
  );
}
