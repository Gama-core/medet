"""
Utilitaire de dessin — annote une image avec la boite englobante et le label
predit. Utile pour le debug, ou pour un futur endpoint qui renverrait l'image
annotee directement (actuellement les endpoints /predict/* renvoient les
coordonnees brutes, le dessin cote client est generalement plus flexible).
"""

from PIL import Image, ImageDraw, ImageFont


def draw_prediction(
    image: Image.Image,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    label: str,
    color: tuple = (255, 0, 0),
) -> Image.Image:
    """Retourne une copie de l'image avec la boite englobante et le label dessines dessus."""
    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    text_position = (x1, max(y1 - 18, 0))
    text_bbox = draw.textbbox(text_position, label, font=font)
    draw.rectangle(text_bbox, fill=color)
    draw.text(text_position, label, fill=(255, 255, 255), font=font)

    return annotated
