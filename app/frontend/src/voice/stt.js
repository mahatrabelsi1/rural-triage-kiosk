import { postTranscription } from "../api/client";

// Two speech-to-text paths:
//  - "browser": the Web Speech API (Chrome/Edge/Safari). Fast, shows words live,
//    but Chrome/Edge send audio to an online service.
//  - "server": record 16 kHz WAV here and transcribe with Whisper on the kiosk
//    server. Works offline once the model is downloaded, and in Firefox.
// "auto" tries the browser first and falls back to the server.

const TARGET_RATE = 16000;
const MAX_RECORD_MS = 30000;

export function browserRecognitionAvailable() {
  return typeof window !== "undefined" && Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function serverRecordingAvailable() {
  return typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getUserMedia) &&
    Boolean(window.AudioContext || window.webkitAudioContext);
}

// Errors where the server path is worth trying instead of giving up.
const FALLBACK_ERRORS = new Set(["network", "service-not-allowed", "language-not-supported", "audio-capture"]);

export function startBrowserRecognition({ lang, onInterim, onFinal, onError, onEnd }) {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new Recognition();
  rec.lang = lang || navigator.language || "en-US";
  rec.interimResults = true;
  rec.continuous = false;
  rec.maxAlternatives = 1;

  let finalText = "";
  let failed = false;
  rec.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (result.isFinal) finalText += result[0].transcript;
      else interim += result[0].transcript;
    }
    onInterim?.((finalText + " " + interim).trim());
  };
  rec.onerror = (event) => {
    failed = true;
    const code = event.error || "unknown";
    onError?.({ code, canFallBack: FALLBACK_ERRORS.has(code) });
  };
  rec.onend = () => {
    if (!failed) onFinal?.(finalText.trim());
    onEnd?.();
  };
  rec.start();
  return { stop: () => rec.stop(), abort: () => rec.abort() };
}

function downsample(buffer, fromRate) {
  if (fromRate === TARGET_RATE) return buffer;
  const ratio = fromRate / TARGET_RATE;
  const out = new Float32Array(Math.floor(buffer.length / ratio));
  for (let i = 0; i < out.length; i += 1) {
    // Average the source samples that fall into this output sample (cheap low-pass).
    const start = Math.floor(i * ratio);
    const end = Math.min(buffer.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j += 1) sum += buffer[j];
    out[i] = end > start ? sum / (end - start) : 0;
  }
  return out;
}

export function encodeWav(samples, rate = TARGET_RATE) {
  const view = new DataView(new ArrayBuffer(44 + samples.length * 2));
  const write = (offset, s) => [...s].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  write(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([view], { type: "audio/wav" });
}

export async function startServerRecording({ onLevel, onAutoStop } = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  const Ctx = window.AudioContext || window.webkitAudioContext;
  const ctx = new Ctx();
  const source = ctx.createMediaStreamSource(stream);
  // ScriptProcessor is deprecated but universally supported and needs no extra file.
  const processor = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  processor.onaudioprocess = (e) => {
    const data = e.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(data));
    if (onLevel) {
      let peak = 0;
      for (let i = 0; i < data.length; i += 64) peak = Math.max(peak, Math.abs(data[i]));
      onLevel(peak);
    }
  };
  source.connect(processor);
  processor.connect(ctx.destination);

  let stopped = false;
  const timer = setTimeout(() => onAutoStop?.(), MAX_RECORD_MS);

  function cleanup() {
    clearTimeout(timer);
    processor.disconnect();
    source.disconnect();
    stream.getTracks().forEach((t) => t.stop());
    ctx.close().catch(() => {});
  }

  return {
    async stop() {
      if (stopped) return "";
      stopped = true;
      const rate = ctx.sampleRate;
      cleanup();
      const total = chunks.reduce((n, c) => n + c.length, 0);
      const merged = new Float32Array(total);
      let offset = 0;
      for (const c of chunks) {
        merged.set(c, offset);
        offset += c.length;
      }
      const result = await postTranscription(encodeWav(downsample(merged, rate)));
      return result.text || "";
    },
    cancel() {
      if (stopped) return;
      stopped = true;
      cleanup();
    },
  };
}
