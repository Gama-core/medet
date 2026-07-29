import { useRef, useState } from "react";
import { predictImage } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { annotateImageFile } from "../lib/drawBox";
import ResultCard, { TYPE_LABELS } from "../components/ResultCard";

export default function ImageMode() {
  const settings = useSettings();
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [annotatedUrl, setAnnotatedUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  function handleFile(f) {
    if (!f) return;
    setFile(f);
    setResult(null);
    setAnnotatedUrl(null);
    setError(null);
    setPreviewUrl(URL.createObjectURL(f));
  }

  async function analyze() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await predictImage(file, settings);
      setResult(res);
      if (res.box) {
        const url = await annotateImageFile(file, res.box, {
          polypType: res.polypType,
          label: res.polypLabel || res.polypType || "Anomalie",
        });
        setAnnotatedUrl(url);
      } else {
        setAnnotatedUrl(null);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div
        className={`dropzone${drag ? " drag" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault(); setDrag(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        onClick={() => inputRef.current?.click()}
        style={{ cursor: "pointer" }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {file ? (
          <span>📎 {file.name} — cliquez pour changer</span>
        ) : (
          <span>Glissez-déposez une image endoscopique ici, ou cliquez pour parcourir</span>
        )}
      </div>

      {previewUrl && (
        <div className="frame-view" style={{ marginTop: 16, maxWidth: 480 }}>
          <img src={annotatedUrl || previewUrl} alt="Aperçu" />
          <div className="frame-caption">
            {annotatedUrl ? "Image avec la boîte détectée (dessinée côté client)" : "Aperçu avant analyse"}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
        <button className="btn btn-primary" disabled={!file || loading} onClick={analyze}>
          {loading ? "Analyse en cours…" : "🔍 Analyser l'image"}
        </button>
        {file && (
          <button
            className="btn"
            onClick={() => { setFile(null); setPreviewUrl(null); setAnnotatedUrl(null); setResult(null); setError(null); }}
          >
            Réinitialiser
          </button>
        )}
      </div>

      {error && <div className="alert alert-error" style={{ marginTop: 16 }}>⚠️ {error}</div>}

      {result && (
        <div style={{ marginTop: 20 }}>
          <ResultCard
            detected={result.detected}
            maxConf={result.maxConf}
            polypType={result.polypType}
            polypLabel={result.polypLabel}
            typeConf={result.typeConf}
            yoloZone={result.yoloZone}
          />

          {result.allProbabilities && (
            <div className="card" style={{ marginTop: 14 }}>
              <h3 style={{ marginTop: 0, color: "var(--navy)", fontSize: "0.9rem" }}>
                Probabilités par type (étage 2b)
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {Object.entries(result.allProbabilities)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, p]) => (
                    <div key={type} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ width: 140, fontSize: "0.82rem", color: "var(--ink-muted)" }}>
                        {TYPE_LABELS[type] || type}
                      </span>
                      <div style={{ flex: 1, background: "#EEF2F5", borderRadius: 6, height: 8, overflow: "hidden" }}>
                        <div style={{
                          width: `${Math.round(p * 100)}%`, height: "100%",
                          background: type === result.polypType ? "var(--teal)" : "#B9C6CE",
                        }} />
                      </div>
                      <span className="mono" style={{ width: 46, textAlign: "right", fontSize: "0.8rem" }}>
                        {Math.round(p * 100)}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {result.processingTimeMs != null && (
            <p style={{ fontSize: "0.78rem", color: "var(--ink-muted)", marginTop: 8 }}>
              Temps de traitement : {Math.round(result.processingTimeMs)} ms
            </p>
          )}
        </div>
      )}
    </div>
  );
}
