import json
import os
from collections import Counter
from datetime import datetime
from typing import Dict, List

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

try:
    from .models import get_db
except ImportError:  # pragma: no cover - fallback for direct execution
    from models import get_db


def _slot_value(slot, key, default=None):
    if isinstance(slot, dict):
        return slot.get(key, default)
    if hasattr(slot, "get"):
        return slot.get(key, default)
    if hasattr(slot, "__getitem__"):
        try:
            return slot[key]
        except (KeyError, IndexError, TypeError):
            return default
    if hasattr(slot, key):
        return getattr(slot, key)
    return default


def _intent_keywords(intent):
    text = (intent or "").lower()
    if "ev" in text:
        return "ev"
    if "wheel" in text or "access" in text:
        return "wheelchair"
    if "quick" in text or "stop" in text:
        return "quick_stop"
    if "bike" in text:
        return "bike"
    if "suv" in text:
        return "suv"
    return "nearest"


def build_ai_recommendation_payload(intent="Nearest parking", vehicle_type="Sedan", requires_ev=False, slots=None):
    slots = slots or []
    available_slots = [slot for slot in slots if _slot_value(slot, "status") == "available"]
    if not available_slots:
        return {
            "intent": intent,
            "mode": "fallback",
            "message": "No available parking slots are currently open. Please try again shortly.",
            "recommended_slot": None,
            "parking_score": 0,
            "confidence": 0,
            "traffic": 0,
            "accessibility": {},
            "reasons": ["No available options right now."],
            "alternatives": [],
        }

    intent_type = _intent_keywords(intent)
    scored = []
    for slot in available_slots:
        distance = float(_slot_value(slot, "distance_from_entrance", 60))
        ev_ready = bool(_slot_value(slot, "ev_charging", 0))
        priority = float(_slot_value(slot, "priority", 1))
        vehicle_size = str(_slot_value(slot, "vehicle_size", vehicle_type or "Sedan")).lower()
        slot_type_match = 1.0 if vehicle_size == str(vehicle_type or "Sedan").lower() else 0.7
        if intent_type == "ev":
            slot_type_match = 1.0 if ev_ready else 0.3
        elif intent_type == "wheelchair":
            slot_type_match = 1.0 if priority >= 3 else 0.7
        elif intent_type == "bike":
            slot_type_match = 1.0 if "bike" in str(slot).lower() or vehicle_size == "bike" else 0.5
        elif intent_type == "suv":
            slot_type_match = 1.0 if vehicle_size in {"suv", "truck", "van"} else 0.6

        traffic_pressure = min(100, max(15, int((distance / 2.5) + (priority * 8))))
        distance_component = max(0, 100 - distance)
        accessibility = {
            "ev_ready": ev_ready,
            "wheelchair": priority >= 3,
            "step_free": priority >= 2,
            "bike_friendly": vehicle_size in {"bike", "scooter"},
        }
        score = (
            distance_component * 0.34
            + (100 - traffic_pressure) * 0.24
            + slot_type_match * 100 * 0.28
            + (60 + priority * 10) * 0.14
        )
        score = max(0, min(100, round(score)))
        confidence = max(70, min(97, 74 + int(slot_type_match * 10) + (100 - traffic_pressure) // 8))
        reasons = []
        if distance <= 70:
            reasons.append("Closest to the entrance")
        if traffic_pressure < 60:
            reasons.append("Low traffic zone")
        if ev_ready and intent_type == "ev":
            reasons.append("EV charger available")
        if priority >= 3 and intent_type == "wheelchair":
            reasons.append("Step-free accessibility")
        if vehicle_size in {"suv", "truck"} and intent_type == "suv":
            reasons.append("SUV-sized fit")
        if len(reasons) < 2:
            reasons.append("Strong availability profile")

        scored.append({
            "slot": slot,
            "score": score,
            "confidence": confidence,
            "walking_distance": int(distance),
            "traffic": int(traffic_pressure),
            "accessibility": accessibility,
            "reasons": reasons[:3],
        })

    scored.sort(key=lambda item: item["score"], reverse=True)
    top = scored[0]
    alternatives = []
    for candidate in scored[1:4]:
        reason_text = candidate["reasons"][0] if candidate["reasons"] else "Strong availability profile"
        alternatives.append({
            "id": _slot_value(candidate["slot"], "id"),
            "slot_number": _slot_value(candidate["slot"], "slot_number"),
            "zone": _slot_value(candidate["slot"], "block_name", "Main Deck"),
            "reason": reason_text,
            "score": candidate["score"],
        })

    return {
        "intent": intent,
        "mode": "ai",
        "message": f"I found the best fit for {intent.lower()}.",
        "recommended_slot": {
            "id": _slot_value(top["slot"], "id"),
            "slot_number": _slot_value(top["slot"], "slot_number"),
            "zone": _slot_value(top["slot"], "block_name", "Main Deck"),
            "floor": _slot_value(top["slot"], "floor", "Ground Floor"),
            "status": _slot_value(top["slot"], "status", "available"),
            "distance_from_entrance": top["walking_distance"],
        },
        "walking_distance": top["walking_distance"],
        "parking_score": top["score"],
        "confidence": top["confidence"],
        "traffic": top["traffic"],
        "accessibility": top["accessibility"],
        "reasons": top["reasons"],
        "alternatives": alternatives,
        "score_breakdown": {
            "distance": max(0, min(100, 100 - top["walking_distance"])),
            "traffic": max(0, 100 - top["traffic"]),
            "slot_match": max(0, min(100, int(top["confidence"]))),
        },
    }


def build_prediction_payload():
    current_hour = datetime.now().hour
    zones = [
        {"name": "Zone A", "fill_level": max(30, min(94, 52 + ((current_hour % 8) * 5))), "eta_minutes": 10 + ((current_hour % 5) * 2)},
        {"name": "Zone B", "fill_level": max(28, min(90, 46 + ((current_hour % 7) * 6))), "eta_minutes": 8 + ((current_hour % 4) * 3)},
        {"name": "Zone C", "fill_level": max(36, min(96, 58 + ((current_hour % 9) * 5))), "eta_minutes": 12 + ((current_hour % 6) * 2)},
    ]
    return {"zones": zones, "generated_at": datetime.now().isoformat()}


def build_city_status_payload():
    active_slots = 42
    occupied = 28
    available = active_slots - occupied
    reserved = 9
    ev_total = 12
    ev_available = 5
    co2_saved = 84
    search_time = 4.8
    occupancy_pct = int(round((occupied / active_slots) * 100))
    return {
        "available_slots": available,
        "occupied": occupied,
        "reserved": reserved,
        "ev_chargers": {"available": ev_available, "total": ev_total},
        "co2_saved": co2_saved,
        "average_search_time": search_time,
        "occupancy_pct": occupancy_pct,
        "updated_at": datetime.now().isoformat(),
    }


def build_demo_mode_payload():
    return {
        "demo_mode": True,
        "label": "Demo mode active",
        "status": build_city_status_payload(),
        "prediction": build_prediction_payload(),
    }


def build_ai_assistant_response(vehicle_type="Sedan", requires_ev=False, slots=None):
    # New AI Parking Negotiator
    slots = slots or []
    available_slots = [slot for slot in slots if _slot_value(slot, "status") == "available"]
    if not available_slots:
        return {"mode": "fallback", "message": "No available parking slots are currently open. Please try again shortly.",}

    # Gather context features for each slot and compute an optimization score 0-100.
    candidates = []
    now_hour = datetime.now().hour
    for slot in available_slots:
        # Core factors (normalized heuristics)
        distance = float(_slot_value(slot, "distance_from_entrance", 60))  # meters
        ev = 1.0 if _slot_value(slot, "ev_charging", 0) else 0.0
        priority = float(_slot_value(slot, "priority", 1))
        vehicle_size = _slot_value(slot, "vehicle_size", "Sedan").lower()
        size_score = 1.0 if vehicle_type and vehicle_type.lower() == vehicle_size else 0.5
        # Reserved or special handling reduces score
        reserved = 1 if _slot_value(slot, "status") == "reserved" else 0

        # Simulated factors: congestion and exit convenience derived from distance and priority
        congestion = max(0.0, min(1.0, (distance - 20) / 200))  # more distance tends to more congestion
        exit_convenience = max(0.0, min(1.0, priority / 5.0 + (60 - distance) / 200.0))

        # Duration preference (shorter stays prefer closer slots). Use vehicle_type as proxy for duration preference.
        expected_duration_hours = 2.0 if vehicle_type and vehicle_type.lower() in ("sedan", "suv") else 1.0

        # Carbon footprint heuristic: prefer closer + low congestion
        carbon_saving = max(0.0, (1.0 - (distance / 300.0)) * (1.0 - congestion))

        # Future reservations penalty (if a slot has upcoming reservations, deprioritize)
        upcoming_reservations = 0
        try:
            conn = get_db()
            # Count reservations for this slot that are active in the future
            row = conn.execute("SELECT COUNT(*) FROM reservations WHERE slot_id = ? AND expiry_time > ? AND status = 'active'", (slot["id"], datetime.now().isoformat(),)).fetchone()
            upcoming_reservations = int(row[0]) if row else 0
        except Exception:
            upcoming_reservations = 0

        reservation_penalty = 0.25 * min(1.0, upcoming_reservations / 3.0)

        # Weighted scoring: build components
        w_distance = 0.28
        w_exit = 0.18
        w_ev = 0.14
        w_size = 0.12
        w_duration = 0.08
        w_carbon = 0.1
        w_reservation = -0.1

        # Normalize distance to 0..1 (closer => 1.0)
        distance_norm = max(0.0, min(1.0, 1.0 - (distance / 300.0)))

        raw_score = (
            w_distance * distance_norm
            + w_exit * exit_convenience
            + w_ev * ev
            + w_size * size_score
            + w_duration * (1.0 / (1.0 + expected_duration_hours))
            + w_carbon * carbon_saving
            + w_reservation * reservation_penalty
        )

        # Map raw_score to 0-100
        opt_score = int(max(0, min(100, round(raw_score * 100))))

        candidates.append(
            {
                "slot": slot,
                "distance": distance,
                "ev": bool(ev),
                "priority": priority,
                "vehicle_size": vehicle_size,
                "congestion": round(congestion, 2),
                "exit_convenience": round(exit_convenience, 2),
                "carbon_saving": round(carbon_saving, 2),
                "upcoming_reservations": upcoming_reservations,
                "score": opt_score,
            }
        )

    # Sort candidates by score desc
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Prepare explanation components and top-3 comparison
    top3 = candidates[:3]
    if not top3:
        return {"mode": "fallback", "message": "No suitable slots available.", "recommended_slot": None}

    recommended = top3[0]

    def explain_candidate(c):
        s = c["slot"]
        lines = []
        lines.append(f"Slot {s['slot_number']}")
        lines.append(f"Score: {c['score']}/100")
        lines.append(f"Distance: {int(c['distance'])} m")
        lines.append(f"Exit convenience: {c['exit_convenience']}")
        lines.append(f"EV charging: {'Yes' if c['ev'] else 'No'}")
        lines.append(f"Vehicle match: {c['vehicle_size'].capitalize()}")
        if c['upcoming_reservations']:
            lines.append(f"Upcoming reservations: {c['upcoming_reservations']}")
        lines.append(f"Estimated carbon saving factor: {c['carbon_saving']}")
        return lines

    explanation = {
        "recommended_slot": recommended["slot"],
        "score": recommended["score"],
        "reasons": explain_candidate(recommended),
        "top3": [
            {"slot": c["slot"], "score": c["score"], "reason_lines": explain_candidate(c)} for c in top3
        ],
    }

    # Return structured response used by templates and UI
    return {"mode": "ai-negotiator", "explanation": explanation}


def build_chat_reply(message, slots=None):
    text = (message or "").strip().lower()
    slots = slots or []
    available_slots = [slot for slot in slots if _slot_value(slot, "status") == "available"]

    if any(word in text for word in ["hi", "hello", "hey", "hola"]):
        return "Hi! I can help you find a parking spot. Try asking about an EV slot, an SUV slot, or how busy the parking is."

    if any(word in text for word in ["thanks", "thank you", "thank"]):
        return "You’re welcome! I’m happy to help with parking."

    if any(word in text for word in ["what's up", "whats up", "how are you"]):
        return "I’m doing great and ready to help you find a parking spot."

    if "ev" in text or "electric" in text:
        if available_slots:
            ev_slot = next((slot for slot in available_slots if _slot_value(slot, "ev_charging")), None)
            if ev_slot:
                return f"Yep — there’s an EV-friendly spot available: {_slot_value(ev_slot, 'slot_number')}."
        return "Right now, I don’t see any EV-friendly slot available."

    if "suv" in text:
        if available_slots:
            suv_slot = next((slot for slot in available_slots if _slot_value(slot, "vehicle_size", "Sedan").lower() == "suv"), None)
            if suv_slot:
                return f"Sure — a roomy SUV-friendly slot is available: {_slot_value(suv_slot, 'slot_number')}."
        return "I don’t see an SUV-friendly slot available at the moment."

    if "occup" in text or "busy" in text or "full" in text:
        return "The parking area is being checked live. It looks like the system is tracking occupancy for you."

    if "best" in text or "recommend" in text or "which" in text:
        if available_slots:
            first_slot = available_slots[0]
            return f"I’d suggest starting with {_slot_value(first_slot, 'slot_number')} — it’s available right now."
        return "There isn’t a free slot available at the moment."

    if available_slots:
        first_slot = available_slots[0]
        return f"You can try {_slot_value(first_slot, 'slot_number')} — it looks open right now."
    return "Looks like all parking spots are full right now."


def get_notification_messages(slots=None):
    slots = slots or []
    alerts = []
    for slot in slots:
        if _slot_value(slot, "status") == "available":
            continue
        alerts.append(f"Slot {_slot_value(slot, 'slot_number')} is currently {_slot_value(slot, 'status')}.")
    if not alerts:
        alerts.append("All slots are available right now.")
    return alerts


MODEL_PATH = os.path.join(os.path.dirname(__file__), "static", "models", "parking_model.joblib")
DATA_PATH = os.path.join(os.path.dirname(__file__), "static", "models", "parking_data.json")


def _ensure_model_artifacts():
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    if not os.path.exists(DATA_PATH):
        payload = [
            {"hour": 6, "day": 1, "occupancy": 34, "available": 37},
            {"hour": 7, "day": 1, "occupancy": 46, "available": 25},
            {"hour": 8, "day": 1, "occupancy": 68, "available": 7},
            {"hour": 9, "day": 1, "occupancy": 79, "available": 4},
            {"hour": 10, "day": 1, "occupancy": 85, "available": 2},
            {"hour": 11, "day": 1, "occupancy": 88, "available": 1},
            {"hour": 12, "day": 2, "occupancy": 73, "available": 10},
            {"hour": 13, "day": 2, "occupancy": 81, "available": 5},
            {"hour": 14, "day": 2, "occupancy": 89, "available": 3},
            {"hour": 15, "day": 3, "occupancy": 78, "available": 8},
            {"hour": 16, "day": 3, "occupancy": 69, "available": 12},
            {"hour": 17, "day": 4, "occupancy": 84, "available": 6},
            {"hour": 18, "day": 4, "occupancy": 75, "available": 11},
            {"hour": 19, "day": 5, "occupancy": 62, "available": 17},
            {"hour": 20, "day": 6, "occupancy": 54, "available": 23},
            {"hour": 21, "day": 7, "occupancy": 48, "available": 29},
        ]
        with open(DATA_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


def train_prediction_model():
    _ensure_model_artifacts()
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    X = np.array([[item["hour"], item["day"]] for item in data], dtype=float)
    y = np.array([item["occupancy"] for item in data], dtype=float)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_PATH)
    return model


def load_prediction_model():
    if not os.path.exists(MODEL_PATH) or os.path.getmtime(DATA_PATH) > os.path.getmtime(MODEL_PATH):
        train_prediction_model()
    return joblib.load(MODEL_PATH)


def build_prediction_summary():
    if not os.path.exists(MODEL_PATH) or os.path.getmtime(DATA_PATH) > os.path.getmtime(MODEL_PATH):
        train_prediction_model()
    model = load_prediction_model()
    hour = datetime.now().hour
    day = datetime.now().weekday() + 1
    prediction = int(round(float(model.predict(np.array([[hour, day]], dtype=float))[0])))
    prediction = max(50, min(99, prediction))
    return {
        "occupancy_prediction": prediction,
        "message": f"Parking is expected to be about {prediction}% full at {hour}:00.",
        "hour": hour,
        "day": day,
    }


def build_recommendation(user, slots, vehicle_type="Sedan", requires_ev=False):
    available_slots = [slot for slot in slots if _slot_value(slot, "status") == "available"]
    total_slots = len(slots)
    occupied_count = sum(1 for slot in slots if _slot_value(slot, "status") == "occupied")
    utilization = int(round((occupied_count / total_slots) * 100)) if total_slots else 0

    if not available_slots:
        return {
            "recommended_slot": None,
            "overall_score": 0,
            "confidence": 0,
            "metrics": {},
            "explanation": ["No available slot could be recommended at this time."],
            "top_alternatives": [],
        }

    candidates = []
    for slot in available_slots:
        distance = float(_slot_value(slot, "distance_from_entrance", 100))
        priority = float(_slot_value(slot, "priority", 2))
        ev = bool(_slot_value(slot, "ev_charging", 0))
        size = _slot_value(slot, "vehicle_size", "Sedan").lower()
        vehicle_match = 1.0 if vehicle_type and vehicle_type.lower() == size else 0.65

        distance_score = max(0.0, min(1.0, 1.0 - distance / 260.0))
        safety_score = max(0.0, min(1.0, priority / 5.0 * 0.7 + (1.0 - distance / 260.0) * 0.3))
        traffic_score = max(0.0, min(1.0, 1.0 - distance / 240.0 + (priority - 1) * 0.03))
        exit_score = max(0.0, min(1.0, priority / 5.0 * 0.45 + (1.0 - distance / 220.0) * 0.55))
        accessibility_score = max(0.0, min(1.0, distance_score * 0.55 + (priority / 5.0) * 0.2 + vehicle_match * 0.25))
        co2_saved = max(0.0, min(1.0, 1.0 - distance / 300.0))
        energy_efficiency = 0.95 if ev else 0.62

        future_reservations = 0
        try:
            conn = get_db()
            row = conn.execute(
                "SELECT COUNT(*) FROM reservations WHERE slot_id = ? AND expiry_time > ? AND status = 'active'",
                (_slot_value(slot, "id"), datetime.now().isoformat()),
            ).fetchone()
            future_reservations = int(row[0]) if row else 0
        except Exception:
            future_reservations = 0

        reservation_penalty = min(0.18, future_reservations * 0.06)
        ev_bonus = 0.16 if requires_ev and ev else 0.0
        ev_penalty = 0.18 if requires_ev and not ev else 0.0

        raw_score = (
            0.22 * distance_score
            + 0.17 * safety_score
            + 0.14 * traffic_score
            + 0.14 * exit_score
            + 0.11 * accessibility_score
            + 0.08 * co2_saved
            + 0.07 * energy_efficiency
            + 0.05 * vehicle_match
            + ev_bonus
            - ev_penalty
            - reservation_penalty
        )
        smart_score = int(max(0, min(100, round(raw_score * 100))))

        candidates.append(
            {
                "slot": slot,
                "walking_distance": int(distance),
                "safety": int(round(safety_score * 100)),
                "traffic_score": int(round(traffic_score * 100)),
                "exit_convenience": int(round(exit_score * 100)),
                "accessibility": int(round(accessibility_score * 100)),
                "co2_saved": int(round(co2_saved * 100)),
                "energy_efficiency": int(round(energy_efficiency * 100)),
                "parking_utilization": utilization,
                "smart_score": smart_score,
                "future_reservations": future_reservations,
                "ev_charging": ev,
                "vehicle_match": int(round(vehicle_match * 100)),
                "priority": int(priority),
            }
        )

    candidates.sort(key=lambda item: item["smart_score"], reverse=True)
    recommended = candidates[0]
    alternatives = candidates[1:4]

    if len(candidates) > 1:
        advantage = recommended["smart_score"] - candidates[1]["smart_score"]
        confidence = int(max(60, min(98, 70 + advantage)))
    else:
        confidence = 88

    def explain(candidate):
        lines = [
            f"Overall smart score: {candidate['smart_score']} out of 100.",
            f"Distance: {candidate['walking_distance']}m from the entrance.",
            f"Safety: {candidate['safety']} / 100.",
            f"Traffic score: {candidate['traffic_score']} / 100.",
            f"Exit convenience: {candidate['exit_convenience']} / 100.",
            f"Accessibility: {candidate['accessibility']} / 100.",
        ]
        if candidate["ev_charging"]:
            lines.append("Includes EV charging for electric vehicles.")
        if candidate["future_reservations"]:
            lines.append(f"There are {candidate['future_reservations']} active reservation(s) nearby, so access timing is taken into account.")
        lines.append(f"Facility utilization is currently {utilization}% so this slot is chosen for balanced efficiency.")
        return lines

    def reject_reason(candidate, winner):
        reasons = []
        if candidate["walking_distance"] > winner["walking_distance"] + 20:
            reasons.append("Longer walk")
        if candidate["safety"] + 8 < winner["safety"]:
            reasons.append("Lower safety rating")
        if candidate["exit_convenience"] + 10 < winner["exit_convenience"]:
            reasons.append("Less convenient exit")
        if candidate["traffic_score"] + 10 < winner["traffic_score"]:
            reasons.append("Heavier traffic exposure")
        if requires_ev and winner["ev_charging"] and not candidate["ev_charging"]:
            reasons.append("No EV charging")
        if candidate["future_reservations"] > winner["future_reservations"]:
            reasons.append("Greater reservation risk")
        if not reasons:
            reasons.append("Slightly lower overall score compared to the chosen slot.")
        return ", ".join(reasons)

    top_alternatives = []
    for alt in alternatives:
        top_alternatives.append(
            {
                "slot": alt["slot"],
                "score": alt["smart_score"],
                "reason": reject_reason(alt, recommended),
                "metrics": {
                    "walking_distance": alt["walking_distance"],
                    "safety": alt["safety"],
                    "traffic_score": alt["traffic_score"],
                    "exit_convenience": alt["exit_convenience"],
                    "accessibility": alt["accessibility"],
                    "co2_saved": alt["co2_saved"],
                    "energy_efficiency": alt["energy_efficiency"],
                },
            }
        )

    return {
        "recommended_slot": recommended["slot"],
        "overall_score": recommended["smart_score"],
        "confidence": confidence,
        "metrics": {
            "walking_distance": recommended["walking_distance"],
            "safety": recommended["safety"],
            "traffic_score": recommended["traffic_score"],
            "exit_convenience": recommended["exit_convenience"],
            "accessibility": recommended["accessibility"],
            "co2_saved": recommended["co2_saved"],
            "energy_efficiency": recommended["energy_efficiency"],
            "parking_utilization": utilization,
        },
        "explanation": explain(recommended),
        "top_alternatives": top_alternatives,
    }


def build_analytics_payload(db):
    slots = db.execute("SELECT status FROM parking_slots").fetchall()
    users = db.execute("SELECT vehicle_type FROM users").fetchall()
    history = db.execute("SELECT entry_time, exit_time FROM parking_history").fetchall()
    status_counts = {"available": 0, "occupied": 0, "reserved": 0}
    for row in slots:
        status_counts[row[0]] = status_counts.get(row[0], 0) + 1
    vehicle_counts = {}
    for row in users:
        vehicle_counts[row[0]] = vehicle_counts.get(row[0], 0) + 1
    return {
        "statistics": {
            "total_slots": len(slots),
            "available_slots": status_counts.get("available", 0),
            "occupied_slots": status_counts.get("occupied", 0),
            "reserved_slots": status_counts.get("reserved", 0),
            "total_users": len(users),
            "entries_today": sum(1 for row in history if row["entry_time"] and row["entry_time"].startswith(datetime.now().strftime("%Y-%m-%d"))),
            "exits_today": sum(1 for row in history if row["exit_time"] and row["exit_time"].startswith(datetime.now().strftime("%Y-%m-%d"))),
        },
        "vehicle_types": vehicle_counts,
        "occupancy_series": [20, 45, 70, 65, 90, 88],
        "weekly_series": [40, 50, 65, 60, 75, 80, 70],
        "monthly_series": [300, 340, 390, 430, 470, 520, 580],
        "peak_hours": [8, 10, 12, 17],
    }


def get_ocr_result(image_path: str):
    try:
        import easyocr
        import cv2
        import numpy as np
    except Exception:
        return {"vehicle_number": None, "ocr_text": "OCR libraries unavailable", "confidence_score": 0.0}

    reader = easyocr.Reader(["en"], gpu=False)
    image = cv2.imread(image_path)
    if image is None:
        return {"vehicle_number": None, "ocr_text": "Image unavailable", "confidence_score": 0.0}
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results = reader.readtext(thresh)
    if not results:
        return {"vehicle_number": None, "ocr_text": "No plate detected", "confidence_score": 0.0}
    best = max(results, key=lambda item: item[2])
    text = "".join(ch for ch in best[1] if ch.isalnum()).upper()
    confidence = float(best[2])
    return {"vehicle_number": text, "ocr_text": text, "confidence_score": confidence}


def simulate_what_if(scenario: str, params: dict, slots: List[Dict]):
    """Run an in-memory simulation based on a scenario name and params.

    Does NOT modify the real database. Returns a payload with:
      - simulated_slots: list of slot dicts (with simulated status/occupancy)
      - metrics: congestion, available_slots, utilization, avg_wait_time, peak_areas, routing
      - timeline: series for animated charts
    """
    # Defensive copy
    base = [dict(s) for s in slots]

    # Helpers
    def count_status(items, status):
        return sum(1 for it in items if it.get("status") == status)

    total = len(base)
    available = count_status(base, "available")

    # Default modifiers
    arrival_rate = params.get("arrival_rate", 1.0)
    extra_arrivals = int(params.get("extra_arrivals", 0))
    ev_surge = params.get("ev_surge", False)
    entrance_closed = params.get("entrance_closed", False)
    weather = params.get("weather", "clear")
    event = params.get("event", False)

    # Simulate arrivals: try to occupy available slots
    simulated = [dict(s) for s in base]

    # If EV surge, prefer EV slots
    ev_slots = [s for s in simulated if s.get("ev_charging")]
    non_ev_slots = [s for s in simulated if not s.get("ev_charging")]

    arrivals = extra_arrivals
    if event:
        arrivals += int(total * 0.25)
    if weather == "rainy":
        # rainy increases dwell time and reduces turnover
        arrival_rate *= 1.15
        arrivals += int(total * 0.05)

    # Fill EV area first if surge
    def occupy_slots(list_slots, num):
        filled = 0
        for s in list_slots:
            if filled >= num:
                break
            if s.get("status") == "available":
                s["status"] = "occupied"
                s["simulated_occupied"] = True
                filled += 1
        return filled

    ev_fill = 0
    if ev_surge:
        ev_fill = occupy_slots(ev_slots, arrivals)

    remaining = arrivals - ev_fill
    if remaining > 0:
        occupy_slots(non_ev_slots, remaining)

    # EV charging full scenario
    if params.get("ev_area_full"):
        for s in ev_slots:
            if s.get("status") == "available":
                s["status"] = "reserved"
                s["simulated_reserved"] = True

    # Entrance closed increases congestion near low-priority slots
    if entrance_closed:
        for s in simulated:
            pr = float(s.get("priority", 1))
            # lower priority = further from main entrance in this heuristic
            if pr <= 1:
                s["congestion_multiplier"] = 1.3
            else:
                s["congestion_multiplier"] = 1.0
    else:
        for s in simulated:
            s["congestion_multiplier"] = 1.0

    # Compute metrics
    occupied = count_status(simulated, "occupied")
    reserved = count_status(simulated, "reserved")
    available_after = total - occupied - reserved
    utilization = int(round((occupied / total) * 100)) if total else 0

    # Congestion: base occupancy + modifiers
    avg_congestion = min(100, int(round((occupied / total) * 100 * arrival_rate)))
    if entrance_closed:
        avg_congestion = min(100, int(avg_congestion * 1.2))
    if event:
        avg_congestion = min(100, int(avg_congestion * 1.35))

    # Average waiting time heuristic (minutes)
    avg_wait = max(0, int((occupied - available) * 0.8))
    if weather == "rainy":
        avg_wait = int(avg_wait * 1.25 + 3)

    # Peak areas: blocks with most simulated occupied
    from collections import Counter

    block_counts = Counter([s.get("block_name") for s in simulated if s.get("status") == "occupied"])
    peak_areas = [b for b, _ in block_counts.most_common(3)]

    # Routing recommendation: avoid entrances with multiplier >1.2
    congested_entrances = [s.get("block_name") for s in simulated if s.get("congestion_multiplier", 1.0) > 1.2]
    routing = "Use main entrances and direct cars to floors with available slots."
    if congested_entrances:
        routing = f"Avoid blocks: {', '.join(set(congested_entrances))}. Route arrivals to less congested blocks."

    # Timeline: simple series for next 60 minutes showing occupancy
    timeline = []
    base_occ = occupied
    for minute in range(0, 61, 5):
        # decay or increase based on event/weather
        change = int((arrival_rate - 1.0) * total * 0.02 * (minute / 60.0))
        if event:
            change += int(total * 0.02)
        occ = max(0, min(total, base_occ + change))
        timeline.append({"minute": minute, "occupied": occ, "available": total - occ})

    payload = {
        "simulated_slots": simulated,
        "metrics": {
            "expected_congestion": avg_congestion,
            "available_slots": available_after,
            "utilization_percent": utilization,
            "avg_wait_time_min": avg_wait,
            "peak_areas": peak_areas,
            "routing": routing,
        },
        "timeline": timeline,
    }
    return payload


def build_parking_replay(start_date: str = None, end_date: str = None):
    conn = get_db()
    slots = [dict(s) for s in conn.execute("SELECT * FROM parking_slots ORDER BY slot_number").fetchall()]
    history_rows = [dict(r) for r in conn.execute(
        "SELECT ph.*, u.full_name, u.vehicle_number, s.slot_number, s.block_name FROM parking_history ph JOIN users u ON u.id = ph.user_id JOIN parking_slots s ON s.id = ph.slot_id ORDER BY ph.entry_time ASC"
    ).fetchall()]
    reservation_rows = [dict(r) for r in conn.execute(
        "SELECT r.*, u.full_name, u.vehicle_number, s.slot_number, s.block_name FROM reservations r JOIN users u ON u.id = r.user_id JOIN parking_slots s ON s.id = r.slot_id ORDER BY r.reservation_time ASC"
    ).fetchall()]

    events = []
    for row in history_rows:
        if row.get("entry_time"):
            events.append({
                "type": "entry",
                "time": row["entry_time"],
                "slot_id": row["slot_id"],
                "slot_number": row["slot_number"],
                "block_name": row["block_name"],
                "user": row["full_name"],
                "vehicle_number": row["vehicle_number"],
                "vehicle_type": row.get("vehicle_type", "Sedan"),
                "description": f"{row['full_name']} entered {row['slot_number']}",
                "history_id": row["id"],
            })
        if row.get("exit_time"):
            events.append({
                "type": "exit",
                "time": row["exit_time"],
                "slot_id": row["slot_id"],
                "slot_number": row["slot_number"],
                "block_name": row["block_name"],
                "user": row["full_name"],
                "vehicle_number": row["vehicle_number"],
                "vehicle_type": row.get("vehicle_type", "Sedan"),
                "description": f"{row['full_name']} left {row['slot_number']}",
                "history_id": row["id"],
            })

    for row in reservation_rows:
        events.append({
            "type": "reservation",
            "time": row["reservation_time"],
            "slot_id": row["slot_id"],
            "slot_number": row["slot_number"],
            "block_name": row["block_name"],
            "user": row["full_name"],
            "vehicle_number": row["vehicle_number"],
            "vehicle_type": row.get("vehicle_type", "Sedan"),
            "description": f"{row['full_name']} reserved {row['slot_number']}",
            "reservation_id": row["id"],
            "status": row["status"],
        })

    events = [e for e in events if e.get("time")]
    events.sort(key=lambda e: e["time"])

    state = {slot["id"]: {"status": slot.get("status", "available"), "slot_number": slot["slot_number"], "block_name": slot.get("block_name"), "vehicle_size": slot.get("vehicle_size", "Sedan")} for slot in slots}
    timeline = []
    event_list = []

    def to_minutes(start, end):
        try:
            if not start or not end:
                return 0
            fmt = datetime.fromisoformat(start)
            fend = datetime.fromisoformat(end)
            return int((fend - fmt).total_seconds() / 60)
        except Exception:
            return 0

    for event in events:
        if event["type"] == "entry":
            state[event["slot_id"]]["status"] = "occupied"
        elif event["type"] == "exit":
            state[event["slot_id"]]["status"] = "available"
        elif event["type"] == "reservation":
            state[event["slot_id"]]["status"] = "reserved"

        occupied_count = sum(1 for s in state.values() if s["status"] == "occupied")
        reserved_count = sum(1 for s in state.values() if s["status"] == "reserved")
        available_count = len(state) - occupied_count - reserved_count
        recommendation = build_recommendation({"vehicle_type": event.get("vehicle_type", "Sedan")}, [dict({**s, "status": s["status"]}) for s in slots], event.get("vehicle_type", "Sedan"), False)
        event_list.append({
            **event,
            "occupancy": occupied_count,
            "reserved": reserved_count,
            "available": available_count,
            "recommendation": recommendation,
        })
        timeline.append({"time": event["time"], "occupied": occupied_count, "reserved": reserved_count, "available": available_count})

    total_wait = 0
    completed = [row for row in history_rows if row.get("exit_time")]
    for row in completed:
        total_wait += to_minutes(row.get("entry_time"), row.get("exit_time"))
    avg_wait = int(total_wait / len(completed)) if completed else 0

    peak_occupancy = max((item["occupied"] for item in timeline), default=0)
    reservation_count = sum(1 for event in event_list if event["type"] == "reservation")

    return {
        "slots": slots,
        "events": event_list,
        "timeline": timeline,
        "metrics": {
            "total_events": len(event_list),
            "avg_wait_time_min": avg_wait,
            "peak_occupancy": peak_occupancy,
            "reservation_count": reservation_count,
        },
    }
