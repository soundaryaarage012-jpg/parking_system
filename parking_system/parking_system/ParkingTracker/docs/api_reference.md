# Smart Parking API Reference

## Overview
This project keeps the original REST endpoints and Socket.IO event contracts intact while adding additive AI and real-time surfaces. The UI consumes these payloads as-is and degrades gracefully when a service is unavailable.

## Core routes

### GET /
Landing page for the application.

### GET /dashboard
Authenticated dashboard for the current user.

### GET /parking
Parking map and digital twin view.

### GET /parking/<slot_id>
Detailed slot view.

### POST /reserve/<slot_id>
Reserve a currently available slot.

### POST /cancel-reservation/<slot_id>
Cancel an active reservation for the current user.

### POST /occupy/<slot_id>
Mark a slot as occupied.

### POST /release/<slot_id>
Release a slot after use.

### GET /prediction
Prediction view.

### GET /ai-assistant
AI Copilot screen.

### GET /api/summary
Returns dashboard summary stats.

### GET /api/slots
Returns parking slots filtered by status, block, or floor.

### GET /api/ai/recommendation
Returns an AI recommendation payload for the selected intent.
Supported parameters:
- intent
- vehicle_type
- requires_ev

Example:
```http
GET /api/ai/recommendation?intent=EV%20parking
```

Response shape:
```json
{
  "intent": "EV parking",
  "mode": "ai",
  "message": "I found the best fit for ev parking.",
  "recommended_slot": {
    "id": 7,
    "slot_number": "B03",
    "zone": "First Floor",
    "floor": "First Floor",
    "status": "available",
    "distance_from_entrance": 100
  },
  "walking_distance": 100,
  "parking_score": 50,
  "confidence": 89,
  "traffic": 56,
  "accessibility": {
    "ev_ready": true,
    "wheelchair": false,
    "step_free": true,
    "bike_friendly": false
  },
  "reasons": ["Low traffic zone", "EV charger available"],
  "alternatives": [
    {"id": 2, "slot_number": "A-02", "zone": "Block A", "reason": "Closest to the entrance", "score": 48}
  ]
}
```

### GET /api/predictions
Returns prediction payload for the city/dashboard view.

Response shape:
```json
{
  "generated_at": "2026-08-03T21:10:13.132717",
  "zones": [
    {"name": "Zone A", "fill_level": 77, "eta_minutes": 12},
    {"name": "Zone B", "fill_level": 46, "eta_minutes": 11},
    {"name": "Zone C", "fill_level": 73, "eta_minutes": 18}
  ]
}
```

### GET /api/city/status
Returns the smart city status payload used by the status bar.

Response shape:
```json
{
  "available_slots": 14,
  "occupied": 28,
  "reserved": 9,
  "ev_chargers": {"available": 5, "total": 12},
  "co2_saved": 84,
  "average_search_time": 4.8,
  "occupancy_pct": 67,
  "updated_at": "2026-08-03T21:10:13.107812"
}
```

### GET /api/demo/state
Returns demo-mode payload used during presentation mode.

### GET /api/replay/data
Returns replay data for the playback screen.

### POST /api/what-if/simulate
Admin simulation endpoint used by the what-if screen.

## Socket.IO
The app emits live parking data through Socket.IO using the existing `parking_update` and `parking_state` events.

### Event: parking_update
Payload shape:
```json
{
  "message": "Reservation confirmed for A12",
  "stats": {"total_slots": 42, "available_slots": 13},
  "slots": [{"id": 1, "slot_number": "A1", "status": "available"}],
  "reservations": []
}
```

### Event: parking_state
Payload shape:
```json
{
  "message": "state",
  "stats": {"total_slots": 42, "available_slots": 13},
  "slots": [{"id": 1, "slot_number": "A1", "status": "available"}],
  "recent_movements": [],
  "reservations": []
}
```

## Notes
- REST endpoints remain the source of truth during initial page load.
- Socket.IO provides additive live delta updates and reconnects with the standard Flask-SocketIO client behavior.
- All new AI surfaces are designed to fall back safely when no recommendation is available.
- The project does not require a backend rewrite to enable the premium frontend and live intelligence pass.
