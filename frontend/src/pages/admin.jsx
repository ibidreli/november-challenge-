import React, { useEffect, useState } from "react";
import axios from "axios";

export default function AdminPage() {
  const [secret, setSecret] = useState(sessionStorage.getItem("admin_secret") || "");
  const [authOk, setAuthOk] = useState(!!sessionStorage.getItem("admin_secret"));
  const [users, setUsers] = useState([]);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newUserName, setNewUserName] = useState("");
  const [newActivity, setNewActivity] = useState({ user_id: "", distance_km: "", date: "" });
  const [msg, setMsg] = useState("");

  // helper: set header globally
  function applySecret(s) {
    if (s) {
      axios.defaults.headers.common["X-Admin-Secret"] = s;
      sessionStorage.setItem("admin_secret", s);
    } else {
      delete axios.defaults.headers.common["X-Admin-Secret"];
      sessionStorage.removeItem("admin_secret");
    }
  }

  useEffect(() => {
    if (authOk) {
      applySecret(secret);
      loadUsers();
      loadActivities();
    } else {
      applySecret(null);
    }
    // eslint-disable-next-line
  }, [authOk]);

  async function login(e) {
    e && e.preventDefault();
    if (!secret) { setMsg("Bitte Passwort eingeben"); return; }
    applySecret(secret);
    try {
      // test call
      await axios.get("/api/admin/users");
      setAuthOk(true);
      setMsg("Eingeloggt");
    } catch (err) {
      applySecret(null);
      setAuthOk(false);
      setMsg("Login fehlgeschlagen (ungültiges Passwort?)");
    }
  }

  function logout() {
    setAuthOk(false);
    setSecret("");
    applySecret(null);
    setMsg("Ausgeloggt");
  }

  async function loadUsers() {
    setLoading(true);
    try {
      const r = await axios.get("/api/admin/users");
      setUsers(r.data || []);
    } catch (e) {
      setMsg("Fehler beim Laden der Nutzer");
      setUsers([]);
    } finally { setLoading(false); }
  }

  async function loadActivities() {
    setLoading(true);
    try {
      const r = await axios.get("/api/admin/activities");
      setActivities(r.data.items || []);
    } catch (e) {
      setMsg("Fehler beim Laden der Aktivitäten");
      setActivities([]);
    } finally { setLoading(false); }
  }

  async function createUser() {
    if (!newUserName || newUserName.trim().length === 0) return setMsg("Name erforderlich");
    try {
      const r = await axios.post("/api/admin/users?name=" + encodeURIComponent(newUserName.trim()));
      setMsg("User erstellt: id " + (r.data.id || "?"));
      setNewUserName("");
      await loadUsers();
    } catch (e) {
      setMsg("Create user failed");
    }
  }

  async function createActivity() {
    const { user_id, distance_km, date } = newActivity;
    if (!user_id || !distance_km) return setMsg("user_id und distance_km erforderlich");
    try {
      await axios.post(`/api/admin/activities?user_id=${encodeURIComponent(user_id)}&distance_km=${encodeURIComponent(distance_km)}${date ? "&date_str="+encodeURIComponent(date): ""}`);
      setMsg("Aktivität erstellt");
      setNewActivity({ user_id: "", distance_km: "", date: "" });
      await loadActivities();
    } catch (e) {
      setMsg("Create activity failed");
    }
  }

  async function deleteActivity(id) {
    if (!window.confirm("Aktivität löschen?")) return;
    try {
      await axios.delete(`/api/admin/activities/${id}`);
      setMsg("Aktivität gelöscht");
      await loadActivities();
    } catch (e) {
      setMsg("Delete failed");
    }
  }

  if (!authOk) {
    return (
      <div style={{ padding: 18 }}>
        <h2>Admin Login</h2>
        <form onSubmit={login}>
          <div style={{ marginBottom: 8 }}>
            <input type="password" value={secret} onChange={(e)=>setSecret(e.target.value)} placeholder="Admin Passwort" style={{ padding: 8, width: 320 }} />
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn primary" onClick={login}>Login</button>
            <button className="btn" onClick={() => { setSecret(""); applySecret(null); }}>Reset</button>
          </div>
        </form>
        <div style={{ marginTop: 12, color: "#666" }}>{msg}</div>
      </div>
    );
  }

  return (
    <div style={{ padding: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Admin Console</h2>
        <div>
          <button className="btn" onClick={logout}>Logout</button>
          <button className="btn" onClick={()=>{ loadUsers(); loadActivities(); }}>Refresh</button>
        </div>
      </div>

      <div style={{ color: "#444", marginBottom: 12 }}>{msg}</div>

      <section style={{ marginBottom: 18 }}>
        <h3>Users</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input placeholder="Neuer Name" value={newUserName} onChange={(e)=>setNewUserName(e.target.value)} />
          <button className="btn primary" onClick={createUser}>Erstelle Nutzer</button>
        </div>
        <div style={{ marginTop: 8 }}>
          {loading ? <div>Lädt…</div> : (
            <ul>
              {users.map(u => <li key={u.id}>{u.id} — {u.name} — strava_id: {u.strava_id}</li>)}
            </ul>
          )}
        </div>
      </section>

      <section style={{ marginBottom: 18 }}>
        <h3>Aktivitäten</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input placeholder="user_id" value={newActivity.user_id} onChange={(e)=>setNewActivity({...newActivity, user_id: e.target.value})} style={{ width: 80 }} />
          <input placeholder="distance_km" value={newActivity.distance_km} onChange={(e)=>setNewActivity({...newActivity, distance_km: e.target.value})} style={{ width: 120 }} />
          <input placeholder="YYYY-MM-DD" value={newActivity.date} onChange={(e)=>setNewActivity({...newActivity, date: e.target.value})} style={{ width: 140 }} />
          <button className="btn primary" onClick={createActivity}>Add Activity</button>
        </div>

        <div style={{ marginTop: 12 }}>
          {loading ? <div>Lädt…</div> : (
            <div style={{ display: "grid", gap: 6 }}>
              {activities.map(a => (
                <div key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 8, border: "1px solid #eee", borderRadius: 6 }}>
                  <div>{a.id} — user:{a.user_id} — {a.date} — {a.distance_km}km — {a.status}</div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn" onClick={()=>deleteActivity(a.id)}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
