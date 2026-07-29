// -----------------------------------------------------------------------
// Client API — backend FastAPI "medet"
// -----------------------------------------------------------------------
// Toutes les routes et la forme des réponses supposées sont centralisées
// ici. Si le contrat réel du backend diffère, c'est le SEUL fichier à
// modifier (voir API_CONTRACT.md à la racine pour le détail complet des
// hypothèses faites, endpoint par endpoint).

import { fmtTime } from "./time";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, { method = "GET", body, params, isForm = false, treatNotFoundAsEmpty = false } = {}) {
  let url = `${API_BASE_URL}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
    );
    const qsStr = qs.toString();
    if (qsStr) url += `?${qsStr}`;
  }

  const opts = { method };
  if (body !== undefined) {
    if (isForm) {
      opts.body = body; // FormData — le navigateur pose le Content-Type
    } else {
      opts.headers = { "Content-Type": "application/json" };
      opts.body = JSON.stringify(body);
    }
  }

  const res = await fetch(url, opts);

  // Le backend renvoie un 404 pour signifier "aucun polype détecté" sur
  // les endpoints de prédiction — ce n'est pas une erreur réseau, c'est
  // une réponse valide qu'on doit traiter comme "detected: false".
  if (res.status === 404 && treatNotFoundAsEmpty) {
    let detail = "Aucune détection au-dessus du seuil.";
    try {
      const errJson = await res.json();
      detail = errJson.detail || detail;
    } catch { /* pas de corps JSON */ }
    return { notFoundEmpty: true, detail };
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errJson = await res.json();
      if (Array.isArray(errJson.detail)) {
        // Erreur de validation FastAPI/Pydantic : liste de {loc, msg, type}
        detail = errJson.detail
          .map((e) => `${(e.loc || []).slice(1).join(".")} : ${e.msg}`)
          .join(" · ");
      } else {
        detail = errJson.detail || JSON.stringify(errJson);
      }
    } catch {
      /* réponse non-JSON, on garde statusText */
    }
    throw new Error(`${res.status} — ${detail}`);
  }
  return res;
}

async function requestJson(path, opts) {
  const res = await request(path, opts);
  return readPredictionBody(res);
}

// ---------------------------------------------------------------------
// Santé backend
// ---------------------------------------------------------------------
export function getHealth() {
  return requestJson("/health");
}

// ---------------------------------------------------------------------
// Seuils envoyés à chaque appel de prédiction
// ---------------------------------------------------------------------
function thresholdParams({ yoloLow, yoloHigh, frameSkip, minSegmentDuration } = {}) {
  return {
    yolo_low: yoloLow,
    yolo_high: yoloHigh,
    frame_skip: frameSkip,
    min_segment_duration: minSegmentDuration,
  };
}

// ---------------------------------------------------------------------
// Forme RÉELLE de la réponse backend (confirmée le 25/07) :
// {
//   is_polyp: bool,
//   polyp_type: "1p"|"1s"|"2"|"3"|null,
//   polyp_label: "Polype sessile (1s)"|null,
//   confidence: float,              // confiance de la classification de type
//   all_probabilities: { "1p": .., "1s": .., "2": .., "3": .. },
//   yolo_confidence: float,         // score YOLO (étage 1)
//   yolo_zone: "ignored"|"uncertain"|"high",
//   bounding_box: { x1, y1, x2, y2 } | null,
//   action: "ignored"|"yolo_only"|"verified_and_classified",
//   processing_time_ms: float
// }
// Pas d'image annotée renvoyée par le backend -> la boîte est dessinée
// côté client (voir src/lib/drawBox.js).
// ---------------------------------------------------------------------
export function normalizePrediction(raw) {
  if (raw && raw.notFoundEmpty) {
    return {
      detected: false,
      maxConf: 0,
      polypType: null,
      polypLabel: null,
      typeConf: null,
      allProbabilities: null,
      yoloZone: null,
      action: "no_detection",
      box: null,
      processingTimeMs: null,
      message: raw.detail,
      raw,
    };
  }
  return {
    detected: !!raw.is_polyp,
    maxConf: raw.yolo_confidence ?? 0,
    polypType: raw.polyp_type ?? null,
    polypLabel: raw.polyp_label ?? null,
    typeConf: raw.confidence ?? null,
    allProbabilities: raw.all_probabilities ?? null,
    yoloZone: raw.yolo_zone ?? null,
    action: raw.action ?? null,
    box: raw.bounding_box
      ? [raw.bounding_box.x1, raw.bounding_box.y1, raw.bounding_box.x2, raw.bounding_box.y2]
      : null,
    processingTimeMs: raw.processing_time_ms ?? null,
    raw,
  };
}

// Lit le corps JSON d'un résultat de request(), qu'il s'agisse d'une
// vraie Response ou du marqueur synthétique "404 = pas de détection".
async function readPredictionBody(res) {
  if (res && res.notFoundEmpty) return res;
  return res.json();
}

// ---------------------------------------------------------------------
// Mode Image — POST /predict/image (multipart: file)
// ---------------------------------------------------------------------
export async function predictImage(file, thresholds) {
  const form = new FormData();
  form.append("file", file);
  const res = await request("/predict/image", {
    method: "POST",
    body: form,
    isForm: true,
    params: thresholdParams(thresholds),
    treatNotFoundAsEmpty: true,
  });
  const json = await readPredictionBody(res);
  return normalizePrediction(json);
}

// ---------------------------------------------------------------------
// Mode Vidéo (analyse bulk backend) — POST /predict/video (multipart: file)
// ⚠️ Le router video.py n'a pas été vu — je pars du principe qu'il
// renvoie un VideoResult (même structure que StreamResult, confirmée
// via schemas.py, car les deux réutilisent process_capture côté backend) :
// { total_frames_read, frames_analyzed, fps_source, detections, segments,
//   processing_time_ms }
// L'app utilise plutôt l'analyse live frame-par-frame (predictImage en
// boucle) pour l'affichage progressif ; cette fonction sert de solution
// de repli / pour l'export CSV.
// ---------------------------------------------------------------------
export async function predictVideoBulk(file, thresholds) {
  const form = new FormData();
  form.append("file", file);
  const json = await requestJson("/predict/video", {
    method: "POST",
    body: form,
    isForm: true,
    params: thresholdParams(thresholds),
  });
  return normalizeBulkResult(json);
}

// ⚠️ Non confirmé : on ne sait pas si /predict/video accepte réellement
// un paramètre `export=csv` qui renvoie un CSV brut au lieu du JSON.
// Si ça échoue, il faudra soit l'ajouter côté backend, soit générer le
// CSV côté client à partir de normalizeBulkResult().
export async function downloadVideoReportCsv(file, thresholds) {
  const form = new FormData();
  form.append("file", file);
  const res = await request("/predict/video", {
    method: "POST",
    body: form,
    isForm: true,
    params: { ...thresholdParams(thresholds), export: "csv" },
  });
  return res.blob();
}

// ---------------------------------------------------------------------
// Mode Webcam — POST /predict/webcam (multipart: frame, image/jpeg)
// Appelé une fois par frame capturée côté navigateur (getUserMedia + canvas).
// Réponse attendue : identique à /predict/image.
// ---------------------------------------------------------------------
export async function predictWebcamFrame(blob, thresholds) {
  const form = new FormData();
  form.append("frame", blob, "frame.jpg");
  const res = await request("/predict/webcam", {
    method: "POST",
    body: form,
    isForm: true,
    params: thresholdParams(thresholds),
    treatNotFoundAsEmpty: true,
  });
  const json = await readPredictionBody(res);
  return normalizePrediction(json);
}

// ---------------------------------------------------------------------
// Mode Flux réseau (RTSP/HTTP) — CONFIRMÉ le 25/07 via schemas.py + stream.py :
// POST /predict/stream (JSON body), un seul appel BLOQUANT et BORNÉ DANS
// LE TEMPS. Pas de session/polling : le backend se connecte, analyse
// pendant `duration_seconds` (1..600s), puis renvoie tout le résultat
// d'un coup. Aucune image de frame renvoyée (juste bounding_box).
//
// StreamRequest { url, duration_seconds, frame_skip, export? }
// StreamResult  { url, connected, total_frames_read, frames_analyzed,
//                 detections: FrameResult[], segments: SegmentResult[],
//                 processing_time_ms, message }
// FrameResult   { frame_index, timestamp_seconds, prediction: PredictionResponse|null }
// SegmentResult { start_timestamp_seconds, end_timestamp_seconds, duration_seconds,
//                 polyp_type, polyp_label, max_confidence, frame_count }
//
// ⚠️ Le champ `export` existe dans StreamRequest mais n'est référencé
// nulle part dans stream_processor.py — il semble non câblé. Ne pas
// compter dessus tant que ce n'est pas confirmé côté backend.
// ---------------------------------------------------------------------
function normalizeSegment(s, i) {
  return {
    id: `seg-${i}-${s.start_timestamp_seconds}`,
    start_s: s.start_timestamp_seconds,
    end_s: s.end_timestamp_seconds,
    start_ts: fmtTime(s.start_timestamp_seconds),
    end_ts: fmtTime(s.end_timestamp_seconds),
    max_conf: s.max_confidence,
    polyp_type: s.polyp_type,
    polyp_label: s.polyp_label,
    type_conf: null, // non fourni par SegmentResult
    n_frames: s.frame_count,
    best_frame_url: null, // le backend ne renvoie pas d'image pour vidéo/flux
  };
}

function normalizeDetectionPoint(d) {
  const pred = d.prediction;
  return {
    elapsed: d.timestamp_seconds,
    frameIndex: d.frame_index,
    conf: pred ? pred.yolo_confidence ?? 0 : 0,
    detected: !!pred?.is_polyp,
    type: pred?.polyp_type ?? null,
    box: pred?.bounding_box
      ? [pred.bounding_box.x1, pred.bounding_box.y1, pred.bounding_box.x2, pred.bounding_box.y2]
      : null,
    frameUrl: null, // pas d'image renvoyée par le backend pour ce mode
  };
}


export function normalizeBulkResult(raw) {
  return {
    connected: raw.connected ?? true,
    totalFramesRead: raw.total_frames_read,
    framesAnalyzed: raw.frames_analyzed,
    processingTimeMs: raw.processing_time_ms,
    message: raw.message ?? null,
    points: (raw.detections || []).map(normalizeDetectionPoint),
    segments: (raw.segments || []).map(normalizeSegment),
  };
}

export async function analyzeStream(url, { durationSeconds = 30, frameSkip } = {}) {
  const json = await requestJson("/predict/stream", {
    method: "POST",
    body: { url, duration_seconds: durationSeconds, frame_skip: frameSkip },
  });
  return normalizeBulkResult(json);
}

// ---------------------------------------------------------------------
// Mode Flux réseau LIVE — session persistante confirmée fonctionnelle le
// 26/07 (backend/routers/stream.py : /stream/start, /stream/{id}/next,
// /stream/{id}/stop). Réutilise run_pipeline_on_image côté serveur, donc
// la réponse de /next a la même forme qu'une PredictionResponse (comme
// /predict/image), enrichie de { status, elapsed_s }.
// ---------------------------------------------------------------------
export function startStreamSession(url, frameSkip) {
  return requestJson("/predict/stream/start", {
    method: "POST",
    body: { url, frame_skip: frameSkip },
  });
}

export async function pollStreamSession(sessionId) {
  const json = await requestJson(`/predict/stream/${sessionId}/next`, { treatNotFoundAsEmpty: true });
  if (json.status === "ended") return { status: "ended" };
  return {
    status: "ok",
    elapsedS: json.elapsed_s,
    frameBase64: json.frame_base64 ?? null,
    ...normalizePrediction(json),
  };
}

export function stopStreamSession(sessionId) {
  return requestJson(`/predict/stream/${sessionId}/stop`, { method: "POST" });
}

// ---------------------------------------------------------------------
// Dossiers (records) — historique des examens
// ---------------------------------------------------------------------
export function listRecords() {
  return requestJson("/records");
}
export function getRecord(id) {
  return requestJson(`/records/${id}`);
}
export function deleteRecord(id) {
  return request(`/records/${id}`, { method: "DELETE" });
}
export function shareRecord(id) {
  return requestJson(`/records/${id}/share`, { method: "POST" });
}
export function unshareRecord(id) {
  return request(`/records/${id}/share`, { method: "DELETE" });
}
