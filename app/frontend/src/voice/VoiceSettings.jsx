import { createContext, useCallback, useContext, useMemo, useState } from "react";

const STORAGE_KEY = "triage-voice-settings";

export const DEFAULT_VOICE_SETTINGS = {
  voiceEnabled: true,
  // "browser" = device voice (instant, offline, lightest); "server" = AI voice model.
  ttsEngine: "browser",
  voiceURI: "",
  rate: 1,
  captions: true,
  // "animated" = SVG nurse with lip-sync (light); "video" = looping clip, no lip-sync.
  avatarStyle: "animated",
  // "auto" tries browser recognition then the kiosk server.
  sttEngine: "auto",
};

function loadSettings() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_VOICE_SETTINGS, ...JSON.parse(raw) } : DEFAULT_VOICE_SETTINGS;
  } catch {
    return DEFAULT_VOICE_SETTINGS;
  }
}

// Fired when the microphone opens so the avatar doesn't talk over (or get
// recorded by) the patient.
export const STOP_SPEAKING_EVENT = "avatar:stop-speaking";

const VoiceSettingsContext = createContext({
  settings: DEFAULT_VOICE_SETTINGS,
  updateSettings: () => {},
  listening: false,
  setListening: () => {},
});

export function VoiceSettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadSettings);
  const [listening, setListening] = useState(false);

  const updateSettings = useCallback((patch) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // per-device convenience only
      }
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ settings, updateSettings, listening, setListening }),
    [settings, updateSettings, listening],
  );
  return <VoiceSettingsContext.Provider value={value}>{children}</VoiceSettingsContext.Provider>;
}

export function useVoiceSettings() {
  return useContext(VoiceSettingsContext);
}
