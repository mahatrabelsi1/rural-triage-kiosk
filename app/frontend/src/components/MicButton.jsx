import { useEffect, useRef, useState } from "react";

import {
  browserRecognitionAvailable,
  serverRecordingAvailable,
  startBrowserRecognition,
  startServerRecording,
} from "../voice/stt";
import { STOP_SPEAKING_EVENT, useVoiceSettings } from "../voice/VoiceSettings";

const BROWSER_ERRORS = {
  "not-allowed": "Microphone permission was blocked. Please allow the microphone, or type instead.",
  "no-speech": "We did not hear anything. Please try again, a little closer to the microphone.",
  aborted: "",
};

// Speech-to-text button for a text field. Calls onText with the recognised words.
export default function MicButton({ onText, label = "Speak" }) {
  const { settings, setListening } = useVoiceSettings();
  const [state, setState] = useState("idle"); // idle | listening | recording | transcribing
  const [interim, setInterim] = useState("");
  const [error, setError] = useState("");
  const sessionRef = useRef(null);

  const canUseBrowser = browserRecognitionAvailable() && settings.sttEngine !== "server";
  const canUseServer = serverRecordingAvailable() && settings.sttEngine !== "browser";
  const supported = canUseBrowser || canUseServer;

  useEffect(() => {
    setListening(state === "listening" || state === "recording");
  }, [state, setListening]);

  useEffect(() => () => {
    sessionRef.current?.abort?.();
    sessionRef.current?.cancel?.();
    setListening(false);
  }, [setListening]);

  async function startServer() {
    try {
      const session = await startServerRecording({ onAutoStop: () => finishServer() });
      sessionRef.current = session;
      setState("recording");
    } catch (err) {
      setState("idle");
      setError(err?.name === "NotAllowedError"
        ? "Microphone permission was blocked. Please allow the microphone, or type instead."
        : "Could not start the microphone on this device.");
    }
  }

  async function finishServer() {
    const session = sessionRef.current;
    if (!session?.stop) return;
    sessionRef.current = null;
    setState("transcribing");
    try {
      const text = await session.stop();
      if (text) onText(text);
      else setError("We did not catch any words. Please try again.");
    } catch (err) {
      setError(err instanceof Error ? `Speech-to-text failed: ${err.message}` : "Speech-to-text failed.");
    } finally {
      setState("idle");
    }
  }

  function startBrowser() {
    setState("listening");
    sessionRef.current = startBrowserRecognition({
      onInterim: setInterim,
      onFinal: (text) => {
        if (text) onText(text);
      },
      onError: ({ code, canFallBack }) => {
        sessionRef.current = null;
        if (canFallBack && canUseServer) {
          // Usually "network": Chrome/Edge recognition needs internet. Record locally instead.
          setInterim("");
          startServer();
          return;
        }
        setState("idle");
        setError(BROWSER_ERRORS[code] ?? `Speech recognition error (${code}). Please type instead.`);
      },
      onEnd: () => {
        setInterim("");
        setState((s) => (s === "listening" ? "idle" : s));
      },
    });
  }

  function toggle() {
    setError("");
    if (state === "listening") {
      sessionRef.current?.stop();
      return;
    }
    if (state === "recording") {
      finishServer();
      return;
    }
    if (state !== "idle") return;
    window.dispatchEvent(new Event(STOP_SPEAKING_EVENT));
    if (canUseBrowser) startBrowser();
    else if (canUseServer) startServer();
  }

  if (!supported) return null;

  const active = state === "listening" || state === "recording";
  return (
    <div className="mic-wrap">
      <button
        type="button"
        className={`mic-button ${active ? "active" : ""}`}
        onClick={toggle}
        disabled={state === "transcribing"}
        aria-pressed={active}
      >
        <span className="mic-dot" aria-hidden="true" />
        {state === "transcribing" ? "Writing it down..." : active ? "Stop" : label}
      </button>
      {active && <span className="mic-hint">{interim || (state === "recording" ? "Recording... press Stop when done." : "Listening...")}</span>}
      {error && <span className="mic-error" role="alert">{error}</span>}
    </div>
  );
}
