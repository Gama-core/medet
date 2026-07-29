function escapeCsvField(v) {
  const s = String(v ?? "");
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function toCsvString(rows) {
  return rows.map((r) => r.map(escapeCsvField).join(",")).join("\n");
}

export function segmentsToCsv(segments) {
  const header = ["#", "type", "label", "debut_s", "fin_s", "duree_s", "confiance_max", "frames_regroupees"];
  const rows = segments.map((s, i) => [
    i + 1,
    s.polyp_type ?? "",
    s.polyp_label || s.polyp_type || "",
    (s.start_s ?? 0).toFixed(2),
    (s.end_s ?? 0).toFixed(2),
    Math.max(0, (s.end_s ?? 0) - (s.start_s ?? 0)).toFixed(2),
    s.max_conf != null ? (s.max_conf * 100).toFixed(1) + "%" : "",
    s.n_frames ?? "",
  ]);
  return toCsvString([header, ...rows]);
}

export function pointsToCsv(points) {
  const header = ["instant_s", "detecte", "type", "confiance"];
  const rows = points.map((p) => [
    (p.elapsed ?? 0).toFixed(2),
    p.detected ? "oui" : "non",
    p.type ?? "",
    p.conf != null ? (p.conf * 100).toFixed(1) + "%" : "",
  ]);
  return toCsvString([header, ...rows]);
}

export function downloadCsv(filename, csvString) {
  // BOM UTF-8 pour qu'Excel affiche correctement les accents
  const blob = new Blob(["\uFEFF" + csvString], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
