import React, { useEffect } from "react";

export default function LoginButton({ onLoginComplete = () => {} }) {
	// Öffne Backend-Login direkt (Backend leitet dann zu Strava weiter).
	const onLogin = () => {
		// prefer VITE_API_BASE_URL, otherwise fall back to known backend host; ensure HTTPS
		let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
		// add scheme if missing, upgrade explicit http to https
		if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
		backendBase = backendBase.replace(/^http:\/\//i, "https://");
		backendBase = backendBase.replace(/\/$/, "");
		const url = `${backendBase}/auth/login`;
		const popup = window.open(url, "strava_oauth", "width=600,height=700");
		if (!popup) {
			// Popup geblockt -> normale Navigation
			window.location.href = url;
			return;
		}
		try { popup.focus(); } catch (e) {}
	};

	// Handle postMessage from auth popup (auth callback posts a message)
	useEffect(() => {
		function onMessage(e) {
			try {
				const data = e?.data;
				if (!data || typeof data !== "object") return;
				if (data.type === "strava_auth_complete") {
					if (data.success) {
						// persist current user id so frontend knows who is "logged in"
						if (data.user && (data.user.id || data.user.id === 0)) {
							try {
								localStorage.setItem("nc_user_id", String(data.user.id));
							} catch (err) {
								// ignore storage errors
							}
						}
						// notify parent to refresh UI
						onLoginComplete(data.user || null);
					} else {
						// in case of failure clear stored id
						try { localStorage.removeItem("nc_user_id"); } catch (err) {}
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
		<button className="btn primary" onClick={onLogin} aria-label="Connect with Strava">
			Connect with Strava
		</button>
	);
}
