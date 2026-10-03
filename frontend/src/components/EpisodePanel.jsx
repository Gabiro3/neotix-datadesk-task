export default function EpisodePanel({ episode, onClose }) {
  if (!episode) return null;
  const rows = [
    ["Episode ID", episode.episode_id],
    ["Robot", episode.robot_id],
    ["Task", episode.task_name],
    ["Quality", episode.quality],
    ["Duration", `${episode.duration_seconds}s`],
    ["Operator", episode.operator_name],
    ["Recorded", episode.recorded_at ? new Date(episode.recorded_at).toLocaleString() : "—"],
    ["Assigned request", episode.assigned_request_id ? `#${episode.assigned_request_id}` : "Unassigned"],
  ];
  return (
    <>
      <div className="drawer-mask" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-head">
          <div>
            <div className="kicker">Episode</div>
            <h2>{episode.episode_id}</h2>
          </div>
          <button className="ghost" type="button" onClick={onClose}>Close</button>
        </div>
        <dl className="meta-list">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>
                {label === "Quality" ? <span className={`badge ${value}`}>{value}</span> : value}
              </dd>
            </div>
          ))}
        </dl>
      </aside>
    </>
  );
}
