import { useEffect, useState } from "react";
import { api } from "../api";
import { useToast } from "../toast.jsx";

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    role: "client",
    organisation: "",
  });

  async function load() {
    try {
      setUsers(await api("/users"));
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createUser(e) {
    e.preventDefault();
    try {
      await api("/users", { method: "POST", body: JSON.stringify(form) });
      toast.push("User created with a temporary password", "ok");
      setForm({ email: "", password: "", name: "", role: "client", organisation: "" });
      load();
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  async function toggle(user) {
    try {
      await api(`/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      toast.push(user.is_active ? "User deactivated" : "User reactivated", "ok");
      load();
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  return (
    <div className="grid">
      <section className="page-heading"><div><div className="eyebrow">Workspace / Administration</div><h1>People & access</h1><p>Manage workspace access, roles, and active accounts.</p></div></section>
      <div className="grid grid-2">
      <div className="card">
        <div className="card-head"><div><h2>Team directory</h2><p className="card-subtitle">{users.length} workspace members</p></div></div>
        <div className="team-table-scroll"><table className="table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td><div className="person-cell"><span className="avatar avatar-small">{u.name.split(" ").map((p) => p[0]).slice(0, 2).join("")}</span><b>{u.name}</b></div></td>
                <td>{u.email}</td>
                <td><span className={`role-badge role-${u.role}`}>{u.role}</span></td>
                <td><span className={`badge ${u.is_active ? "accepted" : "rejected"}`}>{u.is_active ? "Active" : "Inactive"}</span></td>
                <td><button className="ghost" onClick={() => toggle(u)}>{u.is_active ? "Deactivate" : "Activate"}</button></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
      <form className="card form-stack" onSubmit={createUser}>
        <div><h2>Create user</h2><p className="card-subtitle">Invite a new member with the right access level.</p></div>
        <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label>Email<input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
        <label>Temporary password<input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><small>The user must replace this password on first login.</small></label>
        <label>
          Role
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="client">client</option>
            <option value="operator">operator</option>
            <option value="admin">admin</option>
          </select>
        </label>
        <label>Organisation<input value={form.organisation} onChange={(e) => setForm({ ...form, organisation: e.target.value })} /></label>
        <button>Create</button>
      </form>
      </div>
    </div>
  );
}
