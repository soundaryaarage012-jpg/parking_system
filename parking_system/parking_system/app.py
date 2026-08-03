import importlib
import os
import sys

PROJECT_ROOT = os.path.dirname(__file__)
PARKING_APP_DIR = os.path.join(PROJECT_ROOT, "ParkingTracker")

if PARKING_APP_DIR not in sys.path:
    sys.path.insert(0, PARKING_APP_DIR)

parking_app_module = importlib.import_module("ParkingTracker.app")
app = parking_app_module.app


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
