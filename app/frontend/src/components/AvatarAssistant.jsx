import { useEffect, useRef, useState } from "react";

import { postSpeech } from "../api/client";

const FEMALE_VOICE_HINTS = [
  "female",
  "woman",
  "zira",
  "susan",
  "samantha",
  "aria",
  "jenny",
  "sonia",
  "libby",
  "natasha",
  "moira",
  "tessa",
  "victoria",
  "karen",
  "google us english",
];

function pickFemaleVoice() {
  if (!window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((voice) => FEMALE_VOICE_HINTS.some((hint) => voice.name.toLowerCase().includes(hint))) ||
    voices.find((voice) => voice.lang?.toLowerCase().startsWith("en")) ||
    null
  );
}

function getVoicesWhenReady() {
  if (!window.speechSynthesis) return Promise.resolve([]);
  const voices = window.speechSynthesis.getVoices();
  if (voices.length) return Promise.resolve(voices);

  return new Promise((resolve) => {
    window.speechSynthesis.onvoiceschanged = () => {
      resolve(window.speechSynthesis.getVoices());
    };
    setTimeout(() => resolve(window.speechSynthesis.getVoices()), 600);
  });
}

async function browserSpeak(text) {
  if (!window.speechSynthesis || !text) return false;
  await getVoicesWhenReady();
  const voice = pickFemaleVoice();
  if (!voice) return false;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice = voice;
  utterance.rate = 1.12;
  utterance.pitch = 1.28;
  utterance.volume = 1;
  window.speechSynthesis.speak(utterance);
  return true;
}

export default function AvatarAssistant({ speechText }) {
  const audioRef = useRef(null);
  const lastTextRef = useRef("");
  const voiceReadyRef = useRef(false);
  const [voiceBlocked, setVoiceBlocked] = useState(false);
  const [voiceReady, setVoiceReady] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  async function speak(text, force = false, preferBrowserVoice = false) {
    if (!text || (!force && text === lastTextRef.current)) return;
    lastTextRef.current = text;
    setVoiceBlocked(false);
    setSpeaking(true);

    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const usedBrowserVoice = await browserSpeak(text);
      if (usedBrowserVoice || preferBrowserVoice) {
        setVoiceBlocked(!usedBrowserVoice);
        setSpeaking(false);
        return;
      }
      const blob = await postSpeech(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        setSpeaking(false);
      };
      await audio.play();
    } catch {
      const usedBrowserVoice = await browserSpeak(text);
      setVoiceBlocked(!usedBrowserVoice);
      setSpeaking(false);
    }
  }

  useEffect(() => {
    if (voiceReady) {
      speak(speechText);
    }
  }, [speechText, voiceReady]);

  useEffect(() => {
    function startVoiceOnFirstInteraction() {
      if (voiceReadyRef.current) return;
      voiceReadyRef.current = true;
      setVoiceReady(true);
      speak(speechText, true, true);
    }

    window.addEventListener("pointerdown", startVoiceOnFirstInteraction, { once: true });
    window.addEventListener("keydown", startVoiceOnFirstInteraction, { once: true });
    return () => {
      window.removeEventListener("pointerdown", startVoiceOnFirstInteraction);
      window.removeEventListener("keydown", startVoiceOnFirstInteraction);
    };
  }, [speechText]);

  function startVoice() {
    if (voiceReadyRef.current && lastTextRef.current === speechText) return;
    voiceReadyRef.current = true;
    setVoiceReady(true);
    speak(speechText || lastTextRef.current, true, true);
  }

  return (
    <aside className="avatar-assistant" aria-label="Virtual nurse assistant">
      <div className="avatar-panel-head">
        <h2>Virtual Nurse</h2>
        <p>{speaking ? "Speaking now" : voiceReady ? "Guidance companion" : "Tap Start Voice for greeting"}</p>
      </div>
      <video
        className="avatar-video"
        src="/assets/Nurse_GIF_Generation_Request.mp4"
        autoPlay
        muted
        loop
        playsInline
      />
      <div className="avatar-caption">
        <span>Assistant View</span>
        {(!voiceReady || voiceBlocked) && (
          <button type="button" className="voice-button" onClick={startVoice}>
            {voiceReady ? "Enable Voice" : "Start Voice"}
          </button>
        )}
      </div>
    </aside>
  );
}
