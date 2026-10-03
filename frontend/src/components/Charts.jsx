export function BarChart({ items, valueKey = "count", labelKey = "label" }) {
  const max = Math.max(...items.map((item) => Number(item[valueKey]) || 0), 1);
  return (
    <div className="bars">
      {items.map((item) => {
        const value = Number(item[valueKey]) || 0;
        return (
          <div className="bar-row" key={item[labelKey]} data-tooltip={`${item[labelKey]}: ${value}`}>
            <span className="bar-label">{item[labelKey]}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(value / max) * 100}%` }} />
            </div>
            <span className="bar-value">{value}</span>
          </div>
        );
      })}
      {items.length === 0 && <p className="muted">No data in range.</p>}
    </div>
  );
}

export function GroupedBars({ groups }) {
  const days = Object.keys(groups);
  const robots = [...new Set(days.flatMap((day) => groups[day].map((r) => r.robot_id)))];
  const max = Math.max(
    ...days.flatMap((day) => groups[day].map((r) => r.count)),
    1
  );
  const palette = ["#1f6feb", "#0f766e", "#b45309", "#7c3aed", "#be123c"];
  return (
    <div className="grouped">
      <div className="legend">
        {robots.map((robot, i) => (
          <span key={robot}><i style={{ background: palette[i % palette.length] }} />{robot}</span>
        ))}
      </div>
      <div className="grouped-rows">
        {days.map((day) => (
          <div className="grouped-row" key={day}>
            <span className="bar-label">{day.slice(5)}</span>
            <div className="grouped-track">
              {robots.map((robot, i) => {
                const hit = groups[day].find((r) => r.robot_id === robot);
                const value = hit ? hit.count : 0;
                return (
                  <div
                    key={robot}
                    className="grouped-col"
                    data-tooltip={`${robot}: ${value}`}
                    title={`${day} · ${robot}: ${value}`}
                    style={{
                      height: `${(value / max) * 100}%`,
                      background: palette[i % palette.length],
                    }}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
