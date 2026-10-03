import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { useToast } from "../toast.jsx";
import EpisodePanel from "../components/EpisodePanel.jsx";
import { ArrowLeft, CheckCircle2, PackageCheck, RotateCcw } from "lucide-react";

const NEXT = {
  operator: {
    submitted: "in_progress",
    in_progress: "delivered",
    rejected: "in_progress",
  },
  client: {
    delivered: null,
  },
};

export default function RequestDetail({ user }) {
  const { id } = useParams();
  const toast = useToast();
  const [req, setReq] = useState(null);
  const [episodes, setEpisodes] = useState([]);
  const [task, setTask] = useState("");
  const [quality, setQuality] = useState("");
  const [selected, setSelected] = useState([]);
  const [activeEpisode, setActiveEpisode] = useState(null);
  const isStaff = user.role === "operator" || user.role === "admin";

  async function load(taskFilter = task) {
    try {
      const data = await api(`/requests/${id}`);
      setReq(data);
      if (!taskFilter) {
        setTask(data.task_name);
        taskFilter = data.task_name;
      }
      if (isStaff) {
        const query = new URLSearchParams({ available_only: "true" });
        if (taskFilter) query.set("task_name", taskFilter);
        if (quality) query.set("quality", quality);
        setEpisodes(await api(`/episodes?${query.toString()}`));
      }
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  useEffect(() => {
    load();
  }, [id, quality]);

  async function transition(status) {
    try {
      const data = await api(`/requests/${id}/transition`, {
        method: "POST",
        body: JSON.stringify({ status }),
      });
      setReq(data);
      toast.push(`Moved to ${status}`, "ok");
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  async function assign() {
    try {
      const data = await api(`/requests/${id}/assignments`, {
        method: "POST",
        body: JSON.stringify({ episode_ids: selected }),
      });
      setReq(data.request);
      setSelected([]);
      toast.push(`Assigned ${data.assigned} episode(s)`, "ok");
      load();
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  async function unassign(code) {
    try {
      const data = await api(`/requests/${id}/assignments/${code}`, { method: "DELETE" });
      setReq(data.request);
      toast.push(`Removed ${code}`, "ok");
      load();
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  if (!req) return <p className="muted">Loading...</p>;

  const next = isStaff ? NEXT.operator[req.status] : null;

  return (
    <div className="grid">
      <section className="page-heading">
        <div>
          <div className="eyebrow">Workspace / Requests / REQ-{String(req.id).padStart(4, "0")}</div>
          <h1>{req.task_name}</h1>
          <p>{req.client_name} · {req.assigned_count} of {req.episodes_requested} episodes assigned · due {new Date(req.deadline).toLocaleDateString()}</p>
        </div>
        <div className="row">
          <button className="ghost" type="button" onClick={() => history.back()}><ArrowLeft size={14} /> Back</button>
          {next && <button onClick={() => transition(next)}>{next === "delivered" ? <PackageCheck size={14} /> : <RotateCcw size={14} />} {next.replace("_", " ")}</button>}
          {user.role === "client" && req.status === "delivered" && (
            <><button onClick={() => transition("accepted")}><CheckCircle2 size={14} /> Accept</button><button className="danger" onClick={() => transition("rejected")}>Reject</button></>
          )}
        </div>
      </section>
      <div className="grid grid-2 request-workspace">
      <div className="card request-summary">
        <div className="card-head"><div><h2>Delivery workspace</h2><p className="card-subtitle">Assigned inventory and request history</p></div><span className={`badge ${req.status}`}>{req.status.replace("_", " ")}</span></div>
        {req.notes && <p className="muted">{req.notes}</p>}
        <h3>Assigned episodes</h3>
        <table className="table">
          <thead><tr><th>ID</th><th>Robot</th><th>Quality</th><th></th></tr></thead>
          <tbody>
            {req.assignments.map((a) => (
              <tr key={a.id} onClick={() => setActiveEpisode({ ...a.episode, assigned_request_id: req.id })}>
                <td>{a.episode.episode_id}</td>
                <td>{a.episode.robot_id}</td>
                <td><span className={`badge ${a.episode.quality}`}>{a.episode.quality}</span></td>
                <td>
                  {isStaff && ["submitted", "in_progress", "rejected"].includes(req.status) && (
                    <button className="ghost" onClick={(e) => { e.stopPropagation(); unassign(a.episode.episode_id); }}>Remove</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Activity</h3>
        <div className="timeline">{req.events.map((e) => (
          <div key={e.id} className="timeline-item"><i /><div><b>{e.actor_name}</b> moved the request to <span className={`badge ${e.to_status}`}>{e.to_status.replace("_", " ")}</span><small>{new Date(e.created_at).toLocaleString()}</small></div></div>
        ))}</div>
      </div>
      {isStaff && (
        <div className="card assignment-panel">
          <div className="card-head"><div><h2>Episode inventory</h2><p className="card-subtitle">Select a row to inspect its metadata.</p></div></div>
          <div className="filters">
            <label>Task<input value={task} onChange={(e) => setTask(e.target.value)} /></label>
            <label>
              Quality
              <select value={quality} onChange={(e) => setQuality(e.target.value)}>
                <option value="">any</option>
                <option value="good">good</option>
                <option value="usable">usable</option>
              </select>
            </label>
            <button className="ghost" type="button" onClick={() => load(task)}>Filter</button>
          </div>
          <div className="inventory-scroll"><table className="table">
            <thead><tr><th></th><th>ID</th><th>Task</th><th>Quality</th></tr></thead>
            <tbody>
              {episodes.map((ep) => (
                <tr key={ep.id} onClick={() => setActiveEpisode(ep)}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.includes(ep.episode_id)}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        setSelected((cur) =>
                          e.target.checked ? [...cur, ep.episode_id] : cur.filter((x) => x !== ep.episode_id)
                        );
                      }}
                    />
                  </td>
                  <td>{ep.episode_id}</td>
                  <td>{ep.task_name}</td>
                  <td><span className={`badge ${ep.quality}`}>{ep.quality}</span></td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <div className="assignment-footer"><span>{selected.length} selected</span><button disabled={!selected.length} onClick={assign}>Assign selected</button></div>
        </div>
      )}
      </div>
      <EpisodePanel episode={activeEpisode} onClose={() => setActiveEpisode(null)} />
    </div>
  );
}
