import { useSettings } from "../context/SettingsContext";

export default function SettingsSidebar() {
  const {
    yoloLow, yoloHigh, frameSkip, minSegmentDuration,
    setYoloLow, setYoloHigh, setFrameSkip, setMinSegmentDuration,
  } = useSettings();

  return (
    <aside className="sidebar">
      <h2>⚙️ Paramètres médicaux</h2>

      <h3>Sensibilité YOLO (étage 1)</h3>

      <div className="field">
        <label>
          <span>Seuil minimum de détection</span>
          <span className="field-value">{Math.round(yoloLow * 100)}%</span>
        </label>
        <input
          type="range" min="0.10" max="0.50" step="0.05"
          value={yoloLow}
          onChange={(e) => setYoloLow(parseFloat(e.target.value))}
        />
        <div className="field-help">En dessous de ce score → pas de polype détecté.</div>
      </div>

      <div className="field">
        <label>
          <span>Seuil de confiance élevée</span>
          <span className="field-value">{Math.round(yoloHigh * 100)}%</span>
        </label>
        <input
          type="range" min="0.50" max="0.99" step="0.05"
          value={yoloHigh}
          onChange={(e) => setYoloHigh(parseFloat(e.target.value))}
        />
        <div className="field-help">
          Au-dessus de ce score → polype confirmé directement par YOLO, sans EfficientNet.
        </div>
      </div>

      <div className="info-box">
        📊 Zone d'incertitude : <b>{Math.round(yoloLow * 100)}% → {Math.round(yoloHigh * 100)}%</b>
        <br />Dans cette plage, EfficientNet est appelé pour confirmer.
      </div>

      <h3>Analyse vidéo</h3>

      <div className="field">
        <label>
          <span>Analyser 1 frame sur N</span>
          <span className="field-value">{frameSkip}</span>
        </label>
        <input
          type="range" min="1" max="15" step="1"
          value={frameSkip}
          onChange={(e) => setFrameSkip(parseInt(e.target.value, 10))}
        />
        <div className="field-help">Plus la valeur est haute, moins ça consomme de ressources.</div>
      </div>

      <div className="field">
        <label>
          <span>Durée minimale d'un segment (s)</span>
          <span className="field-value">{minSegmentDuration.toFixed(1)}s</span>
        </label>
        <input
          type="range" min="0.1" max="3.0" step="0.1"
          value={minSegmentDuration}
          onChange={(e) => setMinSegmentDuration(parseFloat(e.target.value))}
        />
        <div className="field-help">Ignore les détections trop courtes (bruit).</div>
      </div>

      <div className="footnote">medet — pipeline hybride v2 · interface React</div>
    </aside>
  );
}
