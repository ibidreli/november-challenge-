import React, { useEffect, useRef } from "react";

const duration = "0.85s";
const ankles = [
  [101, 100],
  [88, 101],
  [75, 100],
  [63, 95],
  [64, 79],
  [78, 70],
  [98, 78],
  [107, 90],
];
const bounce = [0, -1, -2, -1, 0, -1, -2, -1];
const point = (x, y) => `${x.toFixed(2)} ${y.toFixed(2)}`;

function leg(frame, offset = 0) {
  const [x, y] = ankles[(frame + offset) % 8];
  const hip = [82, 62 + bounce[frame]];
  const dx = x - hip[0],
    dy = y - hip[1];
  const distance = Math.hypot(dx, dy);
  // Two equal bones, with the knee always bending forwards. The planted foot
  // stays on the ground while the hip rises, rather than rotating independently.
  const bend = Math.sqrt(24 ** 2 - (distance / 2) ** 2);
  const knee = [
    hip[0] + dx / 2 + (dy / distance) * bend,
    hip[1] + dy / 2 - (dx / distance) * bend,
  ];
  return `M${point(...hip)} L${point(...knee)} L${point(x, y)} l8 0`;
}

function arm(frame, offset = 0) {
  const angle =
    (-35 * Math.cos(((frame + offset) * Math.PI) / 4) * Math.PI) / 180;
  const shoulder = [92, 40 + bounce[frame]];
  const elbow = [
    shoulder[0] + Math.sin(angle) * 14,
    shoulder[1] + Math.cos(angle) * 14,
  ];
  const forearm = angle + (110 * Math.PI) / 180;
  const hand = [
    elbow[0] + Math.sin(forearm) * 14,
    elbow[1] + Math.cos(forearm) * 14,
  ];
  return `M${point(...shoulder)} L${point(...elbow)} L${point(...hand)}`;
}

const cycle = (make) => Array.from({ length: 9 }, (_, i) => make(i % 8));
const paths = [
  { name: "back-arm", far: true, poses: cycle((i) => arm(i, 4)) },
  { name: "back-leg", far: true, poses: cycle((i) => leg(i, 4)) },
  {
    name: "torso",
    poses: cycle((i) => `M92 ${39 + bounce[i]} L82 ${62 + bounce[i]}`),
  },
  { name: "front-leg", poses: cycle((i) => leg(i)) },
  { name: "front-arm", poses: cycle((i) => arm(i)) },
];

export default function RunnerLoader() {
  const svg = useRef(null);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      if (preference.matches) {
        svg.current.pauseAnimations();
        svg.current.setCurrentTime(0);
      } else svg.current.unpauseAnimations();
    };
    update();
    preference.addEventListener("change", update);
    return () => preference.removeEventListener("change", update);
  }, []);
  return (
    <div
      className="runner-loader"
      role="status"
      aria-label="Challenge wird geladen"
    >
      <svg ref={svg} viewBox="0 0 180 120" fill="none" aria-hidden="true">
        <path className="runner-track" d="M40 104h100" />
        <ellipse className="runner-shadow" cx="89" cy="103" rx="19" ry="2" />
        <g
          className="runner-stride"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {paths.map(({ name, far, poses }) => (
            <path
              key={name}
              className={`runner-${name}${far ? " runner-far" : ""}`}
              d={poses[0]}
            >
              <animate
                attributeName="d"
                values={poses.join(";")}
                dur={duration}
                repeatCount="indefinite"
              />
            </path>
          ))}
          <circle className="runner-head" cx="98" cy="24" r="7" stroke="none">
            <animate
              attributeName="cy"
              values={cycle((i) => 24 + bounce[i]).join(";")}
              dur={duration}
              repeatCount="indefinite"
            />
          </circle>
        </g>
      </svg>
    </div>
  );
}
