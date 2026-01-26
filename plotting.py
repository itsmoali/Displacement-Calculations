import json
import math
import matplotlib.pyplot as plt

# -------------------------------------------------
# CONFIG
# -------------------------------------------------
FILE_NAME = "CIRCLE_TEST.json"
PRECISION_BAND_MM = 0.01

# -------------------------------------------------
# DATA CONTAINERS
# -------------------------------------------------
cycles = []
dx_vals = []
dy_vals = []
radial_vals = []
conf_vals = []

# -------------------------------------------------
# LOAD JSONL LOG
# -------------------------------------------------
try:
    with open(FILE_NAME, "r") as f:
        for line in f:
            if not line.strip():
                continue

            d = json.loads(line)

            c = d.get("c")
            dx = d.get("dx")
            dy = d.get("dy")
            conf = d.get("conf", 1.0)

            if c is None or dx is None or dy is None:
                continue

            cycles.append(c)
            dx_vals.append(dx)
            dy_vals.append(dy)
            radial_vals.append(math.sqrt(dx*dx + dy*dy))
            conf_vals.append(conf)

except FileNotFoundError:
    print(f"ERROR: {FILE_NAME} not found.")
    raise SystemExit

# -------------------------------------------------
# PLOTTING
# -------------------------------------------------
fig, axes = plt.subplots(
    3, 1,
    figsize=(12, 10),
    sharex=True,
    gridspec_kw={"height_ratios": [2, 2, 1]}
)

ax_xy, ax_radial, ax_conf = axes

# -------------------------------------------------
# DX / DY TIME SERIES
# -------------------------------------------------
ax_xy.plot(cycles, dx_vals, label="DX (mm)", linewidth=1.4)
ax_xy.plot(cycles, dy_vals, label="DY (mm)", linewidth=1.4)

ax_xy.axhline(0, linestyle="--", linewidth=1, alpha=0.6)

# Precision bands
ax_xy.axhline(+PRECISION_BAND_MM, color="red", linestyle=":", alpha=0.7)
ax_xy.axhline(-PRECISION_BAND_MM, color="red", linestyle=":", alpha=0.7)

ax_xy.set_ylabel("Displacement (mm)")
ax_xy.set_title("Cartesian Displacement vs Time")
ax_xy.legend()
ax_xy.grid(alpha=0.3)

# -------------------------------------------------
# RADIAL ERROR (TRUE POSITION ERROR)
# -------------------------------------------------
ax_radial.plot(cycles, radial_vals, color="purple", linewidth=1.6)
ax_radial.axhline(PRECISION_BAND_MM, color="red", linestyle="--", alpha=0.8)

ax_radial.set_ylabel("Radial Error (mm)")
ax_radial.set_title("Total Position Error |√(dx² + dy²)|")
ax_radial.grid(alpha=0.3)

# -------------------------------------------------
# CONFIDENCE TRACKING
# -------------------------------------------------
ax_conf.fill_between(cycles, conf_vals, alpha=0.3)
ax_conf.plot(cycles, conf_vals, linewidth=1.2)

ax_conf.set_ylabel("Confidence")
ax_conf.set_xlabel("Cycle")
ax_conf.set_ylim(0, 1.05)
ax_conf.grid(alpha=0.3)

# -------------------------------------------------
# FINAL LAYOUT
# -------------------------------------------------
plt.tight_layout()
plt.show()
