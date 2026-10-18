import { useCallback, useEffect, useRef, useState } from "react";

import { loadStaffSession, saveStaffSession, setStaffToken } from "./api/client";
import AvatarAssistant from "./components/AvatarAssistant";
import Intake from "./pages/Intake";
import Login from "./pages/Login";
import Queue from "./pages/Queue";
import Result from "./pages/Result";
import Welcome from "./pages/Welcome";

const WELCOME_LINE = "Hello and welcome! I am your virtual nurse. Please tell me who is filling in the form today.";
const QUEUE_LINE = "Clinic queue. Here are the recent patients, sorted by urgency for clinician review.";
const LOGIN_LINE = "Staff login. Please enter your clinic username and password.";

// A shared public kiosk must not keep one patient's answers on screen for the next person.
const PATIENT_IDLE_MS = 3 * 60 * 1000;
const STAFF_IDLE_MS = 10 * 60 * 1000;

function resultLine(level, enteredBy) {
  const who = enteredBy === "companion" ? "The patient's result is" : enteredBy === "nurse" ? "This patient is" : "Your result is";
  if (level === "RED") {
    return `${who} red. This is urgent. Please go to the nurse desk now, or call for help. Someone will see you right away.`;
  }
  if (level === "ORANGE") {
    return `${who} orange. Please stay in the clinic. A clinician will see you today. Tell the nurse if you feel worse.`;
  }
  return `${who} green. Please follow the advice on the screen, and tell the nurse if anything gets worse.`;
}

function useIdle(active, timeoutMs, onIdle) {
  const onIdleRef = useRef(onIdle);
  onIdleRef.current = onIdle;

  useEffect(() => {
    if (!active) return undefined;
    let timer = setTimeout(() => onIdleRef.current(), timeoutMs);
    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(() => onIdleRef.current(), timeoutMs);
    };
    const events = ["pointerdown", "keydown", "input", "scroll"];
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    return () => {
      clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [active, timeoutMs]);
}

export default function App() {
  const [step, setStep] = useState("landing");
  const [enteredBy, setEnteredBy] = useState("patient");
  const [intake, setIntake] = useState(null);
  const [triageRes, setTriageRes] = useState(null);
  const [resultFromQueue, setResultFromQueue] = useState(false);
  const [speechText, setSpeechText] = useState(WELCOME_LINE);
  const [staff, setStaff] = useState(() => loadStaffSession());

  const narrate = useCallback((text) => setSpeechText(text), []);

  function updateStaff(session) {
    saveStaffSession(session);
    setStaffToken(session?.token);
    setStaff(session);
  }

  function goHome() {
    setIntake(null);
    setTriageRes(null);
    setResultFromQueue(false);
    setSpeechText(WELCOME_LINE);
    setStep("landing");
  }

  function openQueue() {
    setSpeechText(staff ? QUEUE_LINE : LOGIN_LINE);
    setStep(staff ? "queue" : "login");
  }

  function authExpired() {
    updateStaff(null);
    setSpeechText(LOGIN_LINE);
    setStep("login");
  }

  const inPatientFlow = step === "intake" || (step === "result" && !resultFromQueue);
  useIdle(inPatientFlow, PATIENT_IDLE_MS, goHome);
  useIdle(Boolean(staff), STAFF_IDLE_MS, () => {
    updateStaff(null);
    if (!inPatientFlow) goHome();
  });

  let page = null;
  if (step === "landing") {
    page = (
      <Welcome
        staff={staff}
        onStart={(who) => {
          setEnteredBy(who);
          setStep("intake");
        }}
        onQueue={openQueue}
      />
    );
  }
  if (step === "intake") {
    page = (
      <Intake
        key={enteredBy}
        enteredBy={enteredBy}
        onBack={goHome}
        onNarration={narrate}
        onDone={(data, res) => {
          setIntake(data);
          setTriageRes(res);
          setResultFromQueue(false);
          setSpeechText(resultLine(res.triage_level, data.entered_by));
          setStep("result");
        }}
      />
    );
  }
  if (step === "login") {
    page = (
      <Login
        onBack={goHome}
        onLoggedIn={(session) => {
          updateStaff(session);
          setSpeechText(QUEUE_LINE);
          setStep("queue");
        }}
      />
    );
  }
  if (step === "queue") {
    page = (
      <Queue
        staff={staff}
        onAuthExpired={authExpired}
        onLogout={() => {
          updateStaff(null);
          goHome();
        }}
        onBack={goHome}
        onOpenSummary={(storedIntake, storedResult) => {
          setIntake(storedIntake);
          setTriageRes(storedResult);
          setResultFromQueue(true);
          setSpeechText(resultLine(storedResult.triage_level, "nurse"));
          setStep("result");
        }}
      />
    );
  }
  if (step === "result") {
    const staffView = resultFromQueue && Boolean(staff);
    page = (
      <Result
        intake={intake}
        triageRes={triageRes}
        isStaff={staffView}
        onAuthExpired={authExpired}
        onReadAloud={narrate}
        restartLabel={staffView ? "Back To Queue" : "Finish"}
        onRestart={() => {
          if (staffView) {
            setIntake(null);
            setTriageRes(null);
            setSpeechText(QUEUE_LINE);
            setStep("queue");
          } else {
            goHome();
          }
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
