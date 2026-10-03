import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useToast } from "../toast.jsx";
import { ArrowLeft, Send } from "lucide-react";

export default function NewRequest() {
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    task_name: "pick cup",
    episodes_requested: 5,
    deadline: "",
    notes: "",
  });
  const [busy, setBusy] = useState(false);

  function set(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const created = await api("/requests", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          episodes_requested: Number(form.episodes_requested),
        }),
      });
      toast.push("Request submitted", "ok");
      navigate(`/requests/${created.id}`);
    } catch (err) {
      toast.push(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <section className="page-heading">
        <div><div className="eyebrow">Workspace / Requests / New</div><h1>Create a request</h1><p>Describe the dataset outcome, required volume, and delivery window.</p></div>
        <button className="ghost" type="button" onClick={() => navigate(-1)}><ArrowLeft size={14} /> Back</button>
      </section>
      <form className="card form-panel" onSubmit={submit}>
        <div className="card-head"><div><h2>Request details</h2><p className="card-subtitle">Operations will match assignable good or usable episodes.</p></div></div>
        <div className="form-stack">
        <label>Task name<input value={form.task_name} onChange={(e) => set("task_name", e.target.value)} /></label>
        <label>Episodes requested<input type="number" min="1" value={form.episodes_requested} onChange={(e) => set("episodes_requested", e.target.value)} /></label>
        <label>Deadline<input type="datetime-local" value={form.deadline} onChange={(e) => set("deadline", e.target.value)} /></label>
        <label>Notes<textarea value={form.notes} onChange={(e) => set("notes", e.target.value)} /></label>
        <button disabled={busy}>{busy ? "Submitting..." : <><Send size={14} /> Submit request</>}</button>
        </div>
      </form>
    </div>
  );
}
