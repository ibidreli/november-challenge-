import React, { useEffect, useState } from 'react';
import axios from 'axios';


export default function Login() {
const [authUrl, setAuthUrl] = useState('');


useEffect(() => {
axios.get('http://localhost:8000/auth/login').then((res) => {
setAuthUrl(res.data.auth_url);
});
}, []);


return (
<div style={{ textAlign: 'center', marginTop: '20%' }}>
<h2>November Challenge Login</h2>
<a href={authUrl}>Login with Strava</a>
</div>
);
}