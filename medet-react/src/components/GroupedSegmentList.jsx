import { useState } from "react";
import { fmtTime } from "../lib/time";
import { groupSegmentsByType } from "../lib/segments";
import { TYPE_LABELS } from "./ResultCard";

export default function GroupedSegmentList({ segments, selectedId, onSelect }) {
  const [expanded, setExpanded] = useState({});

  if (!segments || segments.length === 0) {
    return <div className="alert alert-info">Aucun segment détecté pour l'instant.</div>;
  }

  const groups = groupSegmentsByType(segments);

  function toggle(groupId) {
    setExpanded((e) => ({ ...e, [groupId]: !e[groupId] }));
  }

  return (
    <div className="segment-list">
      {groups.map((g) => {
        const isOpen = !!expanded[g.id];
        const label = TYPE_LABELS[g.polyp_type] || g.polyp_type || "Anomalie";

        return (
          <div key={g.id} className={`segment-item${selectedId === g.first.id ? " selected" : ""}`}>
            <button
              onClick={() => { toggle(g.id); onSelect(g.first.id); }}
              style={{
                all: "unset", cursor: "pointer", width: "100%", boxSizing: "border-box",
                padding: "12px 16px", display: "flex", alignItems: "center",
                justifyContent: "space-between", fontWeight: 600, color: "var(--navy)",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {label}
                {g.count > 1 && <span className="chip chip-demo">× {g.count}</span>}
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span className="mono" style={{ fontWeight: 500, color: "var(--ink-muted)", fontSize: "0.82rem" }}>
                  {g.first.start_ts} → {g.first.end_ts}
                  {g.count > 1 && !isOpen && " (première occurrence)"}
                </span>
                <span style={{ color: "var(--teal)", fontSize: "0.8rem" }}>
                  {isOpen ? "▲ réduire" : g.count > 1 ? "▼ voir toutes les occurrences" : "▼"}
                </span>
              </span>
            </button>

            {isOpen && (
              <div style={{ padding: "0 16px 16px", display: "flex", flexDirection: "column", gap: 10 }}>
                {g.instances.map((s, i) => (
                  <div
                    key={s.id}
                    onClick={() => onSelect(s.id)}
                    style={{
                      display: "flex", gap: 14, alignItems: "center", cursor: "pointer",
                      padding: "10px 12px", borderRadius: 10,
                      border: `1px solid ${selectedId === s.id ? "var(--teal)" : "var(--border)"}`,
                      background: selectedId === s.id ? "#EAF7F7" : "#FAFCFD",
                    }}
                  >
                    {s.best_frame_url && (
                      <img
                        src={s.best_frame_url}
                        alt={`Occurrence ${i + 1}`}
                        style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 6, border: "1px solid var(--border)" }}
                      />
                    )}
                    <div style={{ fontSize: "0.82rem", lineHeight: 1.6 }}>
                      <div style={{ fontWeight: 600, color: "var(--navy)" }}>
                        Occurrence {i + 1} — {s.start_ts} → {s.end_ts}
                      </div>
                      <div style={{ color: "var(--ink-muted)" }}>
                        Durée {fmtTime(Math.max(0, s.end_s - s.start_s))} · Confiance max{" "}
                        {Math.round((s.max_conf || 0) * 100)}%
                        {s.type_conf != null && <> · Type {Math.round(s.type_conf * 100)}%</>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
