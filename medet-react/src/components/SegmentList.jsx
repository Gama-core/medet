import { fmtTime } from "../lib/time";
import { TYPE_LABELS } from "./ResultCard";

export default function SegmentList({ segments, selectedId, onSelect }) {
  if (!segments || segments.length === 0) {
    return <div className="alert alert-info">Aucun segment détecté pour l'instant.</div>;
  }

  return (
    <div className="segment-list">
      {segments.map((s, i) => (
        <details
          key={s.id}
          open={s.id === selectedId}
          className={`segment-item${s.id === selectedId ? " selected" : ""}`}
          onToggle={(e) => e.target.open && onSelect(s.id)}
        >
          <summary onClick={() => onSelect(s.id)}>
            <span>
              #{i + 1} — {TYPE_LABELS[s.polyp_type] || s.polyp_type || "Anomalie"}
            </span>
            <span className="mono" style={{ fontWeight: 500, color: "var(--ink-muted)" }}>
              {s.start_ts} → {s.end_ts}
            </span>
          </summary>
          <div className="segment-body">
            {s.best_frame_url && (
              <img
                src={s.best_frame_url}
                alt={`Meilleure frame du segment ${i + 1}`}
                style={{ width: 180, borderRadius: 8, border: "1px solid var(--border)" }}
              />
            )}
            <div style={{ fontSize: "0.85rem", lineHeight: 1.8 }}>
              <div>Durée : <b>{fmtTime(Math.max(0, s.end_s - s.start_s))}</b></div>
              <div>Confiance max (YOLO) : <b>{Math.round((s.max_conf || 0) * 100)}%</b></div>
              {s.type_conf != null && (
                <div>Confiance type : <b>{Math.round(s.type_conf * 100)}%</b></div>
              )}
              {s.n_frames != null && <div>Frames regroupées : <b>{s.n_frames}</b></div>}
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}
