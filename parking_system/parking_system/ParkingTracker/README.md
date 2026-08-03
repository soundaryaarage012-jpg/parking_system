# Smart Parking Space Tracker

## Overview
Smart Parking Space Tracker is a premium Flask + SQLite parking intelligence platform that combines a cinematic frontend with additive AI and real-time intelligence layers. The project keeps the existing backend contract intact while exposing new recommendation, prediction, and live-status surfaces for Copilot-guided parking experiences.

## Phase 2 highlights
- AI Copilot intent surface with quick actions for nearest, EV, wheelchair, quick-stop, bike, and SUV parking
- AI parking score with explainable slot ranking and fallback-safe recommendation payloads
- Predictive availability service with a dedicated endpoint and status-bar surfacing
- Digital Twin overlays for vision mode and prediction mode
- Socket.IO live occupancy updates with graceful reconnect behavior and REST fallback
- Demo mode using shared component interfaces with simulated data instead of parallel UI

## Quickstart
1. Open a terminal in the project root.
2. Install dependencies:
   ```bash
   pip install -r ParkingTracker/requirements.txt
   ```
3. Start the app:
   ```bash
   cd parking_system
   python app.py
   ```
4. Open the local UI:
   ```text
   http://127.0.0.1:5000/
   ```

## Main user journeys
- Landing page and premium hero experience
- Digital Twin parking map with live slot states and AI overlays
- AI Copilot recommendation card and quick intent chips
- Smart city status bar with live metrics and predictive insight
- Reservation, occupancy, release, and historical parking flows
- Demo mode for presentation conditions without a separate demo UI

## Project structure
- app.py — app entry point
- ParkingTracker/app.py — Flask app factory and socket setup
- ParkingTracker/models.py — SQLite schema and data layer
- ParkingTracker/routes.py — routes and live update endpoints
- ParkingTracker/services.py — AI recommendation, status, prediction, demo, and analytics logic
- ParkingTracker/static/ — CSS, JS, visual assets, and model files
- ParkingTracker/templates/ — UI screens
- ParkingTracker/docs/ — architecture, API, and deployment reference docs

## Stack
- Python Flask
- Flask-SocketIO
- Flask-Login
- SQLite
- Bootstrap 5 + custom premium styling
- JavaScript + live UI hooks
- scikit-learn, joblib, NumPy
- QR generation and OCR-ready integration

## Live AI and realtime surfaces
- REST endpoints remain the source of truth for initial page load
- Socket.IO broadcasts live slot and reservation deltas
- AI recommendation endpoint supports natural-language intent-based scoring
- Prediction endpoint exposes zone-level forecast values for status and map visualization
- Demo mode feeds the same UI interfaces with mocked data so the behavior remains consistent

## Demo mode
Use the existing demo toggle in the UI to activate simulated live movement, occupancy transitions, and AI recommendation timing. The mode is presentation-safe and does not require a separate data path.

## Documentation
See the in-repo docs for:
- API contract reference in [ParkingTracker/docs/api_reference.md](ParkingTracker/docs/api_reference.md)
- Architecture diagram in [ParkingTracker/docs/architecture_diagram.md](ParkingTracker/docs/architecture_diagram.md)
- Deployment guide in [ParkingTracker/docs/deployment_guide.md](ParkingTracker/docs/deployment_guide.md)

## Notes
- The app initializes its SQLite database automatically on first run.
- The AI recommendation and predictive layers are heuristic and service-safe by design, allowing replacement with stronger model-backed services later without UI contract changes.
- Socket.IO reconnect logic stays within the standard Flask-SocketIO client flow and falls back to REST polling through the frontend behavior already implemented in the app shell.
