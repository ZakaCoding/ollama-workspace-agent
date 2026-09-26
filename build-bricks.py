"""Regenerate the inline, accessible low-poly cube in index.html."""

from pathlib import Path


def point(x, y):
    return f"{x:.1f},{y:.1f}"


def polygon(points, face):
    coords = " ".join(point(*p) for p in points)
    return f'<polygon class="face-{face}" points="{coords}" />'


bricks = []
for z in range(3):
    for x in range(3):
        for y in range(3):
            bricks.append((x, y, z))

# Paint the farther blocks first. Each group is one small, shaded isometric brick.
bricks.sort(key=lambda cell: (cell[0] + cell[1] + cell[2], cell[2], cell[0]))
parts = [
    '<svg class="build-cube" viewBox="0 0 640 560" aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">',
    '  <ellipse class="cube-shadow" cx="320" cy="464" rx="180" ry="33" />',
]
for index, (x, y, z) in enumerate(bricks):
    cx = 320 + (x - y) * 50
    cy = 300 + (x + y) * 28 - z * 56
    top = (cx, cy - 27)
    right = (cx + 48, cy)
    front = (cx, cy + 27)
    left = (cx - 48, cy)
    left_bottom = (cx - 48, cy + 54)
    front_bottom = (cx, cy + 81)
    right_bottom = (cx + 48, cy + 54)
    tint = (x * 2 + y + z) % 4
    parts.append(f'  <g class="brick brick-{index:02d} tint-{tint}">')
    parts.append("    " + polygon((left, front, front_bottom, left_bottom), "left"))
    parts.append("    " + polygon((front, right, right_bottom, front_bottom), "right"))
    parts.append("    " + polygon((top, right, front, left), "top"))
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
