"""Create restrained conceptual and procedural figures for the paper draft."""

from pathlib import Path

from PIL import Image, ImageDraw

from make_preview_pareto import font


HERE = Path(__file__).resolve().parent
SCALE = 2
INK = "#111111"
LINE = "#7d908c"
ACCENT = "#135d61"


def canvas(width, height, title):
    image = Image.new("RGB", (width * SCALE, height * SCALE), "white")
    ink = ImageDraw.Draw(image)
    ink.text((width * SCALE / 2, 42 * SCALE), title, font=font(27, True), fill=INK, anchor="mm")
    return image, ink


def box(ink, x, y, w, h, heading, lines=()):
    coords = (x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE)
    ink.rounded_rectangle(coords, radius=5 * SCALE, fill="#f8faf9", outline=LINE, width=2 * SCALE)
    ink.rectangle((x * SCALE, y * SCALE, (x + 6) * SCALE, (y + h) * SCALE), fill=ACCENT)
    ink.text(((x + w / 2) * SCALE, (y + 29) * SCALE), heading, font=font(19, True), fill=INK, anchor="mm")
    for index, line in enumerate(lines):
        ink.text(((x + w / 2) * SCALE, (y + 62 + index * 24) * SCALE), line, font=font(15), fill=INK, anchor="mm")


def arrow(ink, x1, y1, x2, y2):
    ink.line(((x1 * SCALE, y1 * SCALE), (x2 * SCALE, y2 * SCALE)), fill=ACCENT, width=3 * SCALE)
    ink.polygon(((x2 * SCALE, y2 * SCALE), ((x2 - 12) * SCALE, (y2 - 7) * SCALE), ((x2 - 12) * SCALE, (y2 + 7) * SCALE)), fill=ACCENT)


def save(image, name, width, height):
    path = HERE / name
    image.resize((width, height), Image.Resampling.LANCZOS).save(path, optimize=True)
    print(path)


def conceptual():
    width, height = 1600, 400
    image, ink = canvas(width, height, "Governance, Form and Preference")
    boxes = [
        (55, "Urban evidence", ("Buildings and streets", "Heritage records")),
        (450, "Governance rules", ("Who may change what", "Allowed form operations")),
        (845, "Spatial trade-offs", ("Three shared objectives", "Pareto alternatives")),
        (1240, "Role interpretation", ("Ordinal priorities", "3D and building changes")),
    ]
    for x, heading, lines in boxes:
        box(ink, x, 127, 305, 150, heading, lines)
    for x in (360, 755, 1150):
        arrow(ink, x + 8, 202, x + 82, 202)
    ink.text((800 * SCALE, 332 * SCALE), "Rules shape the candidate set; preferences select from it.", font=font(17, True), fill=INK, anchor="mm")
    save(image, "conceptual_framework.png", width, height)


def workflow():
    width, height = 1600, 390
    image, ink = canvas(width, height, "Research Workflow")
    centers = [145, 405, 665, 925, 1185, 1445]
    labels = ["Urban data", "Scenario rules", "Form generation", "Pareto search", "Role choice", "3D review"]
    for x in centers:
        ink.rounded_rectangle(((x - 97) * SCALE, 120 * SCALE, (x + 97) * SCALE, 270 * SCALE), radius=7 * SCALE, fill="#fbfcfb", outline="#aab4b2", width=2 * SCALE)
    for x in (242, 502, 762, 1022, 1282):
        arrow(ink, x + 5, 194, x + 70, 194)
    for x, label in zip(centers, labels):
        ink.text((x * SCALE, 309 * SCALE), label, font=font(19, True), fill=INK, anchor="mm")
    # Roads and buildings
    for dx in (-42, 0, 42):
        ink.rectangle(((centers[0] + dx - 15) * SCALE, 165 * SCALE, (centers[0] + dx + 15) * SCALE, 224 * SCALE), outline=INK, width=2 * SCALE)
    ink.line(((85 * SCALE, 151 * SCALE), (205 * SCALE, 240 * SCALE)), fill=INK, width=3 * SCALE)
    # Rule sliders
    for dy, knob in ((-27, -20), (0, 28), (27, 0)):
        y = 194 + dy
        ink.line(((355 * SCALE, y * SCALE), (455 * SCALE, y * SCALE)), fill=INK, width=2 * SCALE)
        ink.ellipse(((405 + knob - 6) * SCALE, (y - 6) * SCALE, (405 + knob + 6) * SCALE, (y + 6) * SCALE), fill="white", outline=INK, width=2 * SCALE)
    # Massing block silhouettes
    for dx, h in ((-45, 38), (-12, 66), (25, 50)):
        ink.rectangle(((665 + dx) * SCALE, (225 - h) * SCALE, (665 + dx + 28) * SCALE, 225 * SCALE), outline=INK, width=2 * SCALE)
    # Pareto front
    ink.line(((876 * SCALE, 227 * SCALE), (876 * SCALE, 153 * SCALE), (977 * SCALE, 153 * SCALE)), fill=INK, width=2 * SCALE)
    for dx, dy in ((-28, 13), (-10, -8), (13, -18), (37, -34)):
        x, y = 925 + dx, 196 + dy
        ink.ellipse(((x - 5) * SCALE, (y - 5) * SCALE, (x + 5) * SCALE, (y + 5) * SCALE), fill=INK)
    # Preference ranks
    for i, dx in enumerate((-32, 0, 32), start=1):
        ink.ellipse(((1185 + dx - 15) * SCALE, 181 * SCALE, (1185 + dx + 15) * SCALE, 211 * SCALE), outline=INK, width=2 * SCALE)
        ink.text(((1185 + dx) * SCALE, 196 * SCALE), str(i), font=font(15, True), fill=INK, anchor="mm")
    # 3D blocks
    ink.polygon(((1400 * SCALE, 218 * SCALE), (1438 * SCALE, 200 * SCALE), (1474 * SCALE, 218 * SCALE), (1436 * SCALE, 238 * SCALE)), outline=INK)
    ink.line(((1400 * SCALE, 218 * SCALE), (1400 * SCALE, 179 * SCALE), (1438 * SCALE, 161 * SCALE), (1474 * SCALE, 179 * SCALE), (1474 * SCALE, 218 * SCALE)), fill=INK, width=2 * SCALE)
    ink.line(((1438 * SCALE, 161 * SCALE), (1438 * SCALE, 200 * SCALE)), fill=INK, width=2 * SCALE)
    save(image, "research_workflow.png", width, height)


if __name__ == "__main__":
    conceptual()
    workflow()
