import sensor, image, time, json, pyb, math

# ------------
# CONFIG
# ------------
MM_PER_PIXEL = 0.06
JSON_FILE = "FFT_TEST.json"

# Total runs
TOTAL_CYCLES = 1000
# Samples per run
SAMPLES_PER_CYCLE = 7 

# Threshold value (Change depending on the color of the object)
THRESHOLD = (150, 255)
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
# Trigger Pin (optional)
# ------------
trigger_pin = pyb.Pin("P0", pyb.Pin.IN, pyb.Pin.PULL_DOWN)

# ------------
# Buffers
# ------------
ref_buffer = sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE)
burst_buffers = [
    sensor.alloc_extra_fb(sensor.width(), sensor.height(), sensor.GRAYSCALE)
    for _ in range(SAMPLES_PER_CYCLE)
]

# ------------
# Logging Helpers
# ------------
def log(entry):
    with open(JSON_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

# ------------
# Capture Reference
# ------------
def capture_golden_reference():
    print("[REF] Capturing Golden Reference...")
    img = sensor.snapshot()
    img.find_edges(image.EDGE_CANNY, threshold=THRESHOLD)
    ref_buffer.replace(img)
    print("[REF] Reference locked.")

# ------------
# Wait for trigger
# ------------
def wait_for_trigger():
    print("[INFO] Waiting for robot signal...")
    while not trigger_pin.value():
        time.sleep_ms(5)
    time.sleep_ms(50)
    print("[INFO] Signal received.")

# ------------
# Statistics helpers
# ------------
def mean(vals):
    return sum(vals) / len(vals)

def variance(vals, mu):
    return sum((v - mu) ** 2 for v in vals) / len(vals)

def trimmed_mean(vals, trim=1):
    vals = sorted(vals)
    return mean(vals[trim:-trim])

# ------------
# MAIN
# ------------
capture_golden_reference()

# Reset log
with open(JSON_FILE, "w") as f:
    f.write("")

print("[INFO] Starting high-precision displacement monitoring...\n")

for cycle in range(TOTAL_CYCLES):

    # wait_for_trigger()  # enable in production
    time.sleep(2)  # deterministic pause

    # Capture burst
    for buf in burst_buffers:
        buf.replace(sensor.snapshot())

    dxs = []
    dys = []
    responses = []

    for buf in burst_buffers:
        buf.find_edges(image.EDGE_CANNY, threshold=THRESHOLD)
        res = buf.find_displacement(ref_buffer, logpolar=False)
        if res:
            dxs.append(res.x_translation())
            dys.append(res.y_translation())
            responses.append(res.response())

    if len(dxs) < 3:
        log({"cycle": cycle, "status": "fail"})
        print(f"[CYCLE {cycle}] ❌ insufficient displacement samples")
        continue

    # Robust statistics
    dx_px = trimmed_mean(dxs)
    dy_px = trimmed_mean(dys)

    var_dx = variance(dxs, dx_px)
    var_dy = variance(dys, dy_px)

    dx_mm = -dx_px * MM_PER_PIXEL
    dy_mm = -dy_px * MM_PER_PIXEL

    error_mm = math.sqrt(dx_mm**2 + dy_mm**2)
    sigma_mm = math.sqrt(var_dx + var_dy) * MM_PER_PIXEL

    conf = trimmed_mean(responses)

    precision_ok = error_mm <= TARGET_PRECISION_MM

    entry = {
        "cycle": cycle,
        "dx_mm": round(dx_mm, 5),
        "dy_mm": round(dy_mm, 5),
        "error_mm": round(error_mm, 5),
        "sigma_mm": round(sigma_mm, 5),
        "confidence": round(conf, 5),
        "samples": len(dxs),
        "precision_ok": precision_ok,
        "timestamp_ms": pyb.millis()
    }

    log(entry)

    print(
        f"[{cycle:04d}] dx={dx_mm:.5f} dy={dy_mm:.5f} err={error_mm:.5f} "
        f"σ={sigma_mm:.5f} conf={conf:.4f} {'✅' if precision_ok else '⚠️'}"
    )

print("\n[INFO] Displacement monitoring complete.")
