const MODES = [
  { id: "image", label: "🖼️ Image" },
  { id: "video", label: "🎬 Vidéo" },
  { id: "webcam", label: "📷 Webcam (live)" },
  { id: "stream", label: "🔗 Flux réseau (URL)" },
  { id: "records", label: "🗂️ Historique" },
];

export default function ModeTabs({ mode, onChange }) {
  return (
    <div className="mode-tabs" role="tablist" aria-label="Mode d'entrée">
      {MODES.map((m) => (
        <button
          key={m.id}
          role="tab"
          aria-selected={mode === m.id}
          className={`mode-tab${mode === m.id ? " active" : ""}`}
          onClick={() => onChange(m.id)}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
