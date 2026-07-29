// Le backend ne renvoie pas d'image annotée : on dessine la bounding_box
// nous-mêmes, à la résolution native de l'image envoyée, pour que le
// rectangle reste bien aligné quel que soit l'affichage (CSS width:100%
// mettra ensuite le tout à l'échelle correctement).

const BOX_COLORS = { "1p": "#D64550", "1s": "#E8A33D", "2": "#0F8B8D", "3": "#7C3AED" };
const DEFAULT_COLOR = "#D64550";

export function drawBoxOnCanvas(canvas, box, { color, label } = {}) {
  if (!box) return;
  const ctx = canvas.getContext("2d");
  const [x1, y1, x2, y2] = box;
  const strokeColor = color || DEFAULT_COLOR;
  const lineWidth = Math.max(2, Math.round(canvas.width / 250));

  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

  if (label) {
    ctx.font = `${Math.max(14, Math.round(canvas.width / 45))}px 'IBM Plex Sans', sans-serif`;
    const paddingX = 6;
    const textWidth = ctx.measureText(label).width;
    const textHeight = Math.max(18, Math.round(canvas.width / 32));
    const boxY = Math.max(0, y1 - textHeight);

    ctx.fillStyle = strokeColor;
    ctx.fillRect(x1, boxY, textWidth + paddingX * 2, textHeight);
    ctx.fillStyle = "#fff";
    ctx.textBaseline = "middle";
    ctx.fillText(label, x1 + paddingX, boxY + textHeight / 2);
  }
}

/**
 * Charge un fichier/blob image, dessine la bounding box dessus à la
 * résolution native, retourne une data URL prête pour <img src>.
 */
export async function annotateImageFile(file, box, { polypType, label } = {}) {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = reject;
      el.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    if (box) {
      drawBoxOnCanvas(canvas, box, { color: BOX_COLORS[polypType], label });
    }
    return canvas.toDataURL("image/jpeg", 0.92);
  } finally {
    URL.revokeObjectURL(url);
  }
}

/**
 * Variante pour le mode Webcam : le canvas contient déjà la frame capturée
 * (mêmes dimensions que l'image envoyée au backend) — on dessine dessus
 * directement, pas besoin de recharger une image.
 */
export function annotateCaptureCanvas(canvas, box, { polypType, label } = {}) {
  if (box) {
    drawBoxOnCanvas(canvas, box, { color: BOX_COLORS[polypType], label });
  }
  return canvas.toDataURL("image/jpeg", 0.85);
}

/**
 * Variante pour le mode Flux réseau : la frame arrive du backend en base64
 * (le navigateur ne peut pas décoder RTSP lui-même) — on charge cette image,
 * on dessine la boîte dessus à sa résolution native, on retourne une data URL.
 */
export async function annotateBase64Image(base64DataUrl, box, { polypType, label } = {}) {
  const img = await new Promise((resolve, reject) => {
    const el = new Image();
    el.onload = () => resolve(el);
    el.onerror = reject;
    el.src = base64DataUrl;
  });
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);
  if (box) {
    drawBoxOnCanvas(canvas, box, { color: BOX_COLORS[polypType], label });
  }
  return canvas.toDataURL("image/jpeg", 0.85);
}

export { BOX_COLORS };
