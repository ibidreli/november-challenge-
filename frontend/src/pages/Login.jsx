import React from 'react';
// logo located at frontend/logo/Logo.png (relative from src/pages -> ../../logo/...)
import logo from '../../logo/Logo.png';

export default function Login() {
	// backend base: prefer VITE_API_BASE_URL at build time, else fallback host
	// ensure scheme present and force HTTPS (upgrade http to https) to avoid mixed-content blocking
	let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
	if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
	backendBase = backendBase.replace(/^http:\/\//i, "https://");
	backendBase = backendBase.replace(/\/$/, "");

	return (
		<div style={{ display:"flex", alignItems:"center", justifyContent:"center", minHeight: "70vh" }}>
			<div style={{ width:360, textAlign:'center', padding:24, borderRadius:8, background:"#fff", boxShadow:"0 6px 20px rgba(0,0,0,0.08)" }}>
				<img src={logo} alt="logo" style={{ width:96, height:96, objectFit:"contain", marginBottom:12 }} />
				<h2>November Challenge — Connect</h2>
				<p className="muted">Connect your Strava account to participate in the challenge.</p>
				<a className="btn primary" href={`${backendBase}/auth/login`} style={{display:'inline-block', marginTop:12}}>Connect with Strava</a>
			</div>
		</div>
	);
}