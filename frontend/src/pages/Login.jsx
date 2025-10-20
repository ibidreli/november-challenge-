import React from 'react';

export default function Login() {
	// backend base: prefer VITE_API_BASE_URL at build time, else runtime origin
	const backendBase = (import.meta.env.VITE_API_BASE_URL || window.location.origin).replace(/\/$/, "");
	return (
		<div style={{ textAlign: 'center', marginTop: '20%' }}>
			<h2>November Challenge Login</h2>
			<a href={`${backendBase}/auth/login`}>Login with Strava</a>
		</div>
	);
}