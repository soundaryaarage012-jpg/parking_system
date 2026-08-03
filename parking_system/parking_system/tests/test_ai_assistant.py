import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ParkingTracker.services import build_ai_assistant_response


def test_ai_assistant_fallback_mentions_recommended_slot():
    slots = [
        {
            "slot_number": "P01",
            "status": "available",
            "priority": 3,
            "distance_from_entrance": 40,
            "ev_charging": 1,
            "vehicle_size": "Sedan",
        },
        {
            "slot_number": "P02",
            "status": "occupied",
            "priority": 1,
            "distance_from_entrance": 70,
            "ev_charging": 0,
            "vehicle_size": "Sedan",
        },
    ]

    result = build_ai_assistant_response("Sedan", False, slots)

    assert result["mode"] == "fallback"
    assert "P01" in result["message"]
    assert "Sedan" in result["message"]


def test_ai_assistant_accepts_sqlite_rows():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT 'P05' AS slot_number, 'available' AS status, 2 AS priority, 45 AS distance_from_entrance, 1 AS ev_charging, 'Sedan' AS vehicle_size, 'Ground Floor' AS floor"
    )
    row = cursor.fetchone()
    conn.close()

    result = build_ai_assistant_response("Sedan", False, [row])

    assert result["mode"] == "fallback"
    assert "P05" in result["message"]
