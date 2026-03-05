import { useState } from "react";

import Intake from "./pages/Intake";
import Result from "./pages/Result";
import Welcome from "./pages/Welcome";

export default function App() {
  const [step, setStep] = useState("landing");
  const [intake, setIntake] = useState(null);
  const [triageRes, setTriageRes] = useState(null);

  if (step === "landing") {
    return <Welcome onNext={() => setStep("intake")} />;
  }

  if (step === "intake") {
    return (
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

  return (
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
