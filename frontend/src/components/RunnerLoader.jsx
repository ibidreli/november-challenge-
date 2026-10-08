import React from "react";

export default function RunnerLoader() {
  return (
    <div
      className="runner-loader"
      role="status"
      aria-label="Challenge wird geladen"
    >
      <svg viewBox="0 0 180 120" fill="none" aria-hidden="true">
        <path className="runner-track" d="M40 107h100" />
        <ellipse className="runner-shadow" cx="89" cy="105" rx="19" ry="2" />
        <g
          className="runner-stride"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <g transform="translate(91 40)" className="runner-far">
            <g className="runner-arm runner-arm-back">
              <path d="M0 0v14l14-6" />
            </g>
          </g>
          <g transform="translate(82 62)" className="runner-far">
            <g className="runner-leg runner-leg-back">
              <path d="M0 0v20" />
              <g transform="translate(0 20)">
                <path className="runner-knee runner-knee-back" d="M0 0v19h9" />
              </g>
            </g>
          </g>
          <path className="runner-torso" d="m92 39-10 23" />
          <circle className="runner-head" cx="98" cy="24" r="7" stroke="none" />
          <g transform="translate(82 62)">
            <g className="runner-leg">
              <path d="M0 0v20" />
              <g transform="translate(0 20)">
                <path className="runner-knee" d="M0 0v19h9" />
              </g>
            </g>
          </g>
          <g transform="translate(91 40)">
            <path className="runner-arm" d="M0 0v14l14-6" />
          </g>
        </g>
      </svg>
    </div>
  );
}
