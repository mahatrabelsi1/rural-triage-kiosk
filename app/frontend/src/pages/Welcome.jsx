const ENTRY_OPTIONS = [
  {
    id: "patient",
    title: "I am the patient",
    text: "Answer a few simple questions about how you feel.",
  },
  {
    id: "companion",
    title: "I am with the patient",
    text: "Family member, friend or carer answering for the patient.",
  },
  {
    id: "nurse",
    title: "Nurse entering for the patient",
    text: "Use when the patient is alone and cannot use the kiosk.",
  },
];

export default function Welcome({ staff, onStart, onQueue }) {
  return (
    <main className="shell">
      <section className="card hero">
        <span className="tag">Rural Clinic Check-In</span>
        <h1>Welcome. Let us check how you are feeling.</h1>
        <p>
          This kiosk asks a few questions so the clinic can see the most urgent patients first.
          You can type or press the microphone to speak your answers.
        </p>
        <p className="notice emergency-notice" role="note">
          If someone is not breathing, unconscious, or bleeding heavily, call the nurse now. Do not wait for the kiosk.
        </p>

        <div>
          <h2 className="section-title">Who is filling in this form?</h2>
          <div className="entry-grid">
            {ENTRY_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`entry-card entry-${option.id}`}
                onClick={() => onStart(option.id)}
              >
                <strong>{option.title}</strong>
                <span>{option.text}</span>
              </button>
            ))}
          </div>
        </div>

        <p className="notice">
          This tool helps the clinic decide who to see first. It does not give a diagnosis.
        </p>

        <div className="staff-entry">
          <span className="muted-line">Clinic staff</span>
          <button type="button" className="btn-secondary" onClick={onQueue}>
            {staff ? `Open Clinic Queue (${staff.display_name})` : "Staff Login"}
          </button>
        </div>
      </section>
    </main>
  );
}
