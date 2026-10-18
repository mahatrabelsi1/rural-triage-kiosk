import { useState } from "react";

import { downloadPdf } from "../api/client";
import { SEVERITY_OPTIONS, symptomLabel } from "./Intake";

const PATIENT_MESSAGES = {
  RED: {
    title: "Urgent: go to the nurse now",
    steps: [
      "Go to the nurse desk now, or ask someone to call the nurse.",
      "Sit or lie down while you wait. Do not walk around alone.",
      "Show the nurse the number below.",
    ],
  },
  ORANGE: {
    title: "Please stay: you will be seen today",
    steps: [
      "Stay in the clinic waiting area.",
      "Tell the nurse straight away if you feel worse.",
      "Show the nurse the number below when you are called.",
    ],
  },
  GREEN: {
    title: "Lower urgency: follow the advice",
    steps: [
      "Please wait to be called, or follow the advice below.",
      "Come back or tell the nurse if anything gets worse.",
      "Show the nurse the number below if you are asked.",
    ],
  },
};

// Rule IDs and NLP notes are for clinicians; patients see only the plain advice.
const STAFF_ONLY_ADVICE = ["Escalation context:", "Clarification questions are still recommended"];

function severityWord(rating) {
  return SEVERITY_OPTIONS.find((o) => o.value === Number(rating))?.label || String(rating);
}

export default function Result({ intake, triageRes, isStaff, onRestart, onAuthExpired, onReadAloud, restartLabel = "New Patient" }) {
  const level = triageRes?.triage_level || "GREEN";
  const levelKey = level.toLowerCase();
  const [pdfError, setPdfError] = useState("");
  const [pdfLoading, setPdfLoading] = useState(false);
  const message = PATIENT_MESSAGES[level];
  const patientAdvice = triageRes.advice_blocks.filter((a) => !STAFF_ONLY_ADVICE.some((p) => a.startsWith(p)));

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

  function readAdvice() {
    onReadAloud?.([message.title, ...message.steps, ...patientAdvice].join(" "));
  }

  if (!isStaff) {
    return (
      <main className="shell">
        <section className={`card result-card level-${levelKey}`}>
          <div className="patient-result" aria-live="polite">
            <span className="result-chip">{level}</span>
            <h2>{message.title}</h2>
            <ol className="patient-steps">
              {message.steps.map((step) => <li key={step}>{step}</li>)}
            </ol>
            <div className="session-code">
              <span>Your number</span>
              <strong>{triageRes.session_id}</strong>
            </div>
          </div>

          <h3 className="section-title">Advice</h3>
          <ul className="list">
            {patientAdvice.map((a, i) => <li key={i}>{a}</li>)}
          </ul>

          <p className="notice">This result helps the clinic decide who to see first. It is not a diagnosis.</p>

          <div className="cta-row" style={{ marginTop: 18 }}>
            {onReadAloud && (
              <button className="btn-secondary" onClick={readAdvice}>Read Aloud</button>
            )}
            <button className="btn-primary" onClick={onRestart}>{restartLabel}</button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className={`card result-card level-${levelKey}`}>
        <div className="result-banner">
          <div>
            <h2 className="section-title" style={{ marginBottom: 4 }}>Triage Result</h2>
            <p className="muted-line">Session ID: {triageRes.session_id}</p>
          </div>
          <h1 className="result-level">{level}</h1>
        </div>

        <h3 className="section-title">Patient Profile</h3>
        <ul className="list">
          <li>Name: {intake.patient_name || "N/A"}</li>
          <li>Entered by: {intake.entered_by || "N/A"}</li>
          <li>Age group: {intake.age_group || "N/A"}</li>
          <li>Sex: {intake.sex || "N/A"}</li>
          <li>Pregnant: {intake.pregnant == null ? "N/A" : (intake.pregnant ? "Yes" : "No")}</li>
          <li>Chronic illnesses: {chronicLines.length ? chronicLines.join(", ") : "None declared"}</li>
        </ul>

        <h3 className="section-title">Chief Complaint</h3>
        <p className="muted-line">{intake.chief_complaint_text || "N/A"}</p>

        <h3 className="section-title">Symptoms (0-3 scale)</h3>
        <ul className="list">
          {triageRes.selected_symptoms.length ? triageRes.selected_symptoms.map((s) => (
            <li key={s.symptom}>{symptomLabel(s.symptom)}: {s.rating}/3 ({severityWord(s.rating)})</li>
          )) : <li>None selected</li>}
        </ul>

        <h3 className="section-title">AI Extracted From Text</h3>
        <ul className="list">
          {triageRes.extracted_symptoms?.length ? triageRes.extracted_symptoms.map((s) => (
            <li key={s.symptom}>
              {symptomLabel(s.symptom)}: {s.rating}/3
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
          <button className="btn-primary" onClick={savePdf} disabled={pdfLoading}>
            {pdfLoading ? "Preparing PDF..." : "Download Doctor PDF"}
          </button>
          <button className="btn-secondary" onClick={onRestart}>{restartLabel}</button>
        </div>
      </section>
    </main>
  );
}
