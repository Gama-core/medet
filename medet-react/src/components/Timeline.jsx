import { useState } from "react";
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceArea,
} from "recharts";
import { fmtTime } from "../lib/time";
import { TYPE_LABELS } from "./ResultCard";

const TYPE_COLORS = { "1p": "#D64550", "1s": "#E8A33D", "2": "#0F8B8D", "3": "#7C3AED" };
const NORMAL_COLOR = "#B9C6CE";

// Losange pour une détection positive, petit cercle pour un point "normal"
function PointShape(props) {
  const { cx, cy, payload } = props;
  if (!payload) return null;
  const color = payload.detected ? (TYPE_COLORS[payload.type] || "#D64550") : NORMAL_COLOR;
  if (payload.detected) {
    const r = 6;
    const points = `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`;
    return <polygon points={points} fill={color} stroke="#fff" strokeWidth={1} style={{ cursor: "pointer" }} />;
  }
  return <circle cx={cx} cy={cy} r={2.5} fill={color} style={{ cursor: "pointer" }} />;
}

export default function Timeline({ points, segments, selectedId, onSelectSegment, durationS }) {
  const [previewPoint, setPreviewPoint] = useState(null);

  if (!points || points.length === 0) return null;

  function findSegmentAt(elapsed) {
    return segments.find((s) => elapsed >= s.start_s && elapsed <= s.end_s) || null;
  }

  function handlePointClick(p) {
    if (!p || !p.detected) return;
    setPreviewPoint(p);
    const seg = findSegmentAt(p.elapsed);
    if (seg) onSelectSegment(seg.id);
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0, color: "var(--navy)", fontSize: "0.95rem" }}>
        Chronologie de l'examen
      </h3>
      <p style={{ fontSize: "0.78rem", color: "var(--ink-muted)", marginTop: -8, marginBottom: 12 }}>
        Cliquez sur un losange pour vérifier l'image de la détection correspondante.
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid stroke="#E7EDF1" />
          <XAxis
            dataKey="elapsed"
            type="number"
            domain={[0, durationS || "auto"]}
            tickFormatter={fmtTime}
            stroke="#5C6B7A"
            fontSize={12}
          />
          <YAxis
            dataKey="conf"
            type="number"
            domain={[0, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            stroke="#5C6B7A"
            fontSize={12}
            width={46}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null;
              const p = payload[0].payload;
              return (
                <div style={{
                  background: "#fff", border: "1px solid #DFE6EB", borderRadius: 8,
                  padding: "6px 10px", fontSize: "0.78rem",
                }}>
                  <div><b>t = {fmtTime(p.elapsed)}</b></div>
                  <div>{p.detected ? (TYPE_LABELS[p.type] || "Anomalie") : "Normal"}</div>
                  <div>Confiance : {Math.round(p.conf * 100)}%</div>
                  {p.detected && <div style={{ color: "var(--teal-dark)" }}>Cliquer pour vérifier l'image</div>}
                </div>
              );
            }}
          />
          {segments.map((s) => (
            <ReferenceArea
              key={s.id}
              x1={s.start_s}
              x2={Math.max(s.end_s, s.start_s + 0.15)}
              fill={TYPE_COLORS[s.polyp_type] || "#0F8B8D"}
              fillOpacity={s.id === selectedId ? 0.28 : 0.12}
              stroke={s.id === selectedId ? (TYPE_COLORS[s.polyp_type] || "#0F8B8D") : "transparent"}
              onClick={() => onSelectSegment(s.id)}
              style={{ cursor: "pointer" }}
            />
          ))}
          <Scatter data={points} shape={PointShape} onClick={handlePointClick} cursor="pointer" />
        </ScatterChart>
      </ResponsiveContainer>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 4, marginBottom: previewPoint ? 14 : 0 }}>
        {Object.entries(TYPE_LABELS).map(([k, label]) => (
          <span key={k} style={{ fontSize: "0.78rem", color: "var(--ink-muted)" }}>
            <span style={{
              display: "inline-block", width: 9, height: 9, borderRadius: "50%",
              background: TYPE_COLORS[k], marginRight: 5,
            }} />
            {label}
          </span>
        ))}
      </div>

      {previewPoint && previewPoint.frameUrl && (
        <div style={{
          display: "flex", gap: 14, alignItems: "center", padding: "12px 14px",
          borderRadius: 10, border: "1px solid var(--border)", background: "#FAFCFD",
        }}>
          <img
            src={previewPoint.frameUrl}
            alt={`Frame à ${fmtTime(previewPoint.elapsed)}`}
            style={{ width: 140, borderRadius: 8, border: "1px solid var(--border)" }}
          />
          <div style={{ fontSize: "0.85rem" }}>
            <div style={{ fontWeight: 600, color: "var(--navy)" }}>
              Vérification — t = {fmtTime(previewPoint.elapsed)}
            </div>
            <div style={{ color: "var(--ink-muted)", marginTop: 4 }}>
              {TYPE_LABELS[previewPoint.type] || "Anomalie"} · confiance {Math.round(previewPoint.conf * 100)}%
            </div>
            <button className="btn" style={{ marginTop: 8, fontSize: "0.78rem", padding: "0.35rem 0.8rem" }} onClick={() => setPreviewPoint(null)}>
              Fermer l'aperçu
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
