import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useToast } from "../toast.jsx";
import { BarChart, GroupedBars } from "../components/Charts.jsx";
import { CalendarDays, Filter, RefreshCw, X } from "lucide-react";

export default function AnalyticsPage() {
  const toast = useToast();
  const [start, setStart] = useState("2026-08-01");
  const [end, setEnd] = useState("2026-09-30");
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({ operator_name: "", robot_id: "", task_name: "", quality: "" });

  async function load(e) {
    e?.preventDefault();
    try {
      const query = new URLSearchParams({
        start: `${start}T00:00:00Z`,
        end: `${end}T23:59:59Z`,
      });
      Object.entries(filters).forEach(([key, value]) => value && query.set(key, value));
      setData(await api(`/analytics?${query.toString()}`));
    } catch (err) {
      toast.push(err.message, "error");
    }
  }

  useEffect(() => {
    load();
  }, [filters]);

  function setFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function clearFilters() {
    setFilters({ operator_name: "", robot_id: "", task_name: "", quality: "" });
  }

  const grouped = useMemo(() => {
    const days = {};
    for (const row of data?.episodes_per_day_per_robot || []) {
      days[row.day] = days[row.day] || [];
      days[row.day].push(row);
    }
    return days;
  }, [data]);

  const byRobot = useMemo(() => {
    const totals = {};
    for (const row of data?.episodes_per_day_per_robot || []) {
      totals[row.robot_id] = (totals[row.robot_id] || 0) + row.count;
    }
    return Object.entries(totals)
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  const statusItems = Object.entries(data?.requests_by_status || {}).map(([label, count]) => ({
    label,
    count,
  }));
  const totalEpisodes = byRobot.reduce((sum, row) => sum + row.count, 0);
  const totalRequests = statusItems.reduce((sum, row) => sum + row.count, 0);

  return (
    <div className="grid">
      <section className="page-heading">
        <div>
          <div className="eyebrow">Workspace / Analytics</div>
          <h1>Performance analytics</h1>
          <p>Understand recording throughput, request health, and the tasks producing your strongest data.</p>
        </div>
        <form className="date-toolbar" onSubmit={load}>
          <CalendarDays size={16} />
          <label>From<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <span>to</span>
          <label>Until<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <button title="Refresh analytics"><RefreshCw size={14} /> Run report</button>
        </form>
      </section>
      <form className="filter-toolbar" onSubmit={load}>
        <div className="filter-title"><Filter size={15} /><span>Episode filters</span></div>
        <label>Operator<select value={filters.operator_name} onChange={(e) => setFilter("operator_name", e.target.value)}><option value="">All operators</option>{(data?.filter_options?.operators || []).map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Robot type<select value={filters.robot_id} onChange={(e) => setFilter("robot_id", e.target.value)}><option value="">All robots</option>{(data?.filter_options?.robots || []).map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Task<select value={filters.task_name} onChange={(e) => setFilter("task_name", e.target.value)}><option value="">All tasks</option>{(data?.filter_options?.tasks || []).map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Quality<select value={filters.quality} onChange={(e) => setFilter("quality", e.target.value)}><option value="">All quality</option>{(data?.filter_options?.qualities || []).map((value) => <option key={value}>{value}</option>)}</select></label>
        <span className="filter-live">Updates automatically</span>
        {Object.values(filters).some(Boolean) && <button className="ghost" type="button" onClick={clearFilters}><X size={14} /> Clear</button>}
      </form>
      {!data && <div className="card empty-state">Choose a date range and run the report to explore operational trends.</div>}
      {data && (
        <>
          <div className="stat-grid">
            <div className="stat"><div className="kicker">Episodes</div><b>{totalEpisodes}</b><small>Recorded in range</small></div>
            <div className="stat"><div className="kicker">Requests</div><b>{totalRequests}</b><small>Created in range</small></div>
            <div className="stat"><div className="kicker">Median fulfil</div><b>{data.median_submitted_to_delivered_hours ?? "—"}</b><small>Hours to delivery</small></div>
            <div className="stat"><div className="kicker">Top task</div><b className="stat-word">{data.top_good_tasks[0]?.task_name || "—"}</b><small>By good episodes</small></div>
          </div>
          <div className="grid grid-2">
            <div className="card">
              <div className="card-head"><div><h3>Requests by status</h3><p className="card-subtitle">Current workflow distribution</p></div></div>
              <BarChart items={statusItems} />
            </div>
            <div className="card">
              <div className="card-head"><div><h3>Top good tasks</h3><p className="card-subtitle">Highest-quality collection areas</p></div></div>
              <BarChart items={data.top_good_tasks.map((t) => ({ label: t.task_name, count: t.count }))} />
            </div>
          </div>
          <div className="card">
            <div className="card-head"><div><h3>Episodes by robot</h3><p className="card-subtitle">Total recording output by platform</p></div></div>
            <BarChart items={byRobot} />
          </div>
          <div className="card">
            <div className="card-head"><div><h3>Daily recording volume</h3><p className="card-subtitle">Hover a bar to inspect robot throughput</p></div></div>
            <GroupedBars groups={grouped} />
          </div>
          <div className="card">
            <h3>Daily groups</h3>
            <div className="grid">
              {Object.entries(grouped).map(([day, rows]) => (
                <div className="group-block" key={day}>
                  <h4>{day}</h4>
                  <BarChart items={rows.map((r) => ({ label: r.robot_id, count: r.count }))} />
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
