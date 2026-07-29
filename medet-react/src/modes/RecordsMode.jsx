import { useEffect, useState } from "react";
import { listRecords, getRecord, deleteRecord, shareRecord, unshareRecord } from "../lib/api";
import SegmentList from "../components/SegmentList";

export default function RecordsMode() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [shareBusy, setShareBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const res = await listRecords();
      setRecords(res.records || res || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, []);

  async function openRecord(id) {
    setSelected(id);
    setDetail(null);
    try {
      const res = await getRecord(id);
      setDetail(res);
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(id) {
    if (!confirm("Supprimer définitivement cet examen ?")) return;
    try {
      await deleteRecord(id);
      if (selected === id) { setSelected(null); setDetail(null); }
      refresh();
    } catch (e) {
      setError(e.message);
    }
  }

  async function toggleShare() {
    if (!detail) return;
    setShareBusy(true);
    try {
      if (detail.share_token) {
        await unshareRecord(detail.id);
        setDetail({ ...detail, share_token: null });
      } else {
        const res = await shareRecord(detail.id);
        setDetail({ ...detail, share_token: res.share_token });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setShareBusy(false);
    }
  }

  return (
    <div>
      <div className="alert alert-info">
        🗂️ Examens enregistrés en base — aucune identité patient réelle stockée, uniquement une
        référence libre choisie par le médecin.
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--navy)", fontSize: "0.95rem" }}>
            Examens ({records.length})
          </h3>
          {loading ? (
            <p style={{ color: "var(--ink-muted)" }}>Chargement…</p>
          ) : records.length === 0 ? (
            <p style={{ color: "var(--ink-muted)" }}>Aucun examen enregistré pour l'instant.</p>
          ) : (
            <div className="segment-list">
              {records.map((r) => (
                <div
                  key={r.id}
                  className={`segment-item${selected === r.id ? " selected" : ""}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => openRecord(r.id)}
                >
                  <div style={{ padding: "12px 16px", display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontWeight: 600, color: "var(--navy)" }}>
                      {r.reference_label || `Examen #${r.id}`}
                    </span>
                    <span className="mono" style={{ fontSize: "0.78rem", color: "var(--ink-muted)" }}>
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0, color: "var(--navy)", fontSize: "0.95rem" }}>Détail</h3>
          {!selected && <p style={{ color: "var(--ink-muted)" }}>Sélectionnez un examen à gauche.</p>}
          {selected && !detail && <p style={{ color: "var(--ink-muted)" }}>Chargement…</p>}
          {detail && (
            <div>
              <div className="stat-strip" style={{ marginBottom: 14 }}>
                <span>Référence : <b>{detail.reference_label || detail.id}</b></span>
                <span>Segments : <b>{detail.segments?.length || 0}</b></span>
              </div>
              <SegmentList segments={detail.segments || []} selectedId={null} onSelect={() => {}} />
              <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
                <button className="btn" disabled={shareBusy} onClick={toggleShare}>
                  {detail.share_token ? "🔒 Révoquer le partage" : "🔗 Partager avec un confrère"}
                </button>
                <button className="btn btn-danger" onClick={() => remove(detail.id)}>Supprimer</button>
              </div>
              {detail.share_token && (
                <div className="alert alert-success" style={{ marginTop: 12 }}>
                  Lien actif : <code>{window.location.origin}/shared/{detail.share_token}</code>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
