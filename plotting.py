import json
import matplotlib.pyplot as plt

# Using the log file for Diplay
# Change the log file to make the desired plit
FILE_NAME = "CIRCLE_TEST.json"

cycles = []
dx_vals = []
dy_vals = []
conf_vals = []

# 1. Read and parse the JSON Lines file
try:
    with open(FILE_NAME, 'r') as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                cycles.append(data['c'])
                dx_vals.append(data['dx'])
                dy_vals.append(data['dy'])
                conf_vals.append(data['conf'])
except FileNotFoundError:
    print(f"Error: {FILE_NAME} not found. Make sure to copy it from the OpenMV Cam.")
    exit()

# 2. Create the plots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# Displacement Plot (DX and DY)
ax1.plot(cycles, dx_vals, label='DX (mm)', color='blue', linewidth=1.5)
ax1.plot(cycles, dy_vals, label='DY (mm)', color='red', linewidth=1.5)
ax1.axhline(0, color='black', linestyle='--', alpha=0.5) # Zero reference line
ax1.set_ylabel("Displacement (mm)")
ax1.set_title("Object Displacement from Golden Reference")
ax1.legend()
ax1.grid(True, alpha=0.3)

# Confidence Plot
ax2.fill_between(cycles, conf_vals, color='green', alpha=0.3)
ax2.plot(cycles, conf_vals, color='green', label='Confidence')
ax2.set_ylabel("Confidence (0.0 - 1.0)")
ax2.set_xlabel("Cycle Number")
ax2.set_ylim(0, 1.1)
ax2.set_title("Detection Confidence (Samples Found / Total Samples)")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
