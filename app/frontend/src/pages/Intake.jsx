import { useState } from "react";
import { postTriage } from "../api/client";

const SYMPTOM_CATEGORIES = [
  {
    id: "respiratory_flu",
    label: "Respiratory / Flu-like",
    symptoms: ["fever", "cough", "shortness_of_breath", "sore_throat", "chills", "fatigue", "body_aches", "rash"],
  },
  {
    id: "digestive",
    label: "Digestive / Hydration",
    symptoms: ["abdominal_pain", "nausea", "vomiting", "diarrhea", "dehydration_signs"],
  },
  {
    id: "neuro_general",
    label: "Neurologic / General",
    symptoms: ["headache", "dizziness", "fainting", "confusion", "severe_weakness", "back_pain"],
  },
  {
    id: "urgent_specific",
    label: "Urgent / Specific",
    symptoms: ["chest_pain", "bleeding", "head_injury", "urination_pain", "allergic_reaction", "pregnancy_bleeding"],
  },
];

const SYMPTOMS = SYMPTOM_CATEGORIES.flatMap((c) => c.symptoms);

const CHRONIC_OPTIONS = ["diabetes", "hypertension", "heart_problem"];

function labelize(key) {
  return key.replaceAll("_", " ");
}

export default function Intake({ onBack, onDone }) {
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function setSymptom(k, v) {
    setSymptoms(prev => ({ ...prev, [k]: Number(v) }));
  }

  function toggleChronic(k) {
    setChronicIllnesses(prev => ({ ...prev, [k]: !prev[k] }));
  }

  function nextToSymptoms() {
    setError("");
    setCategoryIndex(0);
    setFormStep("symptoms");
  }

  function finishCategory() {
    if (categoryIndex < SYMPTOM_CATEGORIES.length - 1) {
      setCategoryIndex((v) => v + 1);
    }
  }

  async function submit() {
    setError("");
    setLoading(true);
    try {
      const selectedChronic = Object.entries(chronicIllnesses)
        .filter(([, checked]) => checked)
        .map(([name]) => name);

      const payload = {
        patient_name: patientName.trim(),
        age_group: ageGroup || null,
        sex: sex || null,
        pregnant: pregnant === "" ? null : pregnant === "yes",
        use_nlp_extraction: useNlpExtraction,
        chronic_illnesses: selectedChronic,
        chronic_illnesses_other: chronicOther.trim(),
        chief_complaint_text: chief,
        symptoms,
      };
      const res = await postTriage(payload);
      onDone(payload, res);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Submit failed.";
      setError(`Submit failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="card">
        <div className="steps">
          <span className={`step-chip ${formStep === "patient" ? "active" : ""}`}>1. Patient Info</span>
          <span className={`step-chip ${formStep === "symptoms" ? "active" : ""}`}>2. Symptoms</span>
          <span className="step-chip">3. Result</span>
        </div>

        {formStep === "patient" && (
          <>
            <h2 className="section-title">Patient Information</h2>
            <div className="grid-2">
              <div>
                <label>Patient name</label>
                <input value={patientName} onChange={(e) => setPatientName(e.target.value)} />
              </div>
              <div>
                <label>Age group</label>
                <select value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)}>
                  <option value="">Select</option>
                  <option value="child">Child</option>
                  <option value="adult">Adult</option>
                  <option value="elderly">Elderly</option>
                </select>
              </div>
              <div>
                <label>Sex</label>
                <select value={sex} onChange={(e) => setSex(e.target.value)}>
                  <option value="">Select</option>
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                </select>
              </div>
              <div>
                <label>Pregnant?</label>
                <select value={pregnant} onChange={(e) => setPregnant(e.target.value)}>
                  <option value="">Unknown / N/A</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </div>
            </div>

            <h3 className="section-title" style={{ marginTop: 20 }}>Existing Illnesses</h3>
            <div className="check-grid">
              {CHRONIC_OPTIONS.map((k) => (
                <label key={k} className="check-item">
                  <input type="checkbox" checked={chronicIllnesses[k]} onChange={() => toggleChronic(k)} />
                  {labelize(k)}
                </label>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <label>Other chronic illness</label>
              <input value={chronicOther} onChange={(e) => setChronicOther(e.target.value)} />
            </div>

            <div style={{ marginTop: 10 }}>
              <label>Chief complaint (free text)</label>
              <textarea value={chief} onChange={(e) => setChief(e.target.value)} rows={3} />
            </div>

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

            <div className="cta-row" style={{ marginTop: 18 }}>
              <button className="btn-secondary" onClick={onBack}>Back</button>
              <button className="btn-primary" onClick={nextToSymptoms}>Continue To Symptoms</button>
            </div>
          </>
        )}

        {formStep === "symptoms" && (
          <>
            <h2 className="section-title">Symptoms Rating</h2>
            <p className="muted-line">
              Category {categoryIndex + 1} of {SYMPTOM_CATEGORIES.length}: {SYMPTOM_CATEGORIES[categoryIndex].label}
            </p>
            <div className="category-progress">
              {SYMPTOM_CATEGORIES.map((cat, idx) => (
                <span key={cat.id} className={`step-chip ${idx === categoryIndex ? "active" : ""}`}>
                  {idx + 1}. {cat.label}
                </span>
              ))}
            </div>
            <div className="symptom-grid-3">
              {SYMPTOM_CATEGORIES[categoryIndex].symptoms.map((k) => (
                <div key={k} className="symptom-card">
                  <label>{labelize(k)}</label>
                  <select value={symptoms[k]} onChange={(e) => setSymptom(k, e.target.value)}>
                    <option value={0}>0</option>
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                    <option value={4}>4</option>
                    <option value={5}>5</option>
                  </select>
                </div>
              ))}
            </div>

            {error && <p className="error-text">{error}</p>}

            <div className="cta-row" style={{ marginTop: 18 }}>
              <button className="btn-secondary" onClick={() => setFormStep("patient")}>Back To Patient Info</button>
              {categoryIndex < SYMPTOM_CATEGORIES.length - 1 ? (
                <button className="btn-primary" onClick={finishCategory}>Finish Category</button>
              ) : (
                <button className="btn-primary" onClick={submit} disabled={loading}>
                  {loading ? "Processing..." : "Get Triage Result"}
                </button>
              )}
            </div>
          </>
        )}
      </section>
    </main>
  );
}
