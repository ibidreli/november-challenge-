import React from 'react';

export default function Login() {
	// backend base: prefer VITE_API_BASE_URL at build time, else fallback host
	// ensure scheme present and force HTTPS (upgrade http to https) to avoid mixed-content blocking
	let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
	if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
	backendBase = backendBase.replace(/^http:\/\//i, "https://");
	backendBase = backendBase.replace(/\/$/, "");
	return (
		<div style={{ textAlign: 'center', marginTop: '20%' }}>
			<h2>November Challenge Login</h2>
			<a href={`${backendBase}/auth/login`}>Login with Strava</a>
		</div>
	);
}