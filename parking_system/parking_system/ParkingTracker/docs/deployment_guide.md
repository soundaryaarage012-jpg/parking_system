# Smart Parking Deployment Guide

## Local deployment
1. Install dependencies:
   ```bash
   pip install -r ParkingTracker/requirements.txt
   ```
2. Start the app:
   ```bash
   cd parking_system
   python app.py
   ```
3. Open:
   ```text
   http://127.0.0.1:5000/
   ```

## Live mode vs demo mode
- Live mode uses the existing SQLite-backed reservation and occupancy flow with real-time Socket.IO updates.
- Demo mode can be toggled in the UI and simulates occupancy changes, AI response refresh, and predictive metrics through the same presentation interfaces used by live mode.

## Environment and runtime notes
- Python 3.10+
- Flask 3.x
- Flask-SocketIO
- SQLite for lightweight deployment
- Optional future ML service integration can be added behind the existing AI recommendation and prediction endpoints without changing the UI contract

## Production deployment considerations
- Use a WSGI server such as Gunicorn in production.
- Configure a reverse proxy such as Nginx or Azure App Service / IIS depending on environment.
- Store the database outside the source tree if you need persistent production data.
- Keep any external AI model endpoints behind a clearly defined service layer so the frontend remains contract-stable.

## Recommended runtime stack
- Python 3.10+
- Flask 3.x
- Flask-SocketIO
- SQLite for pilot deployment
- Static assets served through the Flask app or a CDN-backed static layer

## Release checklist
- Confirm the app starts without errors.
- Check dashboard, AI assistant, Digital Twin, and reservation flows.
- Validate status bar updates and demo mode.
- Confirm live Socket.IO updates trigger correctly.
- Review accessibility and mobile layout across breakpoints.

## Known limitations
- AI recommendation and prediction behavior are heuristic and demo-safe.
- The current platform is optimized for pilot, hackathon, and stakeholder demonstration scenarios rather than enterprise-scale citywide operations.
- Future enhancements can swap the heuristic service layer for external models without changing the UI contract.
