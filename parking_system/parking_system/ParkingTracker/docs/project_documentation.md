# Smart Parking Space Tracker - Project Documentation

## 1. Project Overview
Smart Parking Space Tracker is a Flask-based web application for managing parking slots, reservations, occupancy, parking history, and reports. The system is designed for a small parking facility with a simple SQLite database and a Bootstrap-based user interface.

## 2. Working Model of the Project
The application works in the following way:
1. Users register and log in.
2. The admin or user can view available, occupied, and reserved parking slots.
3. Users can reserve an available slot.
4. When a vehicle enters, the slot status becomes occupied.
5. When the vehicle leaves, the slot becomes available again.
6. Parking history is logged for tracking and reporting.
7. Forecasting and recommendations are generated using a simple machine learning model.

### Main Flow
- Login/Register -> Dashboard -> Parking Map -> Reserve/Occupy/Release -> History/Reports

## 3. Dataset Used
The project uses a small built-in dataset stored in:
- [ParkingTracker/static/models/parking_data.json](ParkingTracker/static/models/parking_data.json)

This dataset contains sample parking occupancy values for different hours and days. It is used to train a lightweight regression model for occupancy prediction.

### Dataset Fields
- hour
- day
- occupancy
- available

## 4. Current Model Type
The current prediction model is a simple linear regression model stored in:
- [ParkingTracker/static/models/parking_model.joblib](ParkingTracker/static/models/parking_model.joblib)

It predicts occupancy percentage based on time-related inputs.

## 5. Can We Use LLM in This Project?
Yes. An LLM can be integrated, but it should be used as an assistant layer rather than the core parking engine.

### Why LLM is useful here
- It can explain why a slot is recommended.
- It can answer questions like: “Which slot is best for an SUV?”
- It can generate user-friendly parking guidance.
- It can provide natural-language summaries of occupancy and bookings.

### Important note
Because this project has only 11 parking slots, an LLM is not needed for the core logic. The core logic should remain rule-based and database-driven. The LLM can be used for:
- recommendation explanations
- chat/help assistant
- smart natural language interface
- admin insights summarization

## 6. Recommended LLM Integration Approach
A practical design is:
1. Keep the existing slot logic and database intact.
2. Use the current parking data and slot state as input.
3. Send a structured prompt to an LLM for explanation or guidance.
4. If no API key is available, fall back to a local rule-based response.

### Example use cases
- “Recommend the best slot for my SUV near the entrance.”
- “Explain why slot P12 is recommended for EV charging.”
- “Summarize current occupancy for the parking facility.”

## 7. Suggested Implementation for This Project
We can add a simple AI assistant feature in the web app that:
- reads the available slot list
- checks slot status, distance, EV charging, and vehicle size
- returns a human-friendly recommendation
- optionally uses an LLM when an API key is configured

## 8. Recommended Architecture
- Frontend: Flask templates + Bootstrap
- Backend: Flask routes + SQLite
- Prediction: Linear regression model
- AI Layer: Optional OpenAI / Ollama / local LLM integration
- Fallback: Rule-based recommendation

## 9. Best Practical Choice
For this project, the best approach is:
- Use the existing machine learning model for forecasts.
- Use rule-based logic for actual slot assignment.
- Use an LLM only for conversational explanations and assistance.

This gives a strong balance between simplicity, low cost, and real-world usefulness.
