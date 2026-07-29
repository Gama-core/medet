export default function Header() {
  return (
    <div className="medet-header">
      <div className="medet-header-mark">🩺</div>
      <div>
        <div className="medet-eyebrow">Aide au diagnostic endoscopique</div>
        <h1 className="medet-title">medet</h1>
        <p className="medet-subtitle">
          Pipeline hybride YOLO (étage 1) + EfficientNet (étage 2 / 2b) — usage interne, pas d'utilisation clinique.
        </p>
      </div>
    </div>
  );
}
