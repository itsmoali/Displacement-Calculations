import sensor, image, time, json, math, pyb

# ------------
# CONFIGURATION
# ------------
MM_PER_PIXEL = 0.06
JSON_FILE = "CIRCLE_TEST_PRO.json"

# Number of total runs
TOTAL_CYCLES = 1000
# Samples per run
SAMPLES_PER_CYCLE = 5

# Circle detection parameters (Change based on the marker being used)
R_MIN = 20
R_MAX = 100
MAG_THRESHOLD = 2000
ROI_PADDING = 40  # pixels

REFERENCE_SAMPLES = 20  # stable golden reference
PIXEL_EPS = 1e-6

# ------------
# SENSOR SETUP 
# ------------
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.VGA)
sensor.skip_frames(time=2000)

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)
# ------------
# GPIO: Using Pin 0 (P0) as a Trigger Input
# Robot will set this pin HIGH when it arrives at each measurement point
trigger_pin = pyb.Pin("P0", pyb.Pin.IN, pyb.Pin.PULL_DOWN)
# ------------
# GLOBAL STATE
# ------------
ref_cx = 0.0
ref_cy = 0.0

search_roi = (0, 0, sensor.width(), sensor.height())

# ------------
# UTILITIES
# ------------
def clamp_roi(x, y, w, h):
    x = max(0, x)
    y = max(0, y)
    w = min(w, sensor.width() - x)
    h = min(h, sensor.height() - y)
    return (x, y, w, h)

# ------------
# TWO-STAGE CIRCLE DETECTOR
# ------------
def find_target_circle(img):
    global search_roi

    # Work on a copy to avoid cumulative blur
    work = img.copy()
    work.gaussian(1)

    circles = work.find_circles(
        threshold=MAG_THRESHOLD,
        roi=search_roi,
        x_stride=2,
        y_stride=2,
        r_min=R_MIN,
        r_max=R_MAX
    )

    if not circles:
        search_roi = (0, 0, sensor.width(), sensor.height())
        return None

    # Strongest + most circular (magnitude normalized by radius)
    best = max(circles, key=lambda c: c.magnitude() / (c.r() + PIXEL_EPS))

    # Update ROI deterministically
    size = (best.r() + ROI_PADDING) * 2
    new_x = int(best.x() - size // 2)
    new_y = int(best.y() - size // 2)

    search_roi = clamp_roi(new_x, new_y, int(size), int(size))

    return best

# ------------
# GOLDEN REFERENCE 
# ------------
def capture_golden_reference():
    global ref_cx, ref_cy

    print("Locking golden reference... hold steady")

    xs, ys = [], []

    while len(xs) < REFERENCE_SAMPLES:
        img = sensor.snapshot()
        target = find_target_circle(img)

        if target:
            xs.append(target.x())
            ys.append(target.y())

            img.draw_circle(target.x(), target.y(), target.r(), color=255)
            img.draw_cross(target.x(), target.y(), color=255)
        else:
            xs.clear()
            ys.clear()

        time.sleep_ms(50)

    ref_cx = sum(xs) / len(xs)
    ref_cy = sum(ys) / len(ys)

    print("Reference locked at X=%.3f Y=%.3f" % (ref_cx, ref_cy))

# ------------
# LOGGING (HIGH PRECISION)
# ------------
def log_iteration(cycle, dx, dy, sigma, conf):
    entry = {
        "cycle": cycle,
        "dx_mm": round(dx, 4),
        "dy_mm": round(dy, 4),
        "sigma_mm": round(sigma, 5),
        "confidence": conf
    }
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

# ------------
# MAIN
# ------------
capture_golden_reference()

with open(JSON_FILE, "w") as f:
    f.write("")

for cycle in range(TOTAL_CYCLES):
    # Wait for robot trigger
    #wait_for_trigger() # Uncomment for hardware trigger
    time.sleep(2)        # Manual delay for testing

    print("\n Taking Burst Images...")

    dxs = []
    dys = []

    print("Cycle", cycle)

    for _ in range(SAMPLES_PER_CYCLE):
        img = sensor.snapshot()
        target = find_target_circle(img)

        if target:
            dxs.append((target.x() - ref_cx) * MM_PER_PIXEL)
            dys.append((target.y() - ref_cy) * MM_PER_PIXEL)

            img.draw_rectangle(search_roi, color=125)
            img.draw_cross(target.x(), target.y(), color=255)

    if dxs:
        mean_dx = sum(dxs) / len(dxs)
        mean_dy = sum(dys) / len(dys)

        # Combined positional sigma
        var = sum((dx - mean_dx) ** 2 + (dy - mean_dy) ** 2
                  for dx, dy in zip(dxs, dys)) / max(1, len(dxs) - 1)

        sigma = math.sqrt(var)

        conf = len(dxs) / SAMPLES_PER_CYCLE

        log_iteration(cycle, mean_dx, mean_dy, sigma, conf)

        print(" -> Δx=%.4fmm Δy=%.4fmm σ=%.5fmm conf=%.2f"
              % (mean_dx, mean_dy, sigma, conf))
    else:
        print(" -> FAILED (marker lost)")
