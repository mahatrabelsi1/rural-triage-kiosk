import { useEffect, useState } from "react";
import { postTriage } from "../api/client";
import MicButton from "../components/MicButton";

const SYMPTOM_CATEGORIES = [
  {
    id: "respiratory_flu",
    label: "Breathing / Flu-like",
    symptoms: ["fever", "cough", "shortness_of_breath", "sore_throat", "chills", "fatigue", "body_aches", "rash"],
  },
  {
    id: "digestive",
    label: "Stomach / Hydration",
    symptoms: ["abdominal_pain", "nausea", "vomiting", "diarrhea", "dehydration_signs"],
  },
  {
    id: "neuro_general",
    label: "Head / General",
    symptoms: ["headache", "dizziness", "fainting", "confusion", "severe_weakness", "back_pain"],
  },
  {
    id: "urgent_specific",
    label: "Urgent / Specific",
    symptoms: ["chest_pain", "bleeding", "head_injury", "urination_pain", "allergic_reaction", "pregnancy_bleeding"],
  },
];

// Plain-language names shown to patients; keys must match rules.json.
const SYMPTOM_LABELS = {
  fever: "Fever / hot body",
  cough: "Cough",
  shortness_of_breath: "Hard to breathe",
  sore_throat: "Sore throat",
  chills: "Chills / shivering",
  fatigue: "Tired / low energy",
  body_aches: "Body aches",
  rash: "Skin rash",
  abdominal_pain: "Stomach pain",
  nausea: "Feeling sick (nausea)",
  vomiting: "Vomiting",
  diarrhea: "Diarrhea",
  dehydration_signs: "Very thirsty / dry mouth",
  headache: "Headache",
  dizziness: "Dizziness",
  fainting: "Fainting / passing out",
  confusion: "Confused / not thinking clearly",
  severe_weakness: "Very weak / cannot stand",
  back_pain: "Back pain",
  chest_pain: "Chest pain or tightness",
  bleeding: "Bleeding",
  head_injury: "Head injury",
  urination_pain: "Pain when passing urine",
  allergic_reaction: "Allergic reaction / swelling",
  pregnancy_bleeding: "Bleeding during pregnancy",
};

export const SEVERITY_OPTIONS = [
  { value: 0, label: "None" },
  { value: 1, label: "Mild" },
  { value: 2, label: "Moderate" },
  { value: 3, label: "Severe" },
];

const SYMPTOMS = SYMPTOM_CATEGORIES.flatMap((c) => c.symptoms);
const CHRONIC_OPTIONS = ["diabetes", "hypertension", "heart_problem"];
const CHRONIC_LABELS = { diabetes: "Diabetes", hypertension: "High blood pressure", heart_problem: "Heart problem" };

// Wording changes with who is holding the kiosk.
const COPY = {
  patient: {
    profileTitle: "About you",
    name: "Your name",
    age: "Your age group",
    sex: "Your sex",
    pregnant: "Are you pregnant?",
    illnesses: "Do you have any long-term illness?",
    complaint: "What is wrong today? Tell us in your own words.",
    symptomsTitle: "How bad is each problem for you right now?",
  },
  companion: {
    profileTitle: "About the patient",
    name: "Patient's name",
    age: "Patient's age group",
    sex: "Patient's sex",
    pregnant: "Is the patient pregnant?",
    illnesses: "Does the patient have any long-term illness?",
    complaint: "What is wrong with the patient today?",
    symptomsTitle: "How bad is each problem for the patient right now?",
  },
  nurse: {
    profileTitle: "Patient information",
    name: "Patient name",
    age: "Age group",
    sex: "Sex",
    pregnant: "Pregnant?",
    illnesses: "Existing illnesses",
    complaint: "Chief complaint (free text)",
    symptomsTitle: "Symptom severity",
  },
};

export function symptomLabel(key) {
  return SYMPTOM_LABELS[key] || key.replaceAll("_", " ");
}

export default function Intake({ enteredBy = "patient", onBack, onDone, onNarration }) {
  const copy = COPY[enteredBy] || COPY.patient;
  const isNurse = enteredBy === "nurse";

  const [formStep, setFormStep] = useState("patient");
  const [categoryIndex, setCategoryIndex] = useState(0);
  const [patientName, setPatientName] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [sex, setSex] = useState("");
  const [pregnant, setPregnant] = useState("");
  const [useNlpExtraction, setUseNlpExtraction] = useState(true);
  const [chronicIllnesses, setChronicIllnesses] = useState(() => Object.fromEntries(CHRONIC_OPTIONS.map(s => [s, false])));
  const [chronicOther, setChronicOther] = useState("");
  const [chief, setChief] = useState("");
  const [symptoms, setSymptoms] = useState(() => Object.fromEntries(SYMPTOMS.map(s => [s, 0])));
  const [followUps, setFollowUps] = useState([]);
  const [followAnswers, setFollowAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canBePregnant = sex !== "male" && ageGroup !== "elderly";

  function setSymptom(k, v) {
    setSymptoms(prev => ({ ...prev, [k]: Number(v) }));
  }

  function changeSex(value) {
    setSex(value);
    if (value === "male") setPregnant("");
  }

  useEffect(() => {
    if (!onNarration) return;
    if (formStep === "patient") {
      onNarration(`${copy.profileTitle}. Please fill in the details, and tell us what is wrong today.`);
    }
    if (formStep === "symptoms") {
      onNarration(`${SYMPTOM_CATEGORIES[categoryIndex].label}. ${copy.symptomsTitle} Choose none, mild, moderate, or severe.`);
    }
    if (formStep === "clarify") {
      onNarration(`Almost done. Please answer yes or no. ${followUps.map((q) => q.question_text).join(" ")}`);
    }
  }, [formStep, categoryIndex, onNarration, copy, followUps]);

  function toggleChronic(k) {
    setChronicIllnesses(prev => ({ ...prev, [k]: !prev[k] }));
  }

  function nextToSymptoms() {
    setError("");
    setCategoryIndex(0);
    setFormStep("symptoms");
  }

  function buildPayload(overrideSymptoms, clarificationCompleted = false) {
    const selectedChronic = Object.entries(chronicIllnesses)
      .filter(([, checked]) => checked)
      .map(([name]) => name);

    return {
      entered_by: enteredBy,
      patient_name: patientName.trim(),
      age_group: ageGroup || null,
      sex: sex || null,
      pregnant: !canBePregnant || pregnant === "" ? null : pregnant === "yes",
      use_nlp_extraction: useNlpExtraction,
      clarification_completed: clarificationCompleted,
      chronic_illnesses: selectedChronic,
      chronic_illnesses_other: chronicOther.trim(),
      chief_complaint_text: chief,
      symptoms: overrideSymptoms ?? symptoms,
    };
  }

  async function submit() {
    const anyRated = Object.values(symptoms).some((v) => v > 0);
    if (!chief.trim() && !anyRated) {
      setError("Please describe the problem in words, or mark at least one symptom.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const payload = buildPayload();
      const res = await postTriage(payload);
      if (res.needs_clarification && res.follow_up_questions?.length) {
        setFollowUps(res.follow_up_questions);
        setFollowAnswers(Object.fromEntries(res.follow_up_questions.map((q) => [q.question_id, ""])));
        setFormStep("clarify");
        return;
      }
      onDone(payload, res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Submit failed.";
      setError(`Could not get the result: ${msg} Please ask the nurse for help.`);
    } finally {
      setLoading(false);
    }
  }

  async function submitClarification() {
    const hasUnanswered = followUps.some((q) => !followAnswers[q.question_id]);
    if (hasUnanswered) {
      setError("Please answer every question with Yes or No.");
      return;
    }

    setError("");
    setLoading(true);
    try {
      const clarifiedSymptoms = { ...symptoms };
      for (const q of followUps) {
        if (followAnswers[q.question_id] === "yes") {
          const previous = Number(clarifiedSymptoms[q.symptom] || 0);
          clarifiedSymptoms[q.symptom] = Math.max(previous, Number(q.suggested_rating_if_yes || 2));
        }
      }

      setSymptoms(clarifiedSymptoms);
      const payload = buildPayload(clarifiedSymptoms, true);
      const res = await postTriage(payload);
      onDone(payload, res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Submit failed.";
      setError(`Could not get the result: ${msg} Please ask the nurse for help.`);
    } finally {
      setLoading(false);
    }
  }

  const lastCategory = categoryIndex === SYMPTOM_CATEGORIES.length - 1;

  return (
    <main className="shell">
      <section className="card">
        <div className="steps">
          <span className={`step-chip ${formStep === "patient" ? "active" : ""}`}>1. Details</span>
          <span className={`step-chip ${formStep === "symptoms" ? "active" : ""}`}>2. Symptoms</span>
          <span className={`step-chip ${formStep === "clarify" ? "active" : ""}`}>3. Check</span>
          <span className="step-chip">4. Result</span>
        </div>

        {formStep === "patient" && (
          <>
            <h2 className="section-title">{copy.profileTitle}</h2>
            <div className="grid-2">
              <div>
                <label htmlFor="patient-name">{copy.name}</label>
                <input id="patient-name" value={patientName} onChange={(e) => setPatientName(e.target.value)} />
                <MicButton label="Say name" onText={(t) => setPatientName(t.replace(/[.!?]+$/, ""))} />
              </div>
              <div>
                <label htmlFor="age-group">{copy.age}</label>
                <select id="age-group" value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                  <option value="">Select</option>
                  <option value="child">Child (under 16)</option>
                  <option value="adult">Adult (16 to 64)</option>
                  <option value="elderly">Older adult (65+)</option>
                </select>
              </div>
              <div>
                <label htmlFor="sex">{copy.sex}</label>
                <select id="sex" value={sex} onChange={(e) => changeSex(e.target.value)}>
                  <option value="">Select</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="other">Other / prefer not to say</option>
                </select>
              </div>
              {canBePregnant && (
                <div>
                  <label htmlFor="pregnant">{copy.pregnant}</label>
                  <select id="pregnant" value={pregnant} onChange={(e) => setPregnant(e.target.value)}>
                    <option value="">Not sure / not applicable</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>
              )}
            </div>

            <h3 className="section-title" style={{ marginTop: 20 }}>{copy.illnesses}</h3>
            <div className="check-grid">
              {CHRONIC_OPTIONS.map((k) => (
                <label key={k} className="check-item">
                  <input type="checkbox" checked={chronicIllnesses[k]} onChange={() => toggleChronic(k)} />
                  {CHRONIC_LABELS[k]}
                </label>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <label htmlFor="chronic-other">Other illness (optional)</label>
              <input id="chronic-other" value={chronicOther} onChange={(e) => setChronicOther(e.target.value)} />
              <MicButton label="Say it" onText={(t) => setChronicOther(t.replace(/[.!?]+$/, ""))} />
            </div>

            <div style={{ marginTop: 10 }}>
              <label htmlFor="chief-complaint">{copy.complaint}</label>
              <textarea id="chief-complaint" value={chief} onChange={(e) => setChief(e.target.value)} rows={3} />
              <MicButton label="Speak instead of typing" onText={(t) => setChief((prev) => (prev.trim() ? `${prev.trim()} ${t}` : t))} />
            </div>

            {isNurse && (
              <div style={{ marginTop: 10 }}>
                <label className="check-item">
                  <input
                    type="checkbox"
                    checked={useNlpExtraction}
                    onChange={() => setUseNlpExtraction((v) => !v)}
                  />
                  Use AI text extraction from chief complaint
                </label>
              </div>
            )}

            <div className="cta-row" style={{ marginTop: 18 }}>
              <button className="btn-secondary" onClick={onBack}>Back</button>
              <button className="btn-primary" onClick={nextToSymptoms}>Continue To Symptoms</button>
            </div>
          </>
        )}

        {formStep === "symptoms" && (
          <>
            <h2 className="section-title">{copy.symptomsTitle}</h2>
            <p className="muted-line">
              Part {categoryIndex + 1} of {SYMPTOM_CATEGORIES.length}: {SYMPTOM_CATEGORIES[categoryIndex].label}. Leave "None" if it does not apply.
            </p>
            <div className="category-progress">
              {SYMPTOM_CATEGORIES.map((cat, idx) => (
                <button
                  key={cat.id}
                  type="button"
                  className={`step-chip ${idx === categoryIndex ? "active" : ""}`}
                  onClick={() => setCategoryIndex(idx)}
                >
                  {idx + 1}. {cat.label}
                </button>
              ))}
            </div>
            <div className="symptom-grid-3">
              {SYMPTOM_CATEGORIES[categoryIndex].symptoms
                .filter((k) => k !== "pregnancy_bleeding" || canBePregnant)
                .map((k) => (
                  <div key={k} className={`symptom-card severity-${symptoms[k]}`}>
                    <span className="symptom-name" id={`label-${k}`}>{symptomLabel(k)}</span>
                    <div className="severity-row" role="radiogroup" aria-labelledby={`label-${k}`}>
                      {SEVERITY_OPTIONS.map((opt) => (
                        <button
                          key={opt.value}
                          type="button"
                          role="radio"
                          aria-checked={symptoms[k] === opt.value}
                          className={`severity-btn sev-${opt.value} ${symptoms[k] === opt.value ? "selected" : ""}`}
                          onClick={() => setSymptom(k, opt.value)}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
            </div>

            {error && <p className="error-text" role="alert">{error}</p>}

            <div className="cta-row" style={{ marginTop: 18 }}>
              <button
                className="btn-secondary"
                onClick={() => (categoryIndex === 0 ? setFormStep("patient") : setCategoryIndex((v) => v - 1))}
              >
                Back
              </button>
              {!lastCategory ? (
                <button className="btn-primary" onClick={() => setCategoryIndex((v) => v + 1)}>Next</button>
              ) : (
                <button className="btn-primary" onClick={submit} disabled={loading}>
                  {loading ? "Processing..." : "Get Result"}
                </button>
              )}
            </div>
          </>
        )}

        {formStep === "clarify" && (
          <>
            <h2 className="section-title">A few safety questions</h2>
            <p className="muted-line">
              Please answer these quick questions before we show the result.
            </p>

            <div className="clarify-list">
              {followUps.map((q) => (
                <div key={q.question_id} className="clarify-item">
                  <p>{q.question_text}</p>
                  <div className="cta-row">
                    <button
                      type="button"
                      className={`btn-secondary btn-large ${followAnswers[q.question_id] === "yes" ? "btn-choice-active" : ""}`}
                      onClick={() => setFollowAnswers((prev) => ({ ...prev, [q.question_id]: "yes" }))}
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      className={`btn-secondary btn-large ${followAnswers[q.question_id] === "no" ? "btn-choice-active" : ""}`}
                      onClick={() => setFollowAnswers((prev) => ({ ...prev, [q.question_id]: "no" }))}
                    >
                      No
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {error && <p className="error-text" role="alert">{error}</p>}

            <div className="cta-row" style={{ marginTop: 18 }}>
              <button className="btn-secondary" onClick={() => setFormStep("symptoms")}>Back To Symptoms</button>
              <button className="btn-primary" onClick={submitClarification} disabled={loading}>
                {loading ? "Rechecking..." : "Finish"}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
