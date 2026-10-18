import { postSpeech } from "../api/client";
import { CHARS_PER_SECOND } from "./lipsync";

// Both speakers return a controller: { stop(), sampler() }. sampler() is polled
// by the lip-sync loop and returns { cursor, char, amplitude? } or null.

const FEMALE_VOICE_HINTS = [
  "female", "woman", "zira", "susan", "samantha", "aria", "jenny", "sonia",
  "libby", "natasha", "moira", "tessa", "victoria", "karen", "google us english",
];

export function splitSentences(text, maxLength = 220) {
  const chunks = [];
  const re = /[^.!?]+[.!?]*\s*/g;
  let m;
  while ((m = re.exec(text))) {
    const piece = m[0];
    if (!piece.trim()) continue;
    const last = chunks[chunks.length - 1];
    if (last && last.text.length + piece.length <= maxLength && last.text.length < 40) {
      last.text += piece;
    } else {
      chunks.push({ text: piece, offset: m.index });
    }
  }
  return chunks.length ? chunks : [{ text, offset: 0 }];
}

export function hasBrowserVoice() {
  return typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
}

export function listBrowserVoices() {
  if (!hasBrowserVoice()) return [];
  return window.speechSynthesis.getVoices();
}

export function waitForVoices(timeoutMs = 800) {
  if (!hasBrowserVoice()) return Promise.resolve([]);
  const voices = window.speechSynthesis.getVoices();
  if (voices.length) return Promise.resolve(voices);
  return new Promise((resolve) => {
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener?.("voiceschanged", done, { once: true });
    setTimeout(done, timeoutMs);
  });
}

function pickVoice(voiceURI) {
  const voices = listBrowserVoices();
  if (voiceURI) {
    const chosen = voices.find((v) => v.voiceURI === voiceURI);
    if (chosen) return chosen;
  }
  const english = voices.filter((v) => v.lang?.toLowerCase().startsWith("en"));
  // Prefer voices installed on the device: they keep working offline.
  const pool = english.filter((v) => v.localService).length ? english.filter((v) => v.localService) : english;
  return (
    pool.find((v) => FEMALE_VOICE_HINTS.some((hint) => v.name.toLowerCase().includes(hint))) ||
    pool[0] ||
    voices[0] ||
    null
  );
}

export async function speakWithBrowser(text, { rate = 1, voiceURI = "", onEnd, onError } = {}) {
  if (!hasBrowserVoice()) throw new Error("This device has no built-in voice.");
  await waitForVoices();
  const synth = window.speechSynthesis;
  synth.cancel();

  const voice = pickVoice(voiceURI);
  const chunks = splitSentences(text);
  const state = { active: false, base: 0, baseTime: 0, chunkEnd: 0 };
  let cancelled = false;
  let index = 0;

  function next() {
    if (cancelled) return;
    if (index >= chunks.length) {
      state.active = false;
      onEnd?.();
      return;
    }
    const chunk = chunks[index++];
    const utterance = new SpeechSynthesisUtterance(chunk.text);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    utterance.rate = rate;
    utterance.pitch = 1.1;
    utterance.onstart = () => {
      state.active = true;
      state.base = chunk.offset;
      state.baseTime = performance.now();
      state.chunkEnd = chunk.offset + chunk.text.length;
    };
    // Word boundaries re-sync the lip-sync cursor to what is actually being said.
    utterance.onboundary = (e) => {
      if (e.name && e.name !== "word") return;
      state.base = chunk.offset + e.charIndex;
      state.baseTime = performance.now();
    };
    utterance.onend = next;
    utterance.onerror = (e) => {
      if (cancelled || e.error === "interrupted" || e.error === "canceled") return;
      state.active = false;
      onError?.(new Error(`Device voice failed (${e.error || "unknown"})`));
    };
    synth.speak(utterance);
  }

  next();

  return {
    stop() {
      cancelled = true;
      state.active = false;
      synth.cancel();
    },
    sampler() {
      if (!state.active) return null;
      const elapsed = (performance.now() - state.baseTime) / 1000;
      const cursor = Math.min(state.chunkEnd - 1, state.base + elapsed * CHARS_PER_SECOND * rate);
      return { cursor, char: text[Math.floor(cursor)] };
    },
  };
}

let audioContext = null;

function getAudioContext() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) throw new Error("Audio playback is not supported on this device.");
  if (!audioContext) audioContext = new Ctx();
  return audioContext;
}

async function fetchChunkAudio(ctx, chunkText) {
  const blob = await postSpeech(chunkText);
  return ctx.decodeAudioData(await blob.arrayBuffer());
}

// Server-side AI voice. Throws before playing if the first chunk can't be
// generated, so the caller can fall back to the device voice.
export async function speakWithServer(text, { rate = 1, onEnd, onError } = {}) {
  const ctx = getAudioContext();
  if (ctx.state === "suspended") await ctx.resume();

  const chunks = splitSentences(text, 700);
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  analyser.connect(ctx.destination);
  const samples = new Float32Array(analyser.fftSize);

  const state = { source: null, buffer: null, chunk: null, startedAt: 0 };
  let cancelled = false;
  let pending = fetchChunkAudio(ctx, chunks[0].text);
  const first = await pending;

  function play(index, buffer) {
    if (cancelled) return;
    const chunk = chunks[index];
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = rate;
    source.connect(analyser);
    Object.assign(state, { source, buffer, chunk, startedAt: ctx.currentTime });

    // Fetch the next sentence while this one plays.
    pending = index + 1 < chunks.length ? fetchChunkAudio(ctx, chunks[index + 1].text) : null;
    source.onended = async () => {
      if (cancelled) return;
      if (!pending) {
        state.source = null;
        onEnd?.();
        return;
      }
      try {
        play(index + 1, await pending);
      } catch (err) {
        state.source = null;
        onError?.(err);
      }
    };
    source.start();
  }

  play(0, first);

  return {
    stop() {
      cancelled = true;
      try {
        state.source?.stop();
      } catch {
        // already stopped
      }
      state.source = null;
      analyser.disconnect();
    },
    sampler() {
      if (!state.source || !state.buffer) return null;
      const progress = Math.min(1, ((ctx.currentTime - state.startedAt) * rate) / state.buffer.duration);
      const cursor = state.chunk.offset + progress * (state.chunk.text.length - 1);
      analyser.getFloatTimeDomainData(samples);
      let sum = 0;
      for (let i = 0; i < samples.length; i += 1) sum += samples[i] * samples[i];
      return { cursor, char: text[Math.floor(cursor)], amplitude: Math.sqrt(sum / samples.length) };
    },
  };
}
