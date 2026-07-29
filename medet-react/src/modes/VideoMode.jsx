import { useEffect, useRef, useState } from "react";
import { predictImage } from "../lib/api";
import { segmentsToCsv, downloadCsv } from "../lib/exportCsv";
import { useSettings } from "../context/SettingsContext";
import { createSegmentTracker } from "../lib/segments";
import { annotateCaptureCanvas } from "../lib/drawBox";
import Timeline from "../components/Timeline";
import GroupedSegmentList from "../components/GroupedSegmentList";

// Intervalle entre deux frames analysées, en secondes vidéo (indépendant
// de la vitesse de lecture réelle) — dérivé du "frame_skip" des réglages.
function analysisIntervalSeconds(frameSkip) {
  return Math.max(0.15, frameSkip / 25); // 25 fps de référence, comme app2.py
}

export default function VideoMode() {
  const settings = useSettings();
  const [file, setFile] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | paused | done
  const [error, setError] = useState(null);
  const [points, setPoints] = useState([]);
  const [segments, setSegments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [drag, setDrag] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);

  const inputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));
  const trackerRef = useRef(createSegmentTracker(settings.gapThresholdSeconds));
  const lastAnalyzedRef = useRef(-999);
  const busyRef = useRef(false);
  const rafRef = useRef(null);

  useEffect(() => {
    trackerRef.current = createSegmentTracker(settings.gapThresholdSeconds);
  }, [settings.gapThresholdSeconds]);

  function handleFile(f) {
    if (!f) return;
    stopLoop();
    setFile(f);
    setVideoUrl(URL.createObjectURL(f));
    setPoints([]);
    setSegments([]);
    setSelectedId(null);
    setError(null);
    setStatus("idle");
    trackerRef.current.reset();
  }

  async function analyzeCurrentFrame() {
    if (busyRef.current || !videoRef.current || !file) return;
    const video = videoRef.current;
    const elapsed = video.currentTime;
    if (elapsed - lastAnalyzedRef.current < analysisIntervalSeconds(settings.frameSkip)) return;
    lastAnalyzedRef.current = elapsed;
    busyRef.current = true;
    try {
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
      if (!blob) return;
      const blobFile = new File([blob], "frame.jpg", { type: "image/jpeg" });

      const res = await predictImage(blobFile, settings);
      const frameUrl = res.detected
        ? annotateCaptureCanvas(canvas, res.box, { polypType: res.polypType, label: res.polypLabel || res.polypType })
        : null;

      setPoints((prev) => [...prev, { elapsed, conf: res.maxConf || 0, detected: res.detected, type: res.polypType, frameUrl }]);

      const { segments: allSegments } = trackerRef.current.push({
        elapsed, detected: res.detected, type: res.polypType, conf: res.maxConf || 0, frameUrl,
      });
      setSegments(trackerRef.current.all());
      if (allSegments.length) setSelectedId((cur) => cur ?? allSegments[allSegments.length - 1].id);
    } catch (e) {
      setError(e.message);
    } finally {
      busyRef.current = false;
    }
  }

  function loop() {
    analyzeCurrentFrame();
    rafRef.current = requestAnimationFrame(loop);
  }

  function stopLoop() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }

  async function startAnalysis() {
    if (!file || !videoRef.current) return;
    setError(null);
    setPoints([]);
    setSegments([]);
    setSelectedId(null);
    trackerRef.current.reset();
    lastAnalyzedRef.current = -999;
    videoRef.current.currentTime = 0;
    videoRef.current.playbackRate = playbackRate;
    await videoRef.current.play();
    setStatus("analyzing");
    loop();
  }

  function pauseAnalysis() {
    videoRef.current?.pause();
    stopLoop();
    setStatus("paused");
  }

  function resumeAnalysis() {
    videoRef.current?.play();
    setStatus("analyzing");
    loop();
  }

  function handleEnded() {
    stopLoop();
    trackerRef.current.close();
    setSegments(trackerRef.current.all());
    setStatus("done");
  }

  useEffect(() => () => stopLoop(), []);

  function exportCsv() {
    if (segments.length === 0) return;
    downloadCsv(`medet_video_${(file?.name || "rapport").replace(/\.[^.]+$/, "")}.csv`, segmentsToCsv(segments));
  }

  function selectSegment(id) {
    setSelectedId(id);
    const seg = segments.find((s) => s.id === id);
    if (seg && videoRef.current && status !== "analyzing") {
      videoRef.current.currentTime = seg.start_s;
    }
  }

  return (
    <div>
      <div
        className={`dropzone${drag ? " drag" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files?.[0]); }}
        onClick={() => inputRef.current?.click()}
        style={{ cursor: status === "analyzing" ? "not-allowed" : "pointer" }}
      >
        <input ref={inputRef} type="file" accept="video/*" onChange={(e) => handleFile(e.target.files?.[0])} />
        {file ? <span>🎬 {file.name} — cliquez pour changer</span> : <span>Glissez-déposez une vidéo endoscopique, ou cliquez pour parcourir</span>}
      </div>

      {videoUrl && (
        <div className="frame-view" style={{ marginTop: 16, maxWidth: 560 }}>
          <video ref={videoRef} src={videoUrl} muted playsInline onEnded={handleEnded} controls={status === "idle" || status === "done"} />
          <div className="frame-caption">
            {status === "analyzing" && <><span className="live-dot" />Analyse en cours — les segments apparaissent en direct ci-dessous</>}
            {status === "paused" && "En pause"}
            {status === "done" && "Analyse terminée — cliquez un segment pour vous y repositionner"}
            {status === "idle" && "Prêt à analyser"}
          </div>
        </div>
      )}

      <div style={{ marginTop: 16, display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        {status === "idle" && (
          <button className="btn btn-primary" disabled={!file} onClick={startAnalysis}>▶️ Démarrer l'analyse</button>
        )}
        {status === "analyzing" && (
          <button className="btn btn-danger" onClick={pauseAnalysis}>⏸️ Pause</button>
        )}
        {status === "paused" && (
          <button className="btn btn-primary" onClick={resumeAnalysis}>▶️ Reprendre</button>
        )}
        {status === "done" && (
          <button className="btn btn-primary" onClick={startAnalysis}>🔁 Ré-analyser</button>
        )}

        {status === "idle" && (
          <label style={{ fontSize: "0.85rem", color: "var(--ink-muted)", display: "flex", alignItems: "center", gap: 6 }}>
            Vitesse d'analyse :
            <select value={playbackRate} onChange={(e) => setPlaybackRate(parseFloat(e.target.value))}>
              <option value={1}>1×</option>
              <option value={2}>2×</option>
              <option value={4}>4×</option>
            </select>
          </label>
        )}

        <button className="btn" disabled={segments.length === 0} onClick={exportCsv}>
          ⬇️ Exporter en CSV
        </button>
      </div>

      {error && <div className="alert alert-error" style={{ marginTop: 16 }}>⚠️ {error}</div>}

      {points.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div className="stat-strip">
            <span>Position : <b>{videoRef.current ? Math.round(videoRef.current.currentTime) : 0}s</b></span>
            <span>Frames analysées : <b>{points.length}</b></span>
            <span>Segments détectés : <b>{segments.length}</b></span>
          </div>

          <div style={{ marginTop: 16 }}>
            <Timeline
              points={points}
              segments={segments}
              selectedId={selectedId}
              onSelectSegment={selectSegment}
              durationS={videoRef.current?.duration}
            />
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0, color: "var(--navy)", fontSize: "0.95rem" }}>Segments détectés</h3>
            <GroupedSegmentList segments={segments} selectedId={selectedId} onSelect={selectSegment} />
          </div>
        </div>
      )}
    </div>
  );
}
