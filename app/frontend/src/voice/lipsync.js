// Lightweight lip-sync: map the letter currently being spoken to a mouth shape
// ("viseme") and ease an SVG mouth toward it. No ML model, no video decoding:
// one requestAnimationFrame loop that only runs while the avatar is speaking.

// Mouth half-width (w) and opening height (h) in SVG units for each shape.
const SHAPES = {
  rest: { w: 13, h: 1.2 },
  closed: { w: 12, h: 0.4 },
  open: { w: 13, h: 15 },
  wide: { w: 17, h: 8 },
  round: { w: 8, h: 12 },
  fv: { w: 13, h: 4 },
};

const VOWELS = { a: "open", e: "wide", i: "wide", y: "wide", o: "round", u: "round", w: "round" };

export function visemeFor(char) {
  const c = (char || "").toLowerCase();
  if (VOWELS[c]) return { shape: VOWELS[c], open: c === "a" ? 1 : 0.85 };
  if (c === "m" || c === "b" || c === "p") return { shape: "closed", open: 0 };
  if (c === "f" || c === "v") return { shape: "fv", open: 0.4 };
  if (/[a-z0-9]/.test(c)) return { shape: "open", open: 0.35 };
  return { shape: "rest", open: 0 };
}

// Upper lip is a shallow curve, lower lip a deeper one; the gap is the mouth opening.
export function mouthPath(w, h, cx = 100, cy = 146) {
  const top = cy - Math.min(h, 6) * 0.35;
  const bottom = cy + h;
  return `M ${cx - w} ${cy} Q ${cx} ${top} ${cx + w} ${cy} Q ${cx} ${bottom} ${cx - w} ${cy} Z`;
}

export const REST_PATH = mouthPath(SHAPES.rest.w, SHAPES.rest.h);

// Average speaking speed used to estimate where in the text the voice is when
// the browser doesn't report word boundaries (some voices never do).
export const CHARS_PER_SECOND = 14;

export function createLipSync(applyPath) {
  let raf = 0;
  let sampler = null;
  let w = SHAPES.rest.w;
  let h = SHAPES.rest.h;

  function frame() {
    const sample = sampler ? sampler() : null;
    let target = SHAPES.rest;
    let open = 0;
    if (sample) {
      const vis = visemeFor(sample.char);
      target = SHAPES[vis.shape];
      open = vis.open;
      // With real audio, loudness drives how wide the mouth opens.
      if (typeof sample.amplitude === "number") {
        open = sample.amplitude < 0.02 ? 0 : Math.min(1, 0.35 * open + 1.6 * sample.amplitude);
        if (open === 0) target = SHAPES.rest;
      }
    }
    const targetW = SHAPES.rest.w + (target.w - SHAPES.rest.w) * Math.max(open, 0.3);
    const targetH = target === SHAPES.closed ? target.h : SHAPES.rest.h + (target.h - SHAPES.rest.h) * open;
    w += (targetW - w) * 0.45;
    h += (targetH - h) * 0.45;
    applyPath(mouthPath(w, h));
    raf = sampler ? requestAnimationFrame(frame) : 0;
  }

  return {
    start(nextSampler) {
      sampler = nextSampler;
      if (!raf) raf = requestAnimationFrame(frame);
    },
    stop() {
      sampler = null;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      w = SHAPES.rest.w;
      h = SHAPES.rest.h;
      applyPath(REST_PATH);
    },
  };
}

// Word spans for caption highlighting: [{start, end}] character ranges.
export function wordSpans(text) {
  const spans = [];
  const re = /\S+/g;
  let m;
  while ((m = re.exec(text))) spans.push({ start: m.index, end: m.index + m[0].length });
  return spans;
}

export function wordIndexAt(spans, cursor) {
  for (let i = 0; i < spans.length; i += 1) {
    if (cursor < spans[i].end) return i;
  }
  return spans.length - 1;
}
