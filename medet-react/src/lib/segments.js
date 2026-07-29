import { fmtTime } from "./time";

/**
 * Reproduit la logique de regroupement ("groupby") de app2.py :
 * les détections consécutives du même type de polype sont fusionnées
 * en un seul segment tant que l'écart entre deux détections reste
 * inférieur à gapThresholdSeconds. Un changement de type, ou un écart
 * trop grand, ferme le segment courant et en ouvre un nouveau.
 *
 * Usage :
 *   const tracker = createSegmentTracker(gapThresholdSeconds);
 *   const { current, closedSegment } = tracker.push({ elapsed, detected, type, conf, frameUrl });
 *   const last = tracker.close(); // à l'arrêt du flux
 */
/**
 * Regroupe une liste plate de segments par type de polype.
 * Chaque groupe expose : la première occurrence (temporellement),
 * et la liste complète des occurrences triée par heure de début.
 * Sert à l'affichage "collapsed" : un type de polype qui apparaît
 * plusieurs fois dans la vidéo/session n'affiche qu'une seule entrée,
 * dépliable pour voir tous les instants où il a été détecté.
 */
export function groupSegmentsByType(segments) {
  const byType = new Map();
  for (const seg of segments) {
    const key = seg.polyp_type || "inconnu";
    if (!byType.has(key)) byType.set(key, []);
    byType.get(key).push(seg);
  }
  const groups = [];
  for (const [type, instances] of byType.entries()) {
    const sorted = [...instances].sort((a, b) => a.start_s - b.start_s);
    groups.push({
      id: `group-${type}`,
      polyp_type: type === "inconnu" ? null : type,
      instances: sorted,
      count: sorted.length,
      first: sorted[0],
    });
  }
  // Groupes ordonnés par première apparition
  groups.sort((a, b) => a.first.start_s - b.first.start_s);
  return groups;
}

export function createSegmentTracker(gapThresholdSeconds = 1.5) {
  let current = null; // segment en cours de construction
  const segments = [];

  function startSegment({ elapsed, type, conf, frameUrl }) {
    current = {
      id: `seg-${segments.length}-${Date.now()}`,
      start_s: elapsed,
      end_s: elapsed,
      start_ts: fmtTime(elapsed),
      end_ts: fmtTime(elapsed),
      max_conf: conf,
      polyp_type: type,
      type_conf: conf,
      n_frames: 1,
      best_frame_url: frameUrl,
    };
  }

  function finalizeCurrent() {
    if (!current) return null;
    const finished = { ...current };
    segments.push(finished);
    current = null;
    return finished;
  }

  function push({ elapsed, detected, type = null, conf = 0, frameUrl = null }) {
    let closedSegment = null;

    if (detected) {
      const sameType = current && current.polyp_type === type;
      const gapOk = current && elapsed - current.end_s <= gapThresholdSeconds;

      if (!current) {
        startSegment({ elapsed, type, conf, frameUrl });
      } else if (sameType && gapOk) {
        current.end_s = elapsed;
        current.end_ts = fmtTime(elapsed);
        current.n_frames += 1;
        if (conf > current.max_conf) {
          current.max_conf = conf;
          current.type_conf = conf;
          current.best_frame_url = frameUrl;
        }
      } else {
        closedSegment = finalizeCurrent();
        startSegment({ elapsed, type, conf, frameUrl });
      }
    } else if (current && elapsed - current.end_s > gapThresholdSeconds) {
      closedSegment = finalizeCurrent();
    }

    return { current, closedSegment, segments: [...segments] };
  }

  function close() {
    return finalizeCurrent();
  }

  function all() {
    return current ? [...segments, current] : [...segments];
  }

  function reset() {
    current = null;
    segments.length = 0;
  }

  return { push, close, all, reset };
}
