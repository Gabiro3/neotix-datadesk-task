import { useState } from "react";
import { KeyRound, LogOut, ShieldCheck } from "lucide-react";
import { api, clearSession, saveSession } from "../api";
import { useToast } from "../toast.jsx";

export default function ChangePassword({ user, onComplete, onLogout }) {
  const toast = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (newPassword !== confirmation) {
      toast.push("New passwords do not match", "error");
      return;
    }
    setBusy(true);
    try {
      const updatedUser = await api("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      saveSession(localStorage.getItem("token"), updatedUser);
      toast.push("Password updated. Your workspace is ready.", "ok");
      onComplete(updatedUser);
    } catch (error) {
      toast.push(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearSession();
    onLogout();
  }

  return (
    <main className="password-gate">
      <form className="card password-card" onSubmit={submit}>
        <div className="password-icon"><ShieldCheck size={22} /></div>
        <div>
          <div className="kicker">First login security</div>
          <h1>Set your password</h1>
          <p className="card-subtitle">Hello {user.name}. Your administrator issued a temporary password. Replace it before entering the workspace.</p>
        </div>
        <div className="form-stack">
          <label>Temporary password<input autoFocus type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          <label>New password<input type="password" minLength="8" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          <label>Confirm new password<input type="password" minLength="8" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required /></label>
        </div>
        <div className="password-actions">
          <button className="ghost" type="button" onClick={logout}><LogOut size={14} /> Sign out</button>
          <button disabled={busy}><KeyRound size={14} /> {busy ? "Updating..." : "Set password"}</button>
        </div>
      </form>
    </main>
  );
}
