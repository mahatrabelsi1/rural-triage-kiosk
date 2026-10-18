import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import NurseAvatar from "./NurseAvatar";
import { createLipSync, wordIndexAt, wordSpans } from "../voice/lipsync";
import { hasBrowserVoice, speakWithBrowser, speakWithServer, waitForVoices } from "../voice/tts";
import { browserRecognitionAvailable } from "../voice/stt";
import { STOP_SPEAKING_EVENT, useVoiceSettings } from "../voice/VoiceSettings";

export default function AvatarAssistant({ speech }) {
  const { settings, updateSettings, listening } = useVoiceSettings();
  const mouthRef = useRef(null);
  const lipSyncRef = useRef(null);
  const controllerRef = useRef(null);
  const tokenRef = useRef(null);
  const lastSpokenIdRef = useRef(null);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  // Browsers block audio until the first tap or key press on the page.
  const [unlocked, setUnlocked] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [wordIndex, setWordIndex] = useState(-1);
  const [note, setNote] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [voices, setVoices] = useState([]);

  const text = speech?.text || "";
  const spans = useMemo(() => wordSpans(text), [text]);

  useEffect(() => {
    lipSyncRef.current = createLipSync((d) => mouthRef.current?.setAttribute("d", d));
    return () => lipSyncRef.current?.stop();
  }, []);

  useEffect(() => {
    let alive = true;
    waitForVoices().then((list) => alive && setVoices(list));
    const onChange = () => setVoices(window.speechSynthesis.getVoices());
    if (hasBrowserVoice()) window.speechSynthesis.addEventListener?.("voiceschanged", onChange);
    return () => {
      alive = false;
      if (hasBrowserVoice()) window.speechSynthesis.removeEventListener?.("voiceschanged", onChange);
    };
  }, []);

  const stop = useCallback(() => {
    tokenRef.current = null;
    controllerRef.current?.stop();
    controllerRef.current = null;
    lipSyncRef.current?.stop();
    setSpeaking(false);
    setWordIndex(-1);
  }, []);

  const speak = useCallback(async (spokenText) => {
    stop();
    if (!spokenText) return;
    const token = {};
    tokenRef.current = token;
    const { ttsEngine, rate, voiceURI } = settingsRef.current;
    const textSpans = wordSpans(spokenText);

    const finish = () => {
      if (tokenRef.current !== token) return;
      tokenRef.current = null;
      controllerRef.current = null;
      lipSyncRef.current?.stop();
      setSpeaking(false);
      setWordIndex(-1);
    };
    const options = {
      rate,
      voiceURI,
      onEnd: finish,
      onError: (err) => {
        setNote(err.message);
        finish();
      },
    };

    setSpeaking(true);
    setNote("");
    let controller = null;
    try {
      if (ttsEngine === "server") {
        try {
          controller = await speakWithServer(spokenText, options);
        } catch {
          if (tokenRef.current === token) setNote("AI voice unavailable, using the device voice.");
          controller = await speakWithBrowser(spokenText, options);
        }
      } else {
        try {
          controller = await speakWithBrowser(spokenText, options);
        } catch {
          controller = await speakWithServer(spokenText, options);
        }
      }
    } catch {
      if (tokenRef.current === token) setNote("Voice is not available on this device. Please read the screen.");
      finish();
      return;
    }

    if (tokenRef.current !== token) {
      controller.stop();
      return;
    }
    controllerRef.current = controller;

    let lastWord = -1;
    lipSyncRef.current?.start(() => {
      const sample = controller.sampler();
      if (sample) {
        const index = wordIndexAt(textSpans, sample.cursor);
        if (index !== lastWord) {
          lastWord = index;
          setWordIndex(index);
        }
      }
      return sample;
    });
  }, [stop]);

  useEffect(() => {
    function unlock() {
      setUnlocked(true);
    }
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  useEffect(() => {
    window.addEventListener(STOP_SPEAKING_EVENT, stop);
    return () => window.removeEventListener(STOP_SPEAKING_EVENT, stop);
  }, [stop]);

  // Speak each new narration request once, as soon as audio is allowed.
  useEffect(() => {
    if (!settings.voiceEnabled || !unlocked || !speech?.text) return;
    if (lastSpokenIdRef.current === speech.id) return;
    lastSpokenIdRef.current = speech.id;
    speak(speech.text);
  }, [speech, settings.voiceEnabled, unlocked, speak]);

  useEffect(() => {
    if (!settings.voiceEnabled) stop();
  }, [settings.voiceEnabled, stop]);

  useEffect(() => stop, [stop]);

  const englishVoices = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  const status = listening
    ? "Listening to you..."
    : speaking
      ? "Speaking"
      : !unlocked
        ? "Tap anywhere to hear the nurse"
        : settings.voiceEnabled
          ? "Ready to help"
          : "Voice is off";

  return (
    <aside className="avatar-assistant" aria-label="Virtual nurse assistant">
      <div className="avatar-panel-head">
        <h2>Virtual Nurse</h2>
        <p aria-live="polite">{status}</p>
      </div>

      <div className="avatar-stage">
        {settings.avatarStyle === "video" ? (
          <video
            className="avatar-video"
            src="/assets/Nurse_GIF_Generation_Request.mp4"
            autoPlay
            muted
            loop
            playsInline
          />
        ) : (
          <NurseAvatar ref={mouthRef} speaking={speaking} listening={listening} />
        )}
      </div>

      {settings.captions && text && (
        <p className="avatar-captions">
          {spans.map((span, i) => (
            <span key={span.start} className={i === wordIndex ? "caption-word current" : "caption-word"}>
              {text.slice(span.start, span.end)}{" "}
            </span>
          ))}
        </p>
      )}

      {note && <p className="avatar-note">{note}</p>}

      <div className="avatar-controls">
        <button
          type="button"
          className={`voice-button ${settings.voiceEnabled ? "on" : "off"}`}
          aria-pressed={settings.voiceEnabled}
          onClick={() => updateSettings({ voiceEnabled: !settings.voiceEnabled })}
        >
          {settings.voiceEnabled ? "Voice On" : "Voice Off"}
        </button>
        <button
          type="button"
          className="voice-button"
          onClick={() => {
            setUnlocked(true);
            if (!settings.voiceEnabled) updateSettings({ voiceEnabled: true });
            lastSpokenIdRef.current = speech?.id;
            speak(text);
          }}
          disabled={!text}
        >
          {unlocked ? "Repeat" : "Start Voice"}
        </button>
        <button type="button" className="voice-button" onClick={stop} disabled={!speaking}>
          Stop
        </button>
        <button
          type="button"
          className="voice-button"
          aria-expanded={showSettings}
          onClick={() => setShowSettings((v) => !v)}
        >
          Settings
        </button>
      </div>

      {showSettings && (
        <div className="avatar-settings">
          <label>
            Voice
            <select value={settings.ttsEngine} onChange={(e) => updateSettings({ ttsEngine: e.target.value })}>
              <option value="browser">Device voice (fast, works offline)</option>
              <option value="server">AI voice (kiosk server model)</option>
            </select>
          </label>
          {settings.ttsEngine === "browser" && englishVoices.length > 0 && (
            <label>
              Device voice
              <select value={settings.voiceURI} onChange={(e) => updateSettings({ voiceURI: e.target.value })}>
                <option value="">Automatic</option>
                {englishVoices.map((v) => (
                  <option key={v.voiceURI} value={v.voiceURI}>
                    {v.name}{v.localService ? "" : " (online)"}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            Speed: {settings.rate.toFixed(1)}x
            <input
              type="range"
              min="0.7"
              max="1.4"
              step="0.1"
              value={settings.rate}
              onChange={(e) => updateSettings({ rate: Number(e.target.value) })}
            />
          </label>
          <label>
            Speech input (microphone)
            <select value={settings.sttEngine} onChange={(e) => updateSettings({ sttEngine: e.target.value })}>
              <option value="auto">Automatic</option>
              <option value="browser" disabled={!browserRecognitionAvailable()}>
                Browser recognition{browserRecognitionAvailable() ? "" : " (not supported here)"}
              </option>
              <option value="server">Kiosk server (offline Whisper)</option>
            </select>
          </label>
          <label>
            Avatar
            <select value={settings.avatarStyle} onChange={(e) => updateSettings({ avatarStyle: e.target.value })}>
              <option value="animated">Animated nurse (lip-sync, light)</option>
              <option value="video">Video nurse (no lip-sync)</option>
            </select>
          </label>
          <label className="check-item">
            <input
              type="checkbox"
              checked={settings.captions}
              onChange={(e) => updateSettings({ captions: e.target.checked })}
            />
            Show captions
          </label>
        </div>
      )}
    </aside>
  );
}
