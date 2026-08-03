import csv
import os
from io import StringIO
from datetime import datetime

import qrcode
from PIL import Image

from config import BASE_DIR


def calculate_duration(start_time, end_time=None):
    if not start_time:
        return "0 min"
    if end_time is None:
        end_time = datetime.now()
    if isinstance(start_time, str):
        start_time = datetime.fromisoformat(start_time)
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    delta = end_time - start_time
    minutes = int(delta.total_seconds() // 60)
    hours, remainder = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remainder}m"
    return f"{minutes}m"


def format_datetime(value):
    if not value:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime("%Y-%m-%d %H:%M")


def generate_qr_code(slot_id):
    folder = os.path.join(BASE_DIR, "static", "images", "qr")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"slot_{slot_id}.png")
    if os.path.exists(path):
        return f"/static/images/qr/slot_{slot_id}.png"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"http://127.0.0.1:5000/parking/{slot_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(path)
    return f"/static/images/qr/slot_{slot_id}.png"


def export_history_to_csv(history_rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["User", "Vehicle", "Slot", "Entry Time", "Exit Time", "Duration"])
    for row in history_rows:
        writer.writerow([
            row["full_name"],
            row["vehicle_number"],
            row["slot_number"],
            row.get("entry_time") or "—",
            row.get("exit_time") or "—",
            row.get("duration") or "—",
        ])
    output.seek(0)
    return output
