import { useEffect, useRef, useState } from "react";
import { predictWebcamFrame } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { createSegmentTracker } from "../lib/segments";
import { annotateCaptureCanvas } from "../lib/drawBox";
import ResultCard from "../components/ResultCard";
import Timeline from "../components/Timeline";
import GroupedSegmentList from "../components/GroupedSegmentList";
import { segmentsToCsv, downloadCsv } from "../lib/exportCsv";

const CAPTURE_INTERVAL_MS = 400; // ~2.5 img/s envoyées au backend

export default function WebcamMode() {
  const settings = useSettings();
  const videoRef = useRef(null);
  const canvasRef = useRef(document.createElement("canvas"));
  const streamRef = useRef(null);
  const trackerRef = useRef(createSegmentTracker(settings.gapThresholdSeconds));
  const startTsRef = useRef(null);
  const timerRef = useRef(null);
  const busyRef = useRef(false);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [lastResult, setLastResult] = useState(null);
  const [points, setPoints] = useState([]);
  const [segments, setSegments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    trackerRef.current = createSegmentTracker(settings.gapThresholdSeconds);
  }, [settings.gapThresholdSeconds]);

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      trackerRef.current.reset();
      setSegments([]);
      setPoints([]);
      setSelectedId(null);
      startTsRef.current = performance.now();
      setRunning(true);
      timerRef.current = setInterval(captureAndAnalyze, CAPTURE_INTERVAL_MS);
    } catch (e) {
      setError("Impossible d'accéder à la caméra : " + e.message);
    }
  }

  function stop() {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setRunning(false);
    trackerRef.current.close();
    setSegments(trackerRef.current.all());
  }

  async function captureAndAnalyze() {
    if (busyRef.current || !videoRef.current) return;
    busyRef.current = true;
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
      if (!blob) return;

      const elapsed = (performance.now() - startTsRef.current) / 1000;
      const res = await predictWebcamFrame(blob, settings);
      const frameUrl = res.detected
        ? annotateCaptureCanvas(canvas, res.box, { polypType: res.polypType, label: res.polypLabel || res.polypType || "Anomalie" })
        : null;
      setLastResult({ ...res, frameUrl });

      setPoints((prev) => [...prev, { elapsed, conf: res.maxConf || 0, detected: res.detected, type: res.polypType, frameUrl }]);

      const { segments: allSegments } = trackerRef.current.push({
        elapsed,
        detected: res.detected,
        type: res.polypType,
        conf: res.maxConf || 0,
        frameUrl,
      });
      setSegments(trackerRef.current.all());
      if (allSegments.length) setSelectedId((cur) => cur ?? allSegments[allSegments.length - 1].id);
    } catch (e) {
      setError(e.message);
    } finally {
      busyRef.current = false;
    }
  }

  useEffect(() => () => {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  return (
    <div>
      <div className="alert alert-info">
        📷 Démo streaming sans matériel réel — utilise la caméra de cet appareil, image par image, comme
        simulation du flux d'une tour d'endoscopie. Les segments apparaissent en direct pendant l'analyse.
      </div>

      <div className="frame-view" style={{ maxWidth: 560 }}>
        <video ref={videoRef} muted playsInline style={{ display: running ? "block" : "none" }} />
        {!running && (
          <div style={{
            aspectRatio: "4/3", display: "flex", alignItems: "center",
            justifyContent: "center", color: "#8AA0AC", fontSize: "0.9rem",
          }}>
            Caméra arrêtée
          </div>
        )}
        {running && (
          <div className="frame-caption">
            <span className="live-dot" />En direct — analyse toutes les {CAPTURE_INTERVAL_MS}ms
          </div>
        )}
      </div>

      <div style={{ marginTop: 16, display: "flex", gap: 10 }}>
        {!running ? (
          <button className="btn btn-primary" onClick={start}>▶️ Démarrer la caméra</button>
        ) : (
          <button className="btn btn-danger" onClick={stop}>⏹️ Arrêter</button>
        )}
      </div>

      {error && <div className="alert alert-error" style={{ marginTop: 16 }}>⚠️ {error}</div>}

      {lastResult && (
        <div style={{ marginTop: 20 }}>
          <ResultCard
            detected={lastResult.detected}
            maxConf={lastResult.maxConf}
            polypType={lastResult.polypType}
            polypLabel={lastResult.polypLabel}
            typeConf={lastResult.typeConf}
            yoloZone={lastResult.yoloZone}
          />
        </div>
      )}

      {points.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Timeline
            points={points}
            segments={segments}
            selectedId={selectedId}
            onSelectSegment={setSelectedId}
            durationS={points[points.length - 1]?.elapsed}
          />
        </div>
      )}

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, color: "var(--navy)", fontSize: "0.95rem" }}>
            Segments de la session ({segments.length})
          </h3>
          <button
            className="btn"
            disabled={segments.length === 0}
            onClick={() => downloadCsv(`medet_webcam_${Date.now()}.csv`, segmentsToCsv(segments))}
          >
            ⬇️ Exporter en CSV
          </button>
        </div>
        <div style={{ marginTop: 12 }}>
          <GroupedSegmentList segments={segments} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
      </div>
    </div>
  );
}
