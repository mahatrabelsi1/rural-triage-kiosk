import { useState } from "react";

import { downloadPdf } from "../api/client";

function prettyLabel(key) {
  return key.replaceAll("_", " ");
}

export default function Result({ intake, triageRes, isStaff, onRestart, onAuthExpired, restartLabel = "New Patient" }) {
  const levelKey = (triageRes?.triage_level || "GREEN").toLowerCase();
  const [pdfError, setPdfError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);

  async function savePdf() {
    setPdfError("");
    setPdfLoading(true);
    try {
      // The server rebuilds the PDF from the stored session, so only the ID is sent.
      const blob = await downloadPdf(triageRes.session_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `triage_${triageRes.session_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Revoking immediately can cancel the download in some browsers.
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      if (e?.status === 401) return onAuthExpired?.();
      setPdfError(e instanceof Error ? e.message : "PDF failed.");
    } finally {
      setPdfLoading(false);
    }
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

        <h3 className="section-title">Selected Symptoms (0-3)</h3>
        <ul className="list">
          {triageRes.selected_symptoms.length ? triageRes.selected_symptoms.map((s) => (
            <li key={s.symptom}>{prettyLabel(s.symptom)}: {s.rating}/3</li>
          )) : <li>None selected</li>}
        </ul>

        <h3 className="section-title">AI Extracted From Text</h3>
        <ul className="list">
          {triageRes.extracted_symptoms?.length ? triageRes.extracted_symptoms.map((s) => (
            <li key={s.symptom}>
              {prettyLabel(s.symptom)}: {s.rating}/3
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

        {pdfError && <p className="error-text" role="alert">{pdfError}</p>}
        <div className="cta-row" style={{ marginTop: 18 }}>
          {isStaff && (
            <button className="btn-primary" onClick={savePdf} disabled={pdfLoading}>
              {pdfLoading ? "Preparing PDF..." : "Download Doctor PDF"}
            </button>
          )}
          <button className="btn-secondary" onClick={onRestart}>{restartLabel}</button>
        </div>
      </section>
    </main>
  );
}
