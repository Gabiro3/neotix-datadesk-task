import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useToast } from "../toast.jsx";
import { Plus, Search, Sparkles } from "lucide-react";

const STATUS_TERMS = {
  active: ["submitted", "in_progress"],
  open: ["submitted", "in_progress", "rejected"],
  progress: ["in_progress"],
  working: ["in_progress"],
  ready: ["delivered"],
  delivered: ["delivered"],
  complete: ["accepted"],
  completed: ["accepted"],
  accepted: ["accepted"],
  rejected: ["rejected"],
  submitted: ["submitted"],
};

function smartMatch(request, query) {
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  if (!terms.length) return true;
  const text = [request.id, request.client_name, request.task_name, request.status.replace("_", " ")]
    .join(" ")
    .toLowerCase();
  return terms.every((term) => {
    if (["request", "requests", "episode", "episodes", "for", "with", "from"].includes(term)) return true;
    const statuses = STATUS_TERMS[term];
    return statuses ? statuses.includes(request.status) : text.includes(term.replace(/^#/, ""));
  });
}

export default function Requests({ user }) {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState("");
  const toast = useToast();
  const navigate = useNavigate();
  const isStaff = user.role !== "client";

  async function load() {
    try {
      setItems(await api("/requests"));
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  useEffect(() => {
    load();
    if (!isStaff) return undefined;
    const token = localStorage.getItem("token");
    const controller = new AbortController();
    (async () => {
      try {
        const response = await fetch((import.meta.env.VITE_API_URL || "") + "/events", {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          if (buffer.includes("\n\n")) {
            buffer = "";
            load();
          }
        }
      } catch {
        /* closed */
      }
    })();
    return () => controller.abort();
  }, []);

  const filtered = useMemo(() => items.filter((item) => smartMatch(item, query)), [items, query]);
  const activeCount = items.filter((item) => ["submitted", "in_progress", "rejected"].includes(item.status)).length;
  const deliveredCount = items.filter((item) => item.status === "delivered").length;
  const acceptedCount = items.filter((item) => item.status === "accepted").length;

  return (
    <div className="grid">
      <section className="page-heading">
        <div>
          <div className="eyebrow">Workspace / Requests</div>
          <h1>{isStaff ? "Operations overview" : "Dataset requests"}</h1>
          <p>{isStaff ? "Track fulfilment, allocate episodes, and keep every delivery moving." : "Create and review dataset deliveries from one focused workspace."}</p>
        </div>
        {!isStaff && <button onClick={() => navigate("/new")}><Plus size={15} /> New request</button>}
      </section>

      <section className="stat-grid">
        <div className="stat"><div className="kicker">All requests</div><b>{items.length}</b><small>Visible to you</small></div>
        <div className="stat"><div className="kicker">Open work</div><b>{activeCount}</b><small>Needs operations</small></div>
        <div className="stat"><div className="kicker">Awaiting review</div><b>{deliveredCount}</b><small>Delivered to clients</small></div>
        <div className="stat"><div className="kicker">Accepted</div><b>{acceptedCount}</b><small>Completed requests</small></div>
      </section>

      <section className="card">
        <div className="card-head">
          <div>
            <h2>{isStaff ? "All requests" : "Your requests"}</h2>
            <p className="card-subtitle">Search by intent, status, task, client, or request ID.</p>
          </div>
          <div className="search-shell">
            <div className="search-box">
              <Search size={16} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder='Try “active pick cup requests”'
                aria-label="Semantic request search"
              />
              <span className="search-hint"><Sparkles size={12} /> Smart</span>
            </div>
            <div className="search-meta">
              <span onClick={() => setQuery("active")}>active</span>
              <span onClick={() => setQuery("delivered")}>delivered</span>
              <span onClick={() => setQuery("accepted")}>accepted</span>
              <b>{filtered.length} results</b>
            </div>
          </div>
        </div>
        <div className="table-wrap">
        <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Client</th>
            <th>Task</th>
            <th>Progress</th>
            <th>Deadline</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((req) => (
            <tr key={req.id} onClick={() => navigate(`/requests/${req.id}`)}>
              <td><span className="request-id">REQ-{String(req.id).padStart(4, "0")}</span></td>
              <td>{req.client_name}</td>
              <td>{req.task_name}</td>
              <td><div className="progress-wrap"><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(100, req.assigned_count / req.episodes_requested * 100)}%` }} /></div><span>{req.assigned_count}/{req.episodes_requested}</span></div></td>
              <td>{new Date(req.deadline).toLocaleDateString()}</td>
              <td><span className={`badge ${req.status}`}>{req.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      {filtered.length === 0 && <div className="empty-state">No requests match “{query}”. Try a task, client, status, or ID.</div>}
      </section>
    </div>
  );
}
