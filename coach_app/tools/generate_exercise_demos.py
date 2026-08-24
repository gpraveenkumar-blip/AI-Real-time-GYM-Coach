"""
Build-time script that generates a simple, original stick-figure "motion
guide" SVG for each Exercise Library entry — a start-position silhouette and
an end-position silhouette overlaid, with a motion arrow between them. These
are stylized illustrations (not photos/video), generated entirely from
vector math, so there are no licensing concerns.

Run this manually to regenerate the assets in static/exercise_demos/:
    python3 tools/generate_exercise_demos.py

Output is committed to the repo — the Streamlit app just displays the
resulting SVG files, it doesn't run this script at request time.
"""
import math
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "exercise_demos")

# Segment lengths (arbitrary vector units)
HEAD_R = 9
TORSO_LEN = 38
THIGH_LEN = 30
SHANK_LEN = 28
UPPER_ARM_LEN = 20
FOREARM_LEN = 18

START_COLOR = "#5B6472"    # muted outline — starting position
END_COLOR = "#FFB020"      # accent solid — end/working position
BG_COLOR = "#12161c"
LABEL_COLOR = "#E7ECF3"


def _dir_vec(angle_deg):
    """0deg = up, 90deg = right, 180deg = down, 270deg = left (screen coords, y grows down)."""
    rad = math.radians(angle_deg)
    return (math.sin(rad), -math.cos(rad))


def _add(p, v, scale=1.0):
    return (p[0] + v[0] * scale, p[1] + v[1] * scale)


def joint_positions(pose):
    """pose: dict with torso_dir, thigh_dir, shank_dir, upperarm_dir, forearm_dir (degrees).
    Returns a dict of (x, y) points, with hip fixed at the origin."""
    hip = (0.0, 0.0)
    shoulder = _add(hip, _dir_vec(pose["torso_dir"]), TORSO_LEN)
    head = _add(shoulder, _dir_vec(pose["torso_dir"]), HEAD_R + 4)
    knee = _add(hip, _dir_vec(pose["thigh_dir"]), THIGH_LEN)
    ankle = _add(knee, _dir_vec(pose["shank_dir"]), SHANK_LEN)
    elbow = _add(shoulder, _dir_vec(pose["upperarm_dir"]), UPPER_ARM_LEN)
    wrist = _add(elbow, _dir_vec(pose["forearm_dir"]), FOREARM_LEN)
    return {
        "hip": hip, "shoulder": shoulder, "head": head,
        "knee": knee, "ankle": ankle, "elbow": elbow, "wrist": wrist,
    }


def _bounding_box(*point_dicts):
    xs, ys = [], []
    for pts in point_dicts:
        for (x, y) in pts.values():
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _fit_transform(start_pts, end_pts, canvas_w=200, canvas_h=150, pad=28):
    min_x, min_y, max_x, max_y = _bounding_box(start_pts, end_pts)
    width = max(max_x - min_x, 1e-6)
    height = max(max_y - min_y, 1e-6)

    avail_w = canvas_w - 2 * pad
    avail_h = canvas_h - 2 * pad - 18  # leave room for the label at the bottom

    scale = min(avail_w / width, avail_h / height)

    def transform(p):
        x = (p[0] - min_x) * scale + pad + (avail_w - width * scale) / 2
        y = (p[1] - min_y) * scale + pad + (avail_h - height * scale) / 2
        return (round(x, 1), round(y, 1))

    return transform


def _figure_svg_group(pts, color, opacity, stroke_width=3.5, dash=False):
    dasharray = ' stroke-dasharray="4,3"' if dash else ""
    lines = [
        (pts["hip"], pts["shoulder"]),
        (pts["shoulder"], pts["elbow"]),
        (pts["elbow"], pts["wrist"]),
        (pts["hip"], pts["knee"]),
        (pts["knee"], pts["ankle"]),
    ]
    parts = [f'<g stroke="{color}" fill="none" stroke-width="{stroke_width}" '
             f'stroke-linecap="round" opacity="{opacity}"{dasharray}>']
    for (a, b) in lines:
        parts.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>')
    parts.append("</g>")
    head_x, head_y = pts["head"]
    parts.append(
        f'<circle cx="{head_x}" cy="{head_y}" r="{HEAD_R}" fill="{BG_COLOR}" '
        f'stroke="{color}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
    )
    return "\n".join(parts)


def _motion_arrow(start_pts, end_pts):
    """A small curved arrow from the wrist's start position to its end
    position, suggesting the direction of movement."""
    sx, sy = start_pts["wrist"]
    ex, ey = end_pts["wrist"]
    if (abs(sx - ex) + abs(sy - ey)) < 6:
        # Wrist barely moves for this exercise (e.g. a hold) — use the knee instead.
        sx, sy = start_pts["knee"]
        ex, ey = end_pts["knee"]

    mx, my = (sx + ex) / 2, (sy + ey) / 2 - 10
    return (
        f'<path d="M {sx} {sy} Q {mx} {my} {ex} {ey}" stroke="#7DD3FC" '
        f'stroke-width="2" fill="none" stroke-dasharray="3,3" marker-end="url(#arrowhead)"/>'
    )


def render_svg(exercise_name, start_pose, end_pose, cue_text=""):
    start_pts_raw = joint_positions(start_pose)
    end_pts_raw = joint_positions(end_pose)
    transform = _fit_transform(start_pts_raw, end_pts_raw)

    start_pts = {k: transform(v) for k, v in start_pts_raw.items()}
    end_pts = {k: transform(v) for k, v in end_pts_raw.items()}

    is_hold_exercise = start_pose == end_pose
    label = exercise_name

    if is_hold_exercise:
        motion_element = (
            '<circle cx="172" cy="22" r="14" fill="none" stroke="#7DD3FC" stroke-width="2"/>'
            '<text x="172" y="26" text-anchor="middle" font-family="Arial, sans-serif" '
            'font-size="9" font-weight="700" fill="#7DD3FC">HOLD</text>'
        )
        figures = _figure_svg_group(end_pts, END_COLOR, 0.95)
    else:
        motion_element = _motion_arrow(start_pts, end_pts)
        figures = (
            _figure_svg_group(start_pts, START_COLOR, 0.65, dash=True)
            + "\n" + _figure_svg_group(end_pts, END_COLOR, 0.95)
        )

    svg = f'''<svg viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label} demo">
  <defs>
    <marker id="arrowhead" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#7DD3FC"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="200" height="150" rx="6" fill="{BG_COLOR}"/>
  {figures}
  {motion_element}
  <text x="100" y="138" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="{LABEL_COLOR}">{label}</text>
</svg>'''
    return svg


# ---------------------------------------------------------------------------
# Pose parameters per exercise: (start, end) keyframes.
# Angles are degrees from vertical-up, clockwise: 0=up, 90=right, 180=down, 270=left.
# These are stylized, illustrative approximations — not biomechanical ground truth.
# ---------------------------------------------------------------------------
EXERCISE_POSES = {
    # ---- Chest ----
    "Standard Push-Ups": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 75, "forearm_dir": 100},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 80, "forearm_dir": 170},
    ),
    "Wide Push-Ups": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 65, "forearm_dir": 95},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 70, "forearm_dir": 165},
    ),
    "Incline Push-Ups": (
        {"torso_dir": 70, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 75, "forearm_dir": 100},
        {"torso_dir": 70, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 80, "forearm_dir": 165},
    ),
    "Decline Push-Ups": (
        {"torso_dir": 110, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 75, "forearm_dir": 100},
        {"torso_dir": 110, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 80, "forearm_dir": 170},
    ),

    # ---- Back ----
    "Superman": (
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 100, "forearm_dir": 100},
        {"torso_dir": 70, "thigh_dir": 70, "shank_dir": 90, "upperarm_dir": 80, "forearm_dir": 80},
    ),
    "Reverse Snow Angels": (
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 160, "forearm_dir": 160},
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 30, "forearm_dir": 30},
    ),
    "Prone Y-T-W Raises": (
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 105, "forearm_dir": 105},
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 50, "forearm_dir": 50},
    ),
    "Backpack Rows": (
        {"torso_dir": 60, "thigh_dir": 175, "shank_dir": 15, "upperarm_dir": 75, "forearm_dir": 75},
        {"torso_dir": 60, "thigh_dir": 175, "shank_dir": 15, "upperarm_dir": 60, "forearm_dir": 300},
    ),

    # ---- Shoulders ----
    "Pike Push-Ups": (
        {"torso_dir": 130, "thigh_dir": 190, "shank_dir": 95, "upperarm_dir": 80, "forearm_dir": 100},
        {"torso_dir": 130, "thigh_dir": 190, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 165},
    ),
    "Shoulder Taps": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 80, "forearm_dir": 170},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 350, "forearm_dir": 350},
    ),
    "Wall Handstand Hold": (
        {"torso_dir": 0, "thigh_dir": 350, "shank_dir": 350, "upperarm_dir": 175, "forearm_dir": 175},
        {"torso_dir": 0, "thigh_dir": 350, "shank_dir": 350, "upperarm_dir": 175, "forearm_dir": 175},
    ),
    "Arm Circles": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 260, "forearm_dir": 260},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 100, "forearm_dir": 100},
    ),

    # ---- Biceps ----
    "Backpack Curls": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 180, "forearm_dir": 180},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 175, "forearm_dir": 20},
    ),
    "Towel Curls": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 180, "forearm_dir": 180},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 175, "forearm_dir": 20},
    ),
    "Isometric Biceps Hold": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 178, "forearm_dir": 90},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 178, "forearm_dir": 90},
    ),
    "Resistance-Band Curls": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 180, "forearm_dir": 180},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 175, "forearm_dir": 20},
    ),

    # ---- Triceps ----
    "Diamond Push-Ups": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 100},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 88, "forearm_dir": 175},
    ),
    "Chair Dips": (
        {"torso_dir": 5, "thigh_dir": 175, "shank_dir": 15, "upperarm_dir": 190, "forearm_dir": 190},
        {"torso_dir": 15, "thigh_dir": 175, "shank_dir": 15, "upperarm_dir": 195, "forearm_dir": 250},
    ),
    "Close-Grip Push-Ups": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 100},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 88, "forearm_dir": 175},
    ),
    "Overhead Backpack Extension": (
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 175, "forearm_dir": 175},
        {"torso_dir": 0, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 175, "forearm_dir": 35},
    ),

    # ---- Abs / Core ----
    "Plank": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 175},
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 175},
    ),
    "Bicycle Crunches": (
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 130, "forearm_dir": 130},
        {"torso_dir": 60, "thigh_dir": 220, "shank_dir": 240, "upperarm_dir": 220, "forearm_dir": 220},
    ),
    "Leg Raises": (
        {"torso_dir": 90, "thigh_dir": 90, "shank_dir": 90, "upperarm_dir": 90, "forearm_dir": 90},
        {"torso_dir": 90, "thigh_dir": 355, "shank_dir": 5, "upperarm_dir": 90, "forearm_dir": 90},
    ),
    "Mountain Climbers": (
        {"torso_dir": 95, "thigh_dir": 95, "shank_dir": 95, "upperarm_dir": 85, "forearm_dir": 175},
        {"torso_dir": 95, "thigh_dir": 200, "shank_dir": 260, "upperarm_dir": 85, "forearm_dir": 175},
    ),

    # ---- Legs ----
    "Bodyweight Squats": (
        {"torso_dir": 10, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 60, "forearm_dir": 60},
        {"torso_dir": 30, "thigh_dir": 100, "shank_dir": 330, "upperarm_dir": 90, "forearm_dir": 90},
    ),
    "Reverse Lunges": (
        {"torso_dir": 10, "thigh_dir": 0, "shank_dir": 0, "upperarm_dir": 20, "forearm_dir": 20},
        {"torso_dir": 10, "thigh_dir": 60, "shank_dir": 350, "upperarm_dir": 20, "forearm_dir": 20},
    ),
    "Bulgarian Split Squats": (
        {"torso_dir": 10, "thigh_dir": 340, "shank_dir": 20, "upperarm_dir": 20, "forearm_dir": 20},
        {"torso_dir": 20, "thigh_dir": 80, "shank_dir": 330, "upperarm_dir": 20, "forearm_dir": 20},
    ),
    "Glute Bridges": (
        {"torso_dir": 100, "thigh_dir": 160, "shank_dir": 70, "upperarm_dir": 90, "forearm_dir": 90},
        {"torso_dir": 60, "thigh_dir": 130, "shank_dir": 70, "upperarm_dir": 90, "forearm_dir": 90},
    ),
}


def _slugify(name):
    return name.lower().replace(" ", "_").replace("/", "").replace("-", "_").replace("__", "_")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    written = []

    for exercise_name, (start_pose, end_pose) in EXERCISE_POSES.items():
        svg = render_svg(exercise_name, start_pose, end_pose)
        filename = f"{_slugify(exercise_name)}.svg"
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w") as f:
            f.write(svg)
        written.append(filename)

    print(f"Wrote {len(written)} demo SVGs to {os.path.abspath(OUTPUT_DIR)}")
    return written


if __name__ == "__main__":
    main()
