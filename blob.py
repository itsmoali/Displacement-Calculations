import sensor, image, time, json, pyb, math

# ------------
# CONFIG (Change as needed)
# ------------
MM_PER_PIXEL = 0.06
JSON_FILE = "BLOB_TEST.json"

# Total number of runs
TOTAL_CYCLES = 1000
# Number of samples per run
SAMPLES_PER_CYCLE = 7

# Threshold values (change based on the color and size of the target blob)
THRESHOLD = (150, 255)
PIXELS_THRESHOLD = 300
AREA_THRESHOLD = 300

TARGET_PRECISION_MM = 0.01

# ------------
# Sensor Setup 
# ------------
sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)
sensor.set_framesize(sensor.QVGA)

sensor.set_auto_gain(False)
sensor.set_auto_exposure(False)
sensor.set_auto_whitebal(False)

sensor.skip_frames(time=3000)

# ------------
# Globals
# ------------
ref_cx = 0.0
ref_cy = 0.0

burst_buffers = [
    sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE)
    for _ in range(SAMPLES_PER_CYCLE)
]

# ------------
# Blob + Subpixel Centroid
# ------------
def find_target_blob(img):
    blobs = img.find_blobs(
        [THRESHOLD],
        pixels_threshold=PIXELS_THRESHOLD,
        area_threshold=AREA_THRESHOLD,
        merge=True
    )
    if not blobs:
        return None
    return max(blobs, key=lambda b: b.pixels())

def refined_centroid(blob):
    # second moment refinement (subpixel)
    cx = blob.cx()
    cy = blob.cy()

    if blob.m00() > 0:
        cx += blob.m10() / blob.m00() - cx
        cy += blob.m01() / blob.m00() - cy

    return cx, cy

# ------------
# Reference Capture
# ------------
def capture_golden_reference():
    global ref_cx, ref_cy

    print("\n[REF] Capturing golden reference...")
    img = sensor.snapshot()
    blob = find_target_blob(img)

    if not blob:
        raise RuntimeError("Reference blob not found")

    ref_cx, ref_cy = refined_centroid(blob)

    print("[REF] Locked @ %.4f, %.4f px" % (ref_cx, ref_cy))

# ------------
# Statistics
# ------------
def mean(vals):
    return sum(vals) / len(vals)

def variance(vals, mu):
    return sum((v - mu) ** 2 for v in vals) / len(vals)

def trimmed_mean(vals, trim=1):
    vals = sorted(vals)
    return mean(vals[trim:-trim])

# ------------
# Logging
# ------------
def log(entry):
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

# ------------
# MAIN
# ------------
capture_golden_reference()

with open(JSON_FILE, "w") as f:
    f.write("")

print("\n[INFO] Starting precision monitoring...\n")

for cycle in range(TOTAL_CYCLES):

    time.sleep(2)  # deterministic pause

    # Capture burst
    for buf in burst_buffers:
        buf.replace(sensor.snapshot())

    dxs = []
    dys = []

    for buf in burst_buffers:
        blob = find_target_blob(buf)
        if blob:
            cx, cy = refined_centroid(blob)
            dxs.append(cx - ref_cx)
            dys.append(cy - ref_cy)

    if len(dxs) < 3:
        log({"cycle": cycle, "status": "fail"})
        print("[CYCLE %d] ❌ insufficient samples" % cycle)
        continue

    # Robust statistics
    dx_px = trimmed_mean(dxs)
    dy_px = trimmed_mean(dys)

    var_dx = variance(dxs, dx_px)
    var_dy = variance(dys, dy_px)

    dx_mm = dx_px * MM_PER_PIXEL
    dy_mm = dy_px * MM_PER_PIXEL

    error_mm = math.sqrt(dx_mm**2 + dy_mm**2)
    sigma_mm = math.sqrt(var_dx + var_dy) * MM_PER_PIXEL

    precision_ok = error_mm <= TARGET_PRECISION_MM

    entry = {
        "cycle": cycle,
        "dx_mm": round(dx_mm, 5),
        "dy_mm": round(dy_mm, 5),
        "error_mm": round(error_mm, 5),
        "sigma_mm": round(sigma_mm, 5),
        "samples": len(dxs),
        "precision_ok": precision_ok,
        "timestamp_ms": pyb.millis()
    }

    log(entry)

    print(
        "[%04d] dx=%.5f dy=%.5f err=%.5f σ=%.5f %s"
        % (
            cycle,
            dx_mm,
            dy_mm,
            error_mm,
            sigma_mm,
            "Precise" if precision_ok else "Not Precise"
        )
    )

print("\n[INFO] Monitoring complete.")
