import React, { useEffect } from "react";

export default function LoginButton({ onLoginComplete = () => {} }) {
	// Öffne Backend-Login direkt (Backend leitet dann zu Strava weiter).
	const onLogin = () => {
		// prefer VITE_API_BASE_URL, otherwise fall back to the known backend host
		let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
		if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
		// upgrade explicit http:// to https:// to avoid Mixed Content
		backendBase = backendBase.replace(/^http:\/\//i, "https://");
		backendBase = backendBase.replace(/\/$/, "");
		const url = `${backendBase}/auth/login`;
		const popup = window.open(url, "strava_oauth", "width=600,height=700");
		if (!popup) {
			// Popup geblockt -> normale Navigation
			window.location.href = url;
			return;
		}
		// optional: focus popup
		try { popup.focus(); } catch (e) {}
	};

	// Handle postMessage from auth popup (auth callback posts a message)
	useEffect(() => {
		function onMessage(e) {
			try {
				const data = e?.data;
				if (!data || typeof data !== "object") return;
				if (data.type === "strava_auth_complete") {
					// notify parent (refresh UI, etc.)
					if (data.success) {
						onLoginComplete(data.user || null);
					}
				}
			} catch (err) {
				// ignore malformed messages
			}
		}
		window.addEventListener("message", onMessage, false);
		return () => window.removeEventListener("message", onMessage, false);
	}, [onLoginComplete]);

	return (
		<button onClick={onLogin} aria-label="Login with Strava">
			Login with Strava
		</button>
	);
}
