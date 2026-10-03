import { useState } from "react";
import { api } from "../api";
import { useToast } from "../toast.jsx";
import { FileSpreadsheet, UploadCloud } from "lucide-react";

export default function ImportPage() {
  const toast = useToast();
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    const file = e.target.file.files[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const data = await api("/episodes/import", { method: "POST", body });
      setResult(data);
      toast.push(`Imported ${data.imported}, updated ${data.updated}, skipped ${data.skipped}`, "ok");
    } catch (err) {
      toast.push(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <section className="page-heading"><div><div className="eyebrow">Workspace / Import</div><h1>Episode import</h1><p>Safely ingest recording exports. Duplicates and malformed rows are reported without blocking valid data.</p></div></section>
      <div className="card">
      <form className="dropzone" onSubmit={submit}>
        <UploadCloud size={30} />
        <h2>Upload recording export</h2>
        <p className="card-subtitle">CSV only. Running the same file twice will not duplicate episodes.</p>
        <input type="file" name="file" accept=".csv" />
        <button disabled={busy}>{busy ? "Importing..." : <><FileSpreadsheet size={14} /> Import CSV</>}</button>
      </form>
      {result && (
        <>
          <div className="stat-grid compact-stats"><div className="stat"><div className="kicker">Imported</div><b>{result.imported}</b></div><div className="stat"><div className="kicker">Updated</div><b>{result.updated}</b></div><div className="stat"><div className="kicker">Skipped</div><b>{result.skipped}</b></div></div>
          <table className="table">
            <thead><tr><th>Row</th><th>Episode</th><th>Reason</th></tr></thead>
            <tbody>
              {result.skips.map((s, i) => (
                <tr key={i}><td>{s.row}</td><td>{s.episode_id || "—"}</td><td>{s.reason}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      </div>
    </div>
  );
}
