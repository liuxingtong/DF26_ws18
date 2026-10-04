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
    width, height = 1600, 510
    image, ink = canvas(width, height, "Research Workflow")
    top = [
        (45, "Frozen inputs", ("Data and provenance",)),
        (360, "Scenario rules", ("Access and intensity",)),
        (675, "Form operations", ("Candidate geometry",)),
        (990, "Hard constraints", ("Repair or reject",)),
        (1305, "Three objectives", ("Evaluate feasible form",)),
    ]
    for x, heading, lines in top:
        box(ink, x, 120, 250, 115, heading, lines)
    for x in (295, 610, 925, 1240):
        arrow(ink, x + 5, 178, x + 60, 178)
    bottom = [
        (205, "NSGA-II", ("Independent evaluations",)),
        (595, "Pareto set", ("Exact and epsilon fronts",)),
        (985, "Role ranking", ("Priority tiers",)),
        (1375, "3D review", ("Trace each change",)),
    ]
    for x, heading, lines in bottom:
        box(ink, x, 323, 225, 115, heading, lines)
    for x in (430, 820, 1210):
        arrow(ink, x + 10, 380, x + 155, 380)
    ink.line(((1430 * SCALE, 235 * SCALE), (1430 * SCALE, 295 * SCALE), (317 * SCALE, 295 * SCALE), (317 * SCALE, 323 * SCALE)), fill=LINE, width=2 * SCALE)
    save(image, "research_workflow.png", width, height)


if __name__ == "__main__":
    conceptual()
    workflow()
