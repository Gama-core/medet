const TYPE_LABELS = {
  "1p": "Pédiculé (1p)",
  "1s": "Sessile (1s)",
  "2": "Lésion plane (2)",
  "3": "Lésion ulcérée (3)",
};

const ZONE_LABELS = {
  ignored: "Score YOLO trop bas — ignoré",
  uncertain: "Zone incertaine — vérifié par EfficientNet",
  high: "Score YOLO élevé — classification directe",
};

export default function ResultCard({ detected, maxConf, polypType, polypLabel, typeConf, yoloZone }) {
  if (!detected) {
    return (
      <div className="result-card result-success">
        <div className="result-icon">✅</div>
        <div>
          <div className="result-label">Résultat</div>
          <div className="result-value">Aucune anomalie détectée</div>
          {yoloZone && (
            <div style={{ fontSize: "0.8rem", color: "var(--ink-muted)", marginTop: 4 }}>
              {ZONE_LABELS[yoloZone] || yoloZone} · Score YOLO : {Math.round((maxConf || 0) * 100)}%
            </div>
          )}
        </div>
      </div>
    );
  }

  const variant = polypType ? "result-danger" : "result-warning";

  return (
    <div className={`result-card ${variant}`}>
      <div className="result-icon">{polypType ? "🔴" : "⚠️"}</div>
      <div>
        <div className="result-label">Résultat</div>
        <div className="result-value">
          {polypLabel || TYPE_LABELS[polypType] || polypType || "Anomalie détectée"}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--ink-muted)", marginTop: 4 }}>
          Score YOLO : {Math.round((maxConf || 0) * 100)}%
          {typeConf != null && <> · Confiance type : {Math.round(typeConf * 100)}%</>}
          {yoloZone && <> · {ZONE_LABELS[yoloZone] || yoloZone}</>}
        </div>
      </div>
    </div>
  );
}

export { TYPE_LABELS };
