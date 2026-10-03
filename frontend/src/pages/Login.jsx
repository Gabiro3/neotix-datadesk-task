import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, saveSession } from "../api";
import { useToast } from "../toast.jsx";
import { ArrowRight, Building2, LockKeyhole, ShieldCheck, Wrench } from "lucide-react";

const PROFILES = {
  client: { email: "client-a@example.com", password: "client123", icon: Building2 },
  operator: { email: "ops1@example.com", password: "ops123", icon: Wrench },
  admin: { email: "admin@example.com", password: "admin123", icon: ShieldCheck },
};

export default function Login({ onLogin }) {
  const toast = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState("ops1@example.com");
  const [password, setPassword] = useState("ops123");
  const [role, setRole] = useState("operator");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      saveSession(data.access_token, data.user);
      toast.push(`Signed in as ${data.user.name}`, "ok");
      onLogin();
      navigate("/");
    } catch (err) {
      toast.push(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function pickRole(nextRole) {
    setRole(nextRole);
    setEmail(PROFILES[nextRole].email);
    setPassword(PROFILES[nextRole].password);
  }

  return (
    <div className="login">
      <section className="login-visual">
        <img className="login-logo" src="/neotix-datadesk-logo.png" alt="Neotix Data Desk" />
        <img className="robot-art" src="/robot-arm.png" alt="Industrial robot arm" />
      </section>
      <section className="login-form">
        <form className="card" onSubmit={submit}>
          <div className="kicker">Dataset Request Desk</div>
          <h2>Welcome back</h2>
          <p className="card-subtitle">Sign in to continue to your workspace.</p>
          <div className="form-stack" style={{ marginTop: 24 }}>
            <fieldset className="role-picker">
              <legend>Choose your workspace role</legend>
              <div>
                {Object.entries(PROFILES).map(([name, profile]) => {
                  const Icon = profile.icon;
                  return <button className={role === name ? "selected" : ""} type="button" key={name} onClick={() => pickRole(name)}><Icon size={16} /><span>{name}</span></button>;
                })}
              </div>
            </fieldset>
            <label>Email address<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
            <button disabled={busy}>{busy ? "Signing in..." : <><LockKeyhole size={14} /> Sign in <ArrowRight size={14} /></>}</button>
          </div>
        </form>
      </section>
    </div>
  );
}
