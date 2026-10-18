import { forwardRef } from "react";

import { REST_PATH } from "../voice/lipsync";

// Flat SVG nurse. The mouth <path> is exposed through the ref so the lip-sync
// loop can update it directly without re-rendering React on every frame.
const NurseAvatar = forwardRef(function NurseAvatar({ speaking, listening }, mouthRef) {
  return (
    <svg
      className={`nurse-avatar ${speaking ? "is-speaking" : ""} ${listening ? "is-listening" : ""}`}
      viewBox="0 0 200 220"
      role="img"
      aria-label={speaking ? "Virtual nurse speaking" : "Virtual nurse"}
    >
      <defs>
        <linearGradient id="nurse-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#dff1fb" />
          <stop offset="100%" stopColor="#c7e3f1" />
        </linearGradient>
      </defs>
      <rect width="200" height="220" fill="url(#nurse-bg)" />

      {/* shoulders / scrubs */}
      <path d="M30 220 Q36 176 100 170 Q164 176 170 220 Z" fill="#2a9d8f" />
      <path d="M84 172 L100 196 L116 172 Z" fill="#f2c6a0" />
      <rect x="64" y="196" width="16" height="4" rx="2" fill="#e9f5f3" />

      {/* neck */}
      <rect x="88" y="150" width="24" height="26" rx="8" fill="#e8b48c" />

      {/* hair back */}
      <ellipse cx="100" cy="104" rx="56" ry="62" fill="#3b2a24" />

      {/* face */}
      <ellipse cx="100" cy="112" rx="44" ry="52" fill="#f2c6a0" />
      <ellipse cx="57" cy="116" rx="7" ry="11" fill="#e8b48c" />
      <ellipse cx="143" cy="116" rx="7" ry="11" fill="#e8b48c" />

      {/* hair fringe */}
      <path d="M56 98 Q62 54 100 52 Q140 54 146 100 Q128 76 100 74 Q74 76 56 98 Z" fill="#3b2a24" />

      {/* nurse cap */}
      <path d="M66 62 Q100 34 134 62 L128 74 Q100 62 72 74 Z" fill="#ffffff" stroke="#cfe3ea" strokeWidth="1.5" />
      <rect x="95" y="52" width="10" height="16" rx="1.5" fill="#e04f5f" />
      <rect x="92" y="55" width="16" height="10" rx="1.5" fill="#e04f5f" />

      {/* brows */}
      <path className="brow" d="M72 96 Q82 90 92 95" stroke="#3b2a24" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path className="brow" d="M108 95 Q118 90 128 96" stroke="#3b2a24" strokeWidth="3" fill="none" strokeLinecap="round" />

      {/* eyes (blink via CSS) */}
      <g className="eyes">
        <ellipse cx="82" cy="110" rx="6" ry="7" fill="#ffffff" />
        <ellipse cx="118" cy="110" rx="6" ry="7" fill="#ffffff" />
        <circle cx="83" cy="111" r="3.6" fill="#2d2420" />
        <circle cx="119" cy="111" r="3.6" fill="#2d2420" />
        <circle cx="84.2" cy="109.6" r="1.1" fill="#ffffff" />
        <circle cx="120.2" cy="109.6" r="1.1" fill="#ffffff" />
      </g>

      {/* nose + cheeks */}
      <path d="M100 116 Q96 130 101 134" stroke="#d29a74" strokeWidth="2.2" fill="none" strokeLinecap="round" />
      <ellipse cx="72" cy="132" rx="8" ry="5" fill="#f0a5a0" opacity="0.45" />
      <ellipse cx="128" cy="132" rx="8" ry="5" fill="#f0a5a0" opacity="0.45" />

      {/* mouth: driven by lip-sync */}
      <path ref={mouthRef} d={REST_PATH} fill="#9c3b49" stroke="#b3505c" strokeWidth="1.6" strokeLinejoin="round" />

      {/* listening indicator */}
      <g className="listen-waves" opacity={listening ? 1 : 0}>
        <path d="M166 92 Q174 104 166 116" stroke="#1f6fc2" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M174 84 Q188 104 174 124" stroke="#1f6fc2" strokeWidth="3" fill="none" strokeLinecap="round" />
      </g>
    </svg>
  );
});

export default NurseAvatar;
