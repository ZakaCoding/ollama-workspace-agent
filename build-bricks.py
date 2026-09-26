"""Regenerate the inline, accessible low-poly cube in index.html."""

from pathlib import Path


def point(x, y):
    return f"{x:.1f},{y:.1f}"


def coordinates(points):
    return " ".join(point(*p) for p in points)


def polygon(points, face):
    return f'<polygon class="face-{face}" points="{coordinates(points)}" />'


def corners(x, y, z):
    cx = 320 + (x - y) * 50
    cy = 300 + (x + y) * 28 - z * 56
    return {
        "top": (cx, cy - 27),
        "right": (cx + 48, cy),
        "front": (cx, cy + 27),
        "left": (cx - 48, cy),
        "left_bottom": (cx - 48, cy + 54),
        "front_bottom": (cx, cy + 81),
        "right_bottom": (cx + 48, cy + 54),
    }


bricks = []
for z in range(3):
    for x in range(3):
        for y in range(3):
            bricks.append((x, y, z))

# Paint the farther blocks first. Each group is one small, shaded isometric brick.
bricks.sort(key=lambda cell: (cell[0] + cell[1] + cell[2], cell[2], cell[0]))
parts = [
    '<svg class="build-cube" viewBox="0 0 640 560" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">',
    "  <defs>",
]
for y in range(3):
    for z in range(3):
        c = corners(2, y, z)
        face = (c["front"], c["right"], c["right_bottom"], c["front_bottom"])
        parts.append(f'    <clipPath id="mascot-piece-{y}-{z}" clipPathUnits="userSpaceOnUse"><polygon points="{coordinates(face)}" /></clipPath>')
parts.extend([
    "  </defs>",
    '  <ellipse class="cube-shadow" cx="320" cy="464" rx="180" ry="33" />',
])
for index, (x, y, z) in enumerate(bricks):
    c = corners(x, y, z)
    right_face = (c["front"], c["right"], c["right_bottom"], c["front_bottom"])
    tint = (x * 2 + y + z) % 4
    logo_class = " logo-brick" if x == 2 else ""
    parts.append(f'  <g class="brick brick-{index:02d} tint-{tint}{logo_class}">')
    parts.append("    " + polygon((c["left"], c["front"], c["front_bottom"], c["left_bottom"]), "left"))
    parts.append("    " + polygon(right_face, "right"))
    if x == 2:
        # The same image is projected onto the full side. Each brick clips out
        # its own fragment, so the mascot appears piece by piece as they land.
        parts.append(f'    <g clip-path="url(#mascot-piece-{y}-{z})">')
        parts.append('      <image class="brick-mascot-piece" href="assets/owa-mascot.png" x="-1.9" y="-1.0" width="6.9" height="5.0" preserveAspectRatio="none" transform="matrix(50 -28 0 56 320 327)" />')
        parts.append("    </g>")
        parts.append(f'    <polygon class="logo-face-outline" points="{coordinates(right_face)}" />')
    parts.append("    " + polygon((c["top"], c["right"], c["front"], c["left"]), "top"))
    parts.append("  </g>")
parts.append("</svg>")

page = Path(__file__).with_name("index.html")
content = page.read_text()
start = "<!-- BUILD_ART_START -->"
end = "<!-- BUILD_ART_END -->"
if content.count(start) != 1 or content.count(end) != 1:
    raise SystemExit("Could not find unique cube markers")
before, remainder = content.split(start, 1)
_, after = remainder.split(end, 1)
page.write_text(before + start + "\n          " + "\n          ".join(parts) + "\n          " + end + after)
