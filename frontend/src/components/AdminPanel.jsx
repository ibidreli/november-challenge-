import React, { useState, useEffect } from "react";
import axios from "axios";
import "./AdminPanel.css";

export default function AdminPanel() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [adminToken, setAdminToken] = useState(localStorage.getItem("adminToken"));
  const [password, setPassword] = useState("");
  const [activeTab, setActiveTab] = useState("users"); // "users" | "activities"
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userActivities, setUserActivities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Form states
  const [newUserName, setNewUserName] = useState("");
  const [newActivityDate, setNewActivityDate] = useState("");
  const [newActivityDistance, setNewActivityDistance] = useState("");

  const API_BASE = "";

  useEffect(() => {
    if (adminToken) {
      setIsLoggedIn(true);
      loadUsers();
    }
  }, [adminToken]);

  // ===== AUTH =====
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/admin/login`, null, {
        params: { password },
        headers: {
          "X-Admin-Token": adminToken || "",
        },
      });
      const token = response.data.token;
      setAdminToken(token);
      localStorage.setItem("adminToken", token);
      setIsLoggedIn(true);
      setPassword("");
      setSuccess("Logged in successfully!");
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(
        `${API_BASE}/admin/logout`,
        {},
        {
          headers: { "X-Admin-Token": adminToken },
        }
      );
    } catch (e) {
      console.error("Logout error:", e);
    }
    setAdminToken(null);
    setIsLoggedIn(false);
    localStorage.removeItem("adminToken");
    setSelectedUser(null);
    setUserActivities([]);
  };

  // ===== USER MANAGEMENT =====
  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/admin/users`, {
        headers: { "X-Admin-Token": adminToken },
      });
      setUsers(response.data);
      setError("");
    } catch (err) {
      setError("Failed to load users");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUserName.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    try {
      await axios.post(
        `${API_BASE}/admin/users`,
        null,
        {
          params: { name: newUserName },
          headers: { "X-Admin-Token": adminToken },
        }
      );
      setSuccess("User created successfully!");
      setNewUserName("");
      loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Delete this user and all their data?")) return;
    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/admin/users/${userId}`, {
        headers: { "X-Admin-Token": adminToken },
      });
      setSuccess("User deleted!");
      loadUsers();
      if (selectedUser?.id === userId) {
        setSelectedUser(null);
        setUserActivities([]);
      }
    } catch (err) {
      setError("Failed to delete user");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = async (user) => {
    setSelectedUser(user);
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/admin/users/${user.id}/activities`, {
        headers: { "X-Admin-Token": adminToken },
      });
      setUserActivities(response.data);
    } catch (err) {
      setError("Failed to load activities");
    } finally {
      setLoading(false);
    }
  };

  // ===== ACTIVITY MANAGEMENT =====
  const handleAddActivity = async (e) => {
    e.preventDefault();
    if (!selectedUser) {
      setError("Select a user first");
      return;
    }
    if (!newActivityDate || !newActivityDistance) {
      setError("Date and distance are required");
      return;
    }
    setLoading(true);
    try {
      await axios.post(
        `${API_BASE}/admin/users/${selectedUser.id}/activities`,
        null,
        {
          params: {
            date: newActivityDate,
            distance_km: parseFloat(newActivityDistance),
          },
          headers: { "X-Admin-Token": adminToken },
        }
      );
      setSuccess("Activity created!");
      setNewActivityDate("");
      setNewActivityDistance("");
      handleSelectUser(selectedUser); // Reload activities
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create activity");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (!window.confirm("Delete this activity?")) return;
    if (!selectedUser) return;
    setLoading(true);
    try {
      await axios.delete(
        `${API_BASE}/admin/users/${selectedUser.id}/activities/${activityId}`,
        {
          headers: { "X-Admin-Token": adminToken },
        }
      );
      setSuccess("Activity deleted!");
      handleSelectUser(selectedUser); // Reload activities
    } catch (err) {
      setError("Failed to delete activity");
    } finally {
      setLoading(false);
    }
  };

  const handleResetSlots = async (userId) => {
    if (!window.confirm("Reset all slots and score for this user?")) return;
    setLoading(true);
    try {
      await axios.post(
        `${API_BASE}/admin/users/${userId}/reset-slots`,
        {},
        {
          headers: { "X-Admin-Token": adminToken },
        }
      );
      setSuccess("Slots reset!");
      loadUsers();
      if (selectedUser?.id === userId) {
        handleSelectUser(selectedUser);
      }
    } catch (err) {
      setError("Failed to reset slots");
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER =====
  if (!isLoggedIn) {
    return (
      <div className="admin-login-container">
        <div className="admin-login-box">
          <h1>Admin Panel</h1>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Admin Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
            <button type="submit" disabled={loading}>
              {loading ? "Logging in..." : "Login"}
            </button>
          </form>
          {error && <p className="error-message">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>Admin Panel</h1>
        <button onClick={handleLogout} className="logout-btn">
          Logout
        </button>
      </div>

      {error && <div className="admin-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}

      <div className="admin-tabs">
        <button
          className={`tab-btn ${activeTab === "users" ? "active" : ""}`}
          onClick={() => setActiveTab("users")}
        >
          Users
        </button>
        <button
          className={`tab-btn ${activeTab === "activities" ? "active" : ""}`}
          onClick={() => setActiveTab("activities")}
        >
          Activities
        </button>
      </div>

      {/* USERS TAB */}
      {activeTab === "users" && (
        <div className="admin-section">
          <h2>Manage Players</h2>

          <div className="add-user-form">
            <h3>Add New Player</h3>
            <form onSubmit={handleAddUser}>
              <input
                type="text"
                placeholder="Player Name"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                disabled={loading}
              />
              <button type="submit" disabled={loading}>
                {loading ? "Adding..." : "Add Player"}
              </button>
            </form>
          </div>

          <div className="users-list">
            <h3>Existing Players ({users.length})</h3>
            {users.length === 0 ? (
              <p>No players found</p>
            ) : (
              <div className="users-grid">
                {users.map((user) => (
                  <div key={user.id} className="user-card">
                    <h4>{user.name}</h4>
                    <p>Score: {user.total_score}</p>
                    <p>Total KM: {user.km_total || 0}</p>
                    <div className="user-actions">
                      <button
                        className="edit-btn"
                        onClick={() => handleSelectUser(user)}
                      >
                        Edit Activities
                      </button>
                      <button
                        className="reset-btn"
                        onClick={() => handleResetSlots(user.id)}
                      >
                        Reset
                      </button>
                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteUser(user.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ACTIVITIES TAB */}
      {activeTab === "activities" && (
        <div className="admin-section">
          <h2>Manage Activities</h2>

          {selectedUser ? (
            <>
              <div className="selected-user-info">
                <h3>Player: {selectedUser.name}</h3>
                <button
                  className="change-user-btn"
                  onClick={() => {
                    setSelectedUser(null);
                    setUserActivities([]);
                  }}
                >
                  Change Player
                </button>
              </div>

              <div className="add-activity-form">
                <h4>Add Activity</h4>
                <form onSubmit={handleAddActivity}>
                  <input
                    type="date"
                    value={newActivityDate}
                    onChange={(e) => setNewActivityDate(e.target.value)}
                    disabled={loading}
                  />
                  <input
                    type="number"
                    placeholder="Distance (km)"
                    step="0.1"
                    min="0"
                    value={newActivityDistance}
                    onChange={(e) => setNewActivityDistance(e.target.value)}
                    disabled={loading}
                  />
                  <button type="submit" disabled={loading}>
                    {loading ? "Adding..." : "Add Activity"}
                  </button>
                </form>
              </div>

              <div className="activities-list">
                <h4>Activities ({userActivities.length})</h4>
                {userActivities.length === 0 ? (
                  <p>No activities</p>
                ) : (
                  <table className="activities-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Distance (km)</th>
                        <th>Effective KM</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {userActivities.map((activity) => (
                        <tr key={activity.id}>
                          <td>{activity.date}</td>
                          <td>{activity.distance_km.toFixed(2)}</td>
                          <td>{activity.effective_km || "-"}</td>
                          <td>{activity.is_manual ? "Manual" : "Strava"}</td>
                          <td>{activity.status}</td>
                          <td>
                            {activity.is_manual && (
                              <button
                                className="delete-activity-btn"
                                onClick={() => handleDeleteActivity(activity.id)}
                              >
                                Delete
                              </button>
                            )}
                            {!activity.is_manual && <span>Read-only</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          ) : (
            <div className="select-user-prompt">
              <p>Select a player to manage their activities</p>
              <div className="users-list-for-activities">
                {users.map((user) => (
                  <button
                    key={user.id}
                    className="user-select-btn"
                    onClick={() => handleSelectUser(user)}
                  >
                    {user.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
