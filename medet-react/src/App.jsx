import { useState } from "react";
import { SettingsProvider } from "./context/SettingsContext";
import SettingsSidebar from "./components/SettingsSidebar";
import Header from "./components/Header";
import ModeTabs from "./components/ModeTabs";
import ImageMode from "./modes/ImageMode";
import VideoMode from "./modes/VideoMode";
import WebcamMode from "./modes/WebcamMode";
import StreamMode from "./modes/StreamMode";
import RecordsMode from "./modes/RecordsMode";

export default function App() {
  const [mode, setMode] = useState("image");

  return (
    <SettingsProvider>
      <div className="app-shell">
        <SettingsSidebar />
        <main className="main">
          <Header />
          <ModeTabs mode={mode} onChange={setMode} />

          {mode === "image" && <ImageMode />}
          {mode === "video" && <VideoMode />}
          {mode === "webcam" && <WebcamMode />}
          {mode === "stream" && <StreamMode />}
          {mode === "records" && <RecordsMode />}

          <div className="divider" />
          <p className="footer">
            medet — outil d'aide au diagnostic, usage interne uniquement. Ne remplace pas l'avis d'un médecin.
          </p>
        </main>
      </div>
    </SettingsProvider>
  );
}
