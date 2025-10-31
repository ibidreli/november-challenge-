import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Admin() {
  const [token, setToken] = useState(sessionStorage.getItem("admin_token") || null);
  const [password, setPassword] = useState("");
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["x-admin-token"] = token;
      loadPlayers();
    } else {
      delete axios.defaults.headers.common["x-admin-token"];
    }
    // eslint-disable-next-line
  }, [token]);

  async function login(e) {
    e && e.preventDefault();
    setMsg("");
    try {
      const r = await axios.post("/admin/login", { password });
      const t = r.data.token;
      sessionStorage.setItem("admin_token", t);
      setToken(t);
    } catch (err) {
      setMsg("Login failed");
      console.error(err);
    }
  }

  async function loadPlayers() {
    setLoading(true);
    try {
      const r = await axios.get("/admin/players");
      setPlayers(r.data || []);
    } catch (err) {
      console.error("loadPlayers", err);
      setMsg("Could not load players (check admin token)");
    } finally {
      setLoading(false);
    }
  }

  async function createPlayer(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const name = form.get("name");
    const strava_id = form.get("strava_id") || undefined;
    try {
      await axios.post("/admin/player", { name, strava_id });
      setMsg("Player created");
      await loadPlayers();
      e.target.reset();
    } catch (err) {
      console.error(err);
      setMsg("Failed to create player");
    }
  }

  async function deletePlayer(id) {
    if (!window.confirm("Delete player and related activities?")) return;
    try {
      await axios.delete(`/admin/player/${id}`);
      setMsg("Deleted");
      await loadPlayers();
    } catch (err) {
      console.error(err);
      setMsg("Failed to delete");
    }
  }

  async function addActivity(e) {
    e.preventDefault();
    const form = new FormData(e.target);
    const user_id = form.get("user_id") || undefined;
    const strava_id = form.get("strava_id") || undefined;
    const date = form.get("date");
    const km = Number(form.get("km") || 0);
    try {
      await axios.post("/admin/activity", { user_id, strava_id, date, km });
      setMsg("Activity added");
      await loadPlayers();
      e.target.reset();
    } catch (err) {
      console.error(err);
      setMsg("Failed to add activity");
    }
  }

  async function deleteActivity(id) {
    if (!window.confirm("Delete activity?")) return;
    try {
      await axios.delete(`/admin/activity/${id}`);
      setMsg("Activity deleted");
      await loadPlayers();
    } catch (err) {
      console.error(err);
      setMsg("Failed to delete activity");
    }
  }

  if (!token) {
    return (
      <div style={{ padding: 20 }}>
        <h2>Admin Login</h2>
        <form onSubmit={login}>
          <input placeholder="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button type="submit" style={{ marginLeft: 8 }}>Login</button>
        </form>
        <div style={{ color: "red", marginTop: 8 }}>{msg}</div>
      </div>
    );
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>Admin</h2>
      <div style={{ marginBottom: 12 }}>
        <button onClick={() => { sessionStorage.removeItem("admin_token"); setToken(null); setMsg("logged out"); }}>Logout</button>
        <button onClick={loadPlayers} style={{ marginLeft: 8 }}>Refresh</button>
      </div>
      <div style={{ color: "#666", marginBottom: 12 }}>{msg}</div>

      <section style={{ marginBottom: 20 }}>
        <h3>Create player</h3>
        <form onSubmit={createPlayer}>
          <input name="name" placeholder="Name" required />
          <input name="strava_id" placeholder="strava_id (optional)" style={{ marginLeft: 8 }} />
          <button type="submit" style={{ marginLeft: 8 }}>Create</button>
        </form>
      </section>

      <section style={{ marginBottom: 20 }}>
        <h3>Add activity (manual)</h3>
        <form onSubmit={addActivity}>
          <input name="user_id" placeholder="user_id (preferred)" />
          <input name="strava_id" placeholder="or strava_id" style={{ marginLeft: 8 }} />
          <input name="date" placeholder="YYYY-MM-DD" style={{ marginLeft: 8 }} required />
          <input name="km" placeholder="km" style={{ width: 80, marginLeft: 8 }} required />
          <button type="submit" style={{ marginLeft: 8 }}>Add</button>
        </form>
      </section>

      <section>
        <h3>Players</h3>
        {loading ? <div>Loading…</div> : (
          <div>
            {players.map((p) => (
              <div key={p.id} style={{ border: "1px solid #eee", padding: 8, marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{p.name} (id:{p.id})</div>
                    <div style={{ color: "#666" }}>strava_id: {p.strava_id}</div>
                    <div style={{ color: "#666" }}>score: {p.total_score}</div>
                  </div>
                  <div>
                    <button onClick={() => deletePlayer(p.id)}>Delete player</button>
                  </div>
                </div>
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 13, color: "#444" }}>Slots preview:</div>
                  <pre style={{ background: "#fafafa", padding: 8 }}>{JSON.stringify(p.slots || [], null, 2)}</pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
