import { useEffect, useRef, useState } from "react";
import { analyzeStream, startStreamSession, pollStreamSession, stopStreamSession } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { createSegmentTracker } from "../lib/segments";
import { annotateBase64Image } from "../lib/drawBox";
import { segmentsToCsv, downloadCsv } from "../lib/exportCsv";
import ResultCard from "../components/ResultCard";
import Timeline from "../components/Timeline";
import GroupedSegmentList from "../components/GroupedSegmentList";

const POLL_DELAY_MS = 30; // délai entre deux /next pour ne pas saturer le backend

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error("délai dépassé")), ms)),
  ]);
}

export default function StreamMode() {
  const settings = useSettings();
  const [url, setUrl] = useState("rtsp://camera-ip:8554/mystream");
  const [error, setError] = useState(null);

  // ---- Mode LIVE (session persistante, vraie frame par frame) ----
  const [liveRunning, setLiveRunning] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [currentFrame, setCurrentFrame] = useState(null); // affichage vidéo continu
  const [livePoints, setLivePoints] = useState([]);
  const [pollAttempts, setPollAttempts] = useState(0);
  const [liveSegments, setLiveSegments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const sessionIdRef = useRef(null);
  const stopFlagRef = useRef(false);
  const trackerRef = useRef(createSegmentTracker(settings.gapThresholdSeconds));

  // ---- Mode ponctuel (un seul appel borné dans le temps) ----
  const [durationSeconds, setDurationSeconds] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    trackerRef.current = createSegmentTracker(settings.gapThresholdSeconds);
  }, [settings.gapThresholdSeconds]);

  useEffect(() => () => {
    stopFlagRef.current = true;
    if (sessionIdRef.current) stopStreamSession(sessionIdRef.current).catch(() => {});
  }, []);

  async function startLive() {
    setError(null);
    setConnecting(true);
    try {
      const { session_id } = await startStreamSession(url, settings.frameSkip);
      sessionIdRef.current = session_id;
      stopFlagRef.current = false;
      trackerRef.current.reset();
      setLivePoints([]);
      setLiveSegments([]);
      setSelectedId(null);
      setCurrentFrame(null);
      setPollAttempts(0);
      setLiveRunning(true);
      pollLoop();
    } catch (e) {
      setError(e.message);
    } finally {
      setConnecting(false);
    }
  }

  async function pollLoop() {
    while (!stopFlagRef.current && sessionIdRef.current) {
      setPollAttempts((n) => n + 1);
      try {
        const res = await pollStreamSession(sessionIdRef.current);
        if (res.status === "ended") {
          await endLive();
          break;
        }
        setLastResult(res);

        // Affichage vidéo continu : la boîte n'est dessinée que si détecté
        let annotatedFrame = null;
        if (res.frameBase64) {
          try {
            annotatedFrame = res.detected
              ? await withTimeout(annotateBase64Image(res.frameBase64, res.box, {
                  polypType: res.polypType,
                  label: res.polypLabel || res.polypType || "Anomalie",
                }), 2000)
              : res.frameBase64;
            setCurrentFrame(annotatedFrame);
          } catch (e) {
            console.warn("Échec du dessin de la boîte sur la frame reçue :", e);
            // On continue quand même la boucle avec l'image brute, sans boîte,
            // plutôt que de bloquer tout l'affichage.
            annotatedFrame = res.frameBase64;
            setCurrentFrame(annotatedFrame);
          }
        }

        // On ne garde l'image en mémoire dans les points/segments que pour
        // les détections positives (évite de saturer la mémoire du navigateur
        // sur une session longue).
        const pointFrameUrl = res.detected ? annotatedFrame : null;
        setLivePoints((prev) => [...prev, {
          elapsed: res.elapsedS, conf: res.maxConf || 0, detected: res.detected,
          type: res.polypType, frameUrl: pointFrameUrl,
        }]);
        const { segments: allSegments } = trackerRef.current.push({
          elapsed: res.elapsedS, detected: res.detected, type: res.polypType,
          conf: res.maxConf || 0, frameUrl: pointFrameUrl,
        });
        setLiveSegments(trackerRef.current.all());
        if (allSegments.length) setSelectedId((cur) => cur ?? allSegments[allSegments.length - 1].id);
      } catch (e) {
        setError(e.message);
        stopFlagRef.current = true;
        setLiveRunning(false);
        break;
      }
      await new Promise((r) => setTimeout(r, POLL_DELAY_MS));
    }
  }

  async function endLive() {
    stopFlagRef.current = true;
    trackerRef.current.close();
    setLiveSegments(trackerRef.current.all());
    setLiveRunning(false);
    if (sessionIdRef.current) {
      try { await stopStreamSession(sessionIdRef.current); } catch { /* déjà fermée */ }
      sessionIdRef.current = null;
    }
  }

  async function runOnce() {
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const res = await analyzeStream(url, { durationSeconds, frameSkip: settings.frameSkip });
      if (!res.connected) setError(res.message || "Connexion au flux impossible.");
      else setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function exportLiveCsv() {
    downloadCsv(`medet_flux_direct_${Date.now()}.csv`, segmentsToCsv(liveSegments));
  }
  function exportOnceCsv() {
    downloadCsv(`medet_flux_ponctuel_${Date.now()}.csv`, segmentsToCsv(result.segments));
  }

  return (
    <div>
      <div className="alert alert-info">
        🔗 Mode live avec image en direct — session persistante côté backend, une frame analysée et
        affichée à la fois (boîte dessinée quand un polype est détecté), comme le mode Webcam.
      </div>

      <div className="card">
        <label style={{ fontWeight: 600, fontSize: "0.88rem", display: "block", marginBottom: 8 }}>
          URL du flux (RTSP / HTTP / HTTPS)
        </label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="rtsp://camera-ip:8554/mystream"
          disabled={liveRunning || loading}
        />

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14, alignItems: "center" }}>
          {!liveRunning ? (
            <button className="btn btn-primary" disabled={!url || connecting || loading} onClick={startLive}>
              {connecting ? "Connexion…" : "▶️ Démarrer le direct"}
            </button>
          ) : (
            <button className="btn btn-danger" onClick={endLive}>⏹️ Arrêter le direct</button>
          )}

          <div style={{ borderLeft: "1px solid var(--border)", paddingLeft: 14, display: "flex", gap: 10, alignItems: "center" }}>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.85rem", color: "var(--ink-muted)" }}>
              Analyse ponctuelle — durée (s)
              <input
                type="number" min={1} max={600} value={durationSeconds} disabled={loading || liveRunning}
                onChange={(e) => setDurationSeconds(Math.min(600, Math.max(1, parseInt(e.target.value, 10) || 1)))}
                style={{ width: 80 }}
              />
            </label>
            <button className="btn" disabled={!url || loading || liveRunning} onClick={runOnce}>
              {loading ? `Analyse (${durationSeconds}s)…` : "Lancer"}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      {/* ---- Résultats LIVE ---- */}
      {(liveRunning || livePoints.length > 0) && (
        <div style={{ marginTop: 12 }}>
          {currentFrame && (
            <div className="frame-view" style={{ maxWidth: 560 }}>
              <img src={currentFrame} alt="Flux en direct" />
              <div className="frame-caption">
                {liveRunning && <><span className="live-dot" />En direct — t = {lastResult?.elapsedS?.toFixed(1)}s</>}
              </div>
            </div>
          )}

          <div className="stat-strip" style={{ marginTop: 12 }}>
            <span>Appels /next : <b>{pollAttempts}</b></span>
            <span>Frames analysées : <b>{livePoints.length}</b></span>
            <span>Segments détectés : <b>{liveSegments.length}</b></span>
          </div>

          {lastResult && (
            <div style={{ marginTop: 12 }}>
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

          {livePoints.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Timeline
                points={livePoints}
                segments={liveSegments}
                selectedId={selectedId}
                onSelectSegment={setSelectedId}
                durationS={livePoints[livePoints.length - 1]?.elapsed}
              />
            </div>
          )}

          <div className="card" style={{ marginTop: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, color: "var(--navy)", fontSize: "0.95rem" }}>Segments détectés (direct)</h3>
              <button className="btn" disabled={liveSegments.length === 0} onClick={exportLiveCsv}>⬇️ Exporter en CSV</button>
            </div>
            <div style={{ marginTop: 12 }}>
              <GroupedSegmentList segments={liveSegments} selectedId={selectedId} onSelect={setSelectedId} />
            </div>
          </div>
        </div>
      )}

      {/* ---- Résultats de l'analyse ponctuelle ---- */}
      {result && (
        <div style={{ marginTop: 20 }}>
          <div className="stat-strip">
            <span>Frames lues : <b>{result.totalFramesRead}</b></span>
            <span>Frames analysées : <b>{result.framesAnalyzed}</b></span>
            <span>Segments détectés : <b>{result.segments.length}</b></span>
            <span>Temps de traitement : <b>{Math.round(result.processingTimeMs)} ms</b></span>
          </div>
          {result.points.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Timeline points={result.points} segments={result.segments} selectedId={null} onSelectSegment={() => {}} durationS={durationSeconds} />
            </div>
          )}
          <div className="card" style={{ marginTop: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, color: "var(--navy)", fontSize: "0.95rem" }}>Segments détectés</h3>
              <button className="btn" disabled={result.segments.length === 0} onClick={exportOnceCsv}>⬇️ Exporter en CSV</button>
            </div>
            <div style={{ marginTop: 12 }}>
              <GroupedSegmentList segments={result.segments} selectedId={null} onSelect={() => {}} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
