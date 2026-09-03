import { postPdf } from "../api/client";

function prettyLabel(key) {
  return key.replaceAll("_", " ");
}

export default function Result({ intake, triageRes, onRestart, restartLabel = "New Patient" }) {
  const levelKey = (triageRes?.triage_level || "GREEN").toLowerCase();

  async function downloadPdf() {
    const payload = {
      session_id: triageRes.session_id,
      triage_level: triageRes.triage_level,
      patient_name: intake.patient_name,
      chief_complaint_text: intake.chief_complaint_text,
      matched_reasons: triageRes.matched_rules.map((r) => `${r.id}: ${r.reason}`),
      selected_symptoms: triageRes.selected_symptoms.map((s) => `${prettyLabel(s.symptom)} = ${s.rating}/5`),
      extracted_symptoms: (triageRes.extracted_symptoms || []).map((s) =>
        `${prettyLabel(s.symptom)} = ${s.rating}/5 (${Math.round((s.confidence || 0) * 100)}% confidence, phrase: "${s.source_phrase || "n/a"}")`
      ),
      extracted_entities: (triageRes.extracted_entities || []).map((entity) =>
        `${entity.text} (${entity.label}, ${Math.round((entity.score || 0) * 100)}% confidence)`
      ),
      advice_blocks: triageRes.advice_blocks,
      age_group: intake.age_group,
      sex: intake.sex,
      pregnant: intake.pregnant,
      chronic_illnesses: intake.chronic_illnesses,
      chronic_illnesses_other: intake.chronic_illnesses_other
    };
    const blob = await postPdf(payload);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `triage_${triageRes.session_id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const chronicLines = [
    ...(intake.chronic_illnesses || []),
    ...(intake.chronic_illnesses_other ? [intake.chronic_illnesses_other] : [])
  ];

  return (
    <main className="shell">
      <section className={`card result-card level-${levelKey}`}>
        <div className="steps">
          <span className="step-chip">1. Patient Info</span>
          <span className="step-chip">2. Symptoms</span>
          <span className="step-chip">3. Clarify</span>
          <span className="step-chip active">4. Result</span>
        </div>

        <div className="result-banner">
          <div>
            <h2 className="section-title" style={{ marginBottom: 4 }}>Triage Result</h2>
            <p className="muted-line">Session ID: {triageRes.session_id}</p>
          </div>
          <h1 className="result-level">{triageRes.triage_level}</h1>
        </div>

        <h3 className="section-title">Patient Profile</h3>
        <ul className="list">
          <li>Name: {intake.patient_name || "N/A"}</li>
          <li>Age group: {intake.age_group || "N/A"}</li>
          <li>Sex: {intake.sex || "N/A"}</li>
          <li>Pregnant: {intake.pregnant === null ? "N/A" : (intake.pregnant ? "Yes" : "No")}</li>
          <li>Chronic illnesses: {chronicLines.length ? chronicLines.join(", ") : "None declared"}</li>
        </ul>

        <h3 className="section-title">Chief Complaint</h3>
        <p className="muted-line">{intake.chief_complaint_text || "N/A"}</p>

        <h3 className="section-title">Selected Symptoms (1-5)</h3>
        <ul className="list">
          {triageRes.selected_symptoms.length ? triageRes.selected_symptoms.map((s) => (
            <li key={s.symptom}>{prettyLabel(s.symptom)}: {s.rating}/5</li>
          )) : <li>None selected</li>}
        </ul>

        <h3 className="section-title">AI Extracted From Text</h3>
        <ul className="list">
          {triageRes.extracted_symptoms?.length ? triageRes.extracted_symptoms.map((s) => (
            <li key={s.symptom}>
              {prettyLabel(s.symptom)}: {s.rating}/5
              {" "}({Math.round((s.confidence || 0) * 100)}% confidence, phrase: "{s.source_phrase || "n/a"}")
            </li>
          )) : <li>No additional symptoms extracted</li>}
        </ul>

        <h3 className="section-title">Biomedical Entities</h3>
        <ul className="list">
          {triageRes.extracted_entities?.length ? triageRes.extracted_entities.map((entity, index) => (
            <li key={`${entity.text}-${index}`}>
              {entity.text} ({entity.label}, {Math.round((entity.score || 0) * 100)}% confidence)
            </li>
          )) : <li>No biomedical entities extracted</li>}
        </ul>

        <h3 className="section-title">Matched Rule Reasons</h3>
        <ul className="list">
          {triageRes.matched_rules.length ? triageRes.matched_rules.map((r) => (
            <li key={r.id}>{r.id}: {r.reason}</li>
          )) : <li>None (GREEN default)</li>}
        </ul>

        <h3 className="section-title">Guidance / Advice</h3>
        <ul className="list">
          {triageRes.advice_blocks.map((a, i) => <li key={i}>{a}</li>)}
        </ul>

        <div className="cta-row" style={{ marginTop: 18 }}>
          <button className="btn-primary" onClick={downloadPdf}>Download Doctor PDF</button>
          <button className="btn-secondary" onClick={onRestart}>{restartLabel}</button>
        </div>
      </section>
    </main>
  );
}
