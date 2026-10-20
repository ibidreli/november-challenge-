import React from "react";

export const WHATSAPP_INVITE_URL =
  "https://chat.whatsapp.com/K7tBs2IaLR8LxZMd2Ntp7c";

export default function WhatsAppNotice() {
  return (
    <a
      className="whatsapp-notice"
      href={WHATSAPP_INVITE_URL}
      target="_blank"
      rel="noopener noreferrer"
      title="WhatsApp öffnen (neuer Tab)"
    >
      <svg
        className="whatsapp-notice-icon"
        viewBox="0 0 24 24"
        width="22"
        height="22"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M20.8 11.4a8.8 8.8 0 0 1-13.2 7.6L3 20.2l1.2-4.4a8.8 8.8 0 1 1 16.6-4.4Z" />
        <path d="M8 7h2l1 3-1.3 1.2a7.2 7.2 0 0 0 3.1 3.1L14 13l3 1v2a1 1 0 0 1-1 1A9 9 0 0 1 7 8a1 1 0 0 1 1-1Z" />
      </svg>
      <span className="whatsapp-notice-description">
        Infos & Ankündigungen zur Challenge
      </span>
      <span className="whatsapp-notice-action">
        WhatsApp beitreten <span aria-hidden="true">↗</span>
      </span>
    </a>
  );
}
