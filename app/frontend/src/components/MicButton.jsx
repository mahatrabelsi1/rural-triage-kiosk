import { useEffect, useRef, useState } from "react";

import {
  browserRecognitionAvailable,
  serverRecordingAvailable,
  startBrowserRecognition,
  startServerRecording,
} from "../voice/stt";
import { STOP_SPEAKING_EVENT, useVoiceSettings } from "../voice/VoiceSettings";

const NOTHING_HEARD = "We did not catch any words. Please press the microphone and speak again, a little closer.";
const MIC_BLOCKED = "Microphone permission was blocked. Please allow the microphone, or type instead.";

const BROWSER_ERRORS = {
  "not-allowed": MIC_BLOCKED,
  "no-speech": NOTHING_HEARD,
  aborted: "",
};

// When the kiosk server can't transcribe (model missing, or server down or
// restarting), "auto" mode uses browser recognition until this time passes.
let serverSttRetryAt = 0;
const serverSttUnavailable = () => Date.now() < serverSttRetryAt;

// Speech-to-text button for a text field. Calls onText with the recognised words.
export default function MicButton({ onText, label = "Speak" }) {
  const { settings, setListening } = useVoiceSettings();
  const [state, setState] = useState("idle"); // idle | listening | recording | transcribing
  const [interim, setInterim] = useState("");
  const [error, setError] = useState("");
  const sessionRef = useRef(null);

  const engine = settings.sttEngine;
  const canUseBrowser = browserRecognitionAvailable() && engine !== "server";
  const canUseServer = serverRecordingAvailable() && engine !== "browser";
  const supported = canUseBrowser || canUseServer;

  useEffect(() => {
    setListening(state === "listening" || state === "recording");
  }, [state, setListening]);

  useEffect(() => () => {
    sessionRef.current?.abort?.();
    sessionRef.current?.cancel?.();
    setListening(false);
  }, [setListening]);

  function deliver(text) {
    const cleaned = (text || "").trim();
    if (cleaned) onText(cleaned);
    else setError(NOTHING_HEARD);
  }

  async function startServer() {
    try {
      const session = await startServerRecording({ onAutoStop: () => finishServer() });
      sessionRef.current = session;
      setState("recording");
    } catch (err) {
      setState("idle");
      setError(err?.name === "NotAllowedError" ? MIC_BLOCKED : "Could not start the microphone on this device.");
    }
  }

  async function finishServer() {
    const session = sessionRef.current;
    if (!session?.stop) return;
    sessionRef.current = null;
    setState("transcribing");
    try {
      deliver(await session.stop());
    } catch (err) {
      const unreachable = err?.status === 0;
      if ((err?.status === 503 || unreachable) && engine === "auto" && browserRecognitionAvailable()) {
        // Model missing: skip the server for 10 min. Server down/restarting: retry it after 30 s.
        serverSttRetryAt = Date.now() + (unreachable ? 30000 : 600000);
        setError(unreachable
          ? "The kiosk server did not respond. Press the microphone again to use the browser instead. (Staff: check that the backend is running.)"
          : "Offline speech recognition is not ready on this kiosk. Press the microphone again to use the browser instead.");
      } else if (unreachable) {
        setError("The kiosk server did not respond. Please try again, or type instead. (Staff: check that the backend is running on port 8000.)");
      } else {
        setError(err instanceof Error ? `Speech-to-text failed: ${err.message}` : "Speech-to-text failed.");
      }
    } finally {
      setState("idle");
    }
  }

  function startBrowser() {
    setState("listening");
    sessionRef.current = startBrowserRecognition({
      onInterim: setInterim,
      onFinal: deliver,
      onError: ({ code, canFallBack }) => {
        sessionRef.current = null;
        if (canFallBack && canUseServer && !serverSttUnavailable()) {
          // Usually "network": browser recognition needs internet. Record locally instead.
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
    // The kiosk server is the reliable path (offline, any browser); browser
    // recognition is used only when chosen or when the server can't help.
    if (canUseServer && !(engine === "auto" && serverSttUnavailable() && canUseBrowser)) startServer();
    else if (canUseBrowser) startBrowser();
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
      {active && (
        <span className="mic-hint">
          {interim || (state === "recording" ? "Speak now. It stops by itself when you pause." : "Listening...")}
        </span>
      )}
      {error && <span className="mic-error" role="alert">{error}</span>}
    </div>
  );
}
