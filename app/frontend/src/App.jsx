import { useState } from "react";

import AvatarAssistant from "./components/AvatarAssistant";
import Intake from "./pages/Intake";
import Queue from "./pages/Queue";
import Result from "./pages/Result";
import Welcome from "./pages/Welcome";

const WELCOME_LINE = "Hello, good evening! I am happy to help you today! Let us take care of this together.";
const PATIENT_INFO_LINE = "Patient information! Great, let us start with the patient profile and chief complaint.";
const QUEUE_LINE = "Clinic queue! Here are the recent patients, sorted by urgency for clinician review.";

function resultLine(level, prefix = "You are") {
  if (level === "RED") {
    return `${prefix} red. Please seek urgent medical attention now. We will help you right away.`;
  }
  if (level === "ORANGE") {
    return `${prefix} orange. Please see the officer and wait for same-day review. You are in the right place.`;
  }
  return `${prefix} green! Good news. Please follow the guidance, rest if you can, and come back another day if symptoms continue or get worse.`;
}

export default function App() {
  const [step, setStep] = useState("landing");
  const [role, setRole] = useState("intake");
  const [intake, setIntake] = useState(null);
  const [triageRes, setTriageRes] = useState(null);
  const [speechText, setSpeechText] = useState(WELCOME_LINE);

  let page = null;
  if (step === "landing") {
    page = (
      <Welcome
        role={role}
        onRoleChange={setRole}
        onNext={() => {
          setSpeechText(PATIENT_INFO_LINE);
          setStep("intake");
        }}
        onQueue={() => {
          setSpeechText(QUEUE_LINE);
          setStep("queue");
        }}
      />
    );
  }
  if (step === "intake") {
    page = (
      <Intake
        onBack={() => setStep("landing")}
        onNarration={setSpeechText}
        onDone={(data, res) => {
          setIntake(data);
          setTriageRes(res);
          setSpeechText(resultLine(res.triage_level));
          setStep("result");
        }}
      />
    );
  }
  if (step === "queue") {
    page = (
      <Queue
        onBack={() => setStep("landing")}
        onOpenSummary={(storedIntake, storedResult) => {
          setIntake(storedIntake);
          setTriageRes(storedResult);
          setSpeechText(resultLine(storedResult.triage_level, "This patient is"));
          setStep("result");
        }}
      />
    );
  }
  if (step === "result") {
    page = (
      <Result
        intake={intake}
        triageRes={triageRes}
        restartLabel={role === "clinician" ? "Back To Queue" : "New Patient"}
        onRestart={() => {
          setStep(role === "clinician" ? "queue" : "landing");
          setIntake(null);
          setTriageRes(null);
          setSpeechText(
            role === "clinician"
              ? QUEUE_LINE
              : WELCOME_LINE
          );
        }}
      />
    );
  }

  return (
    <div className="split-layout">
      <div className="split-triage">{page}</div>
      <aside className="split-video">
        <AvatarAssistant speechText={speechText} />
      </aside>
    </div>
  );
}
