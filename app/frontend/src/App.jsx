import { useState } from "react";

import AvatarAssistant from "./components/AvatarAssistant";
import Intake from "./pages/Intake";
import Result from "./pages/Result";
import Welcome from "./pages/Welcome";

export default function App() {
  const [step, setStep] = useState("landing");
  const [intake, setIntake] = useState(null);
  const [triageRes, setTriageRes] = useState(null);

  let page = null;
  if (step === "landing") {
    page = <Welcome onNext={() => setStep("intake")} />;
  }
  if (step === "intake") {
    page = (
      <Intake
        onBack={() => setStep("landing")}
        onDone={(data, res) => {
          setIntake(data);
          setTriageRes(res);
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
        onRestart={() => {
          setStep("landing");
          setIntake(null);
          setTriageRes(null);
        }}
      />
    );
  }

  return (
    <div className="split-layout">
      <div className="split-triage">{page}</div>
      <aside className="split-video">
        <AvatarAssistant />
      </aside>
    </div>
  );
}
