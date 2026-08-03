from datetime import datetime, timedelta
import os
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, Response, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from forms import validate_login, validate_registration
from models import (check_password, create_reservation, get_current_user, get_dashboard_stats, get_db, get_history,
                    get_parking_slots, get_reservations, hash_password, log_history, search_slots, search_users,
                    update_slot_status)
from services import (
    build_ai_assistant_response,
    build_ai_recommendation_payload,
    build_chat_reply,
    build_recommendation,
    build_analytics_payload,
    build_city_status_payload,
    build_demo_mode_payload,
    build_prediction_payload,
    build_prediction_summary,
    get_notification_messages,
    get_ocr_result,
    simulate_what_if,
    build_parking_replay,
)
from utils import calculate_duration, export_history_to_csv, generate_qr_code

bp = Blueprint("main", __name__)
socketio = SocketIO(cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.login_view = "main.login"
login_manager.login_message_category = "warning"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.full_name = row["full_name"]
        self.email = row["email"]
        self.phone = row["phone"]
        self.vehicle_number = row["vehicle_number"]
        self.vehicle_type = row["vehicle_type"] if "vehicle_type" in row.keys() else "Sedan"
        self.role = row["role"]


@login_manager.user_loader
def load_user(user_id):
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row:
        return User(row)
    return None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        role = getattr(current_user, "role", "")
        if not current_user.is_authenticated or role.strip().lower() != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def _current_user_context():
    return current_user if current_user.is_authenticated else None


def _broadcast_update(message):
    # Include slots payload so front-end can render real backend data
    try:
        slots = get_parking_slots({})
        slots_list = [dict(s) for s in slots]
        for s in slots_list:
            try:
                s["qr_path"] = generate_qr_code(s["id"])
            except Exception:
                s["qr_path"] = None
    except Exception:
        slots_list = []
    try:
        reservations = get_reservations()
        reservations_list = [dict(r) for r in reservations]
    except Exception:
        reservations_list = []
    payload = {"message": message, "stats": get_dashboard_stats(), "slots": slots_list, "reservations": reservations_list}
    socketio.emit("parking_update", payload, broadcast=True)


@bp.route("/")
def index():
    stats = get_dashboard_stats()
    return render_template("index.html", stats=stats, current_user=_current_user_context())


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        errors = validate_registration(data)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html", data=data)

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (data["email"],)).fetchone()
        if existing:
            flash("Email already registered.", "danger")
            return render_template("register.html", data=data)

        conn.execute(
            "INSERT INTO users (full_name, email, password, phone, vehicle_number, vehicle_type, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data["full_name"],
                data["email"],
                hash_password(data["password"]),
                data.get("phone", ""),
                data.get("vehicle_number", ""),
                data.get("vehicle_type", "Sedan"),
                "user",
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html", current_user=_current_user_context())


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        errors = validate_login(request.form)
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("login.html", current_user=_current_user_context())

        conn = get_db()
        user_row = conn.execute("SELECT * FROM users WHERE email = ?", (request.form["email"],)).fetchone()
        if user_row and check_password(request.form["password"], user_row["password"]):
            user = User(user_row)
            login_user(user)
            session["user_id"] = user.id
            flash("Login successful.", "success")
            if user.role == "admin":
                return redirect(url_for("main.admin_dashboard"))
            return redirect(url_for("main.dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", current_user=_current_user_context())


@bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    slots = get_parking_slots({})
    recommendation = build_recommendation(current_user, slots, current_user.vehicle_type, False)
    prediction = build_prediction_summary()
    return render_template("dashboard.html", stats=stats, prediction=prediction, recommendation=recommendation, current_user=_current_user_context())


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "UPDATE users SET full_name = ?, phone = ?, vehicle_number = ?, vehicle_type = ? WHERE id = ?",
            (request.form.get("full_name"), request.form.get("phone", ""), request.form.get("vehicle_number", ""), request.form.get("vehicle_type", "Sedan"), current_user.id),
        )
        conn.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.profile"))
    user_row = get_db().execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
    return render_template("profile.html", current_user=user_row)


@bp.route("/parking")
@login_required
def parking():
    filters = {
        "status": request.args.get("status"),
        "block_name": request.args.get("block_name"),
        "floor": request.args.get("floor"),
    }
    slots = get_parking_slots(filters)
    recommendation = build_recommendation(current_user, slots, request.args.get("vehicle_type", current_user.vehicle_type), bool(request.args.get("requires_ev")))
    slots_json = [dict(s) for s in slots]
    for s in slots_json:
        try:
            s["qr_path"] = generate_qr_code(s["id"])
        except Exception:
            s["qr_path"] = None
    return render_template("parking.html", slots=slots, slots_json=slots_json, recommendation=recommendation, current_user=_current_user_context(), filters=filters)


@bp.route("/parking/<int:slot_id>")
@login_required
def parking_detail(slot_id):
    slot = get_db().execute("SELECT * FROM parking_slots WHERE id = ?", (slot_id,)).fetchone()
    if not slot:
        flash("Parking slot not found.", "danger")
        return redirect(url_for("main.parking"))
    qr_path = generate_qr_code(slot_id)
    return render_template("parking_detail.html", slot=slot, qr_path=qr_path, current_user=_current_user_context())


@bp.route("/slot/<slot_number>")
@login_required
def slot_detail(slot_number):
    slot = get_db().execute("SELECT * FROM parking_slots WHERE slot_number = ?", (slot_number,)).fetchone()
    if not slot:
        flash("Parking slot not found.", "danger")
        return redirect(url_for("main.parking"))
    qr_path = generate_qr_code(slot["id"])
    return render_template("parking_detail.html", slot=slot, qr_path=qr_path, current_user=_current_user_context())


@bp.route("/reserve/<int:slot_id>", methods=["POST"])
@login_required
def reserve_slot(slot_id):
    slot = get_db().execute("SELECT * FROM parking_slots WHERE id = ?", (slot_id,)).fetchone()
    if not slot:
        flash("Slot not found.", "danger")
        return redirect(url_for("main.parking"))
    if slot["status"] != "available":
        flash("This slot is not available for reservation.", "warning")
        return redirect(url_for("main.parking"))

    expiry_time = (datetime.now() + timedelta(minutes=15)).isoformat()
    create_reservation(current_user.id, slot_id, expiry_time)
    update_slot_status(slot_id, "reserved", current_user.id)
    _broadcast_update(f"Reservation confirmed for {slot['slot_number']}")
    flash("Reservation successful.", "success")
    return redirect(url_for("main.parking"))


@bp.route("/cancel-reservation/<int:slot_id>", methods=["POST"])
@login_required
def cancel_reservation(slot_id):
    conn = get_db()
    conn.execute("UPDATE reservations SET status='cancelled' WHERE slot_id = ? AND user_id = ? AND status='active'", (slot_id, current_user.id))
    conn.commit()
    update_slot_status(slot_id, "available")
    _broadcast_update("Reservation expired or cancelled")
    flash("Reservation cancelled.", "info")
    return redirect(url_for("main.parking"))


@bp.route("/occupy/<int:slot_id>", methods=["POST"])
@login_required
def occupy_slot(slot_id):
    slot = get_db().execute("SELECT * FROM parking_slots WHERE id = ?", (slot_id,)).fetchone()
    if not slot:
        flash("Slot not found.", "danger")
        return redirect(url_for("main.parking"))
    if slot["status"] == "occupied":
        flash("Slot is already occupied.", "warning")
        return redirect(url_for("main.parking"))

    update_slot_status(slot_id, "occupied", current_user.id)
    log_history(current_user.id, slot_id, datetime.now().isoformat(), vehicle_number=current_user.vehicle_number)
    _broadcast_update(f"Vehicle entered at {slot['slot_number']}")
    flash("Slot occupied successfully.", "success")
    return redirect(url_for("main.parking"))


@bp.route("/release/<int:slot_id>", methods=["POST"])
@login_required
def release_slot(slot_id):
    conn = get_db()
    history = conn.execute("SELECT * FROM parking_history WHERE slot_id = ? AND exit_time IS NULL ORDER BY id DESC LIMIT 1", (slot_id,)).fetchone()
    if not history:
        flash("No active parking session found.", "warning")
        return redirect(url_for("main.parking"))

    end_time = datetime.now()
    duration = calculate_duration(history["entry_time"], end_time)
    conn.execute("UPDATE parking_history SET exit_time = ?, duration = ? WHERE id = ?", (end_time.isoformat(), duration, history["id"]))
    conn.commit()
    update_slot_status(slot_id, "available")
    _broadcast_update(f"Vehicle exited from {slot_id}")
    flash("Slot released successfully.", "info")
    return redirect(url_for("main.parking"))


@bp.route("/history")
@login_required
def history():
    search = request.args.get("q", "")
    history_rows = get_history(current_user.id, search=search)
    return render_template("history.html", history=history_rows, current_user=_current_user_context(), q=search)


@bp.route("/scan-qr")
@login_required
def scan_qr():
    return render_template("scan_qr.html", current_user=_current_user_context())


@bp.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    stats = get_dashboard_stats()
    users = get_db().execute("SELECT * FROM users ORDER BY id DESC LIMIT 20").fetchall()
    slots = get_db().execute("SELECT * FROM parking_slots ORDER BY slot_number").fetchall()
    history_rows = get_history(search=request.args.get("q", ""))
    return render_template("admin_dashboard.html", stats=stats, users=users, slots=slots, history=history_rows, current_user=_current_user_context())


@bp.route("/admin/what-if")
@login_required
@admin_required
def admin_what_if():
    slots = get_parking_slots({})
    slots_json = [dict(s) for s in slots]
    return render_template("admin_what_if.html", slots_json=slots_json, current_user=_current_user_context())


@bp.route('/api/what-if/simulate', methods=['POST'])
@login_required
@admin_required
def api_what_if_simulate():
    data = request.get_json() or {}
    scenario = data.get('scenario')
    params = data.get('params', {})
    slots = get_parking_slots({})
    try:
        result = simulate_what_if(scenario or 'custom', params, [dict(s) for s in slots])
        return result
    except Exception as exc:
        return {"error": str(exc)}, 500


@bp.route('/replay')
@login_required
def replay():
    replay_payload = build_parking_replay()
    return render_template('replay.html', payload=replay_payload, current_user=_current_user_context())


@bp.route('/api/replay/data')
@login_required
def api_replay_data():
    return build_parking_replay()


@bp.route("/admin/slot/add", methods=["POST"])
@login_required
@admin_required
def add_slot():
    conn = get_db()
    slot_number = request.form.get("slot_number", "").strip()
    block_name = request.form.get("block_name", "").strip()
    floor = request.form.get("floor", "Ground Floor").strip()
    if slot_number and block_name:
        conn.execute(
            "INSERT INTO parking_slots (slot_number, block_name, floor, status, distance_from_entrance, ev_charging, priority, vehicle_size) VALUES (?, ?, ?, 'available', ?, ?, ?, ?)",
            (slot_number, block_name, floor, request.form.get("distance_from_entrance", 60), 1 if request.form.get("ev_charging") else 0, request.form.get("priority", 1), request.form.get("vehicle_size", "Sedan")),
        )
        conn.commit()
        _broadcast_update("A new slot was added by admin")
        flash("Parking slot added successfully.", "success")
    else:
        flash("Slot number and block name are required.", "danger")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/slot/delete/<int:slot_id>", methods=["POST"])
@login_required
@admin_required
def delete_slot(slot_id):
    conn = get_db()
    conn.execute("DELETE FROM parking_slots WHERE id = ?", (slot_id,))
    conn.commit()
    _broadcast_update("A parking slot was removed")
    flash("Parking slot deleted.", "info")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/slot/update/<int:slot_id>", methods=["POST"])
@login_required
@admin_required
def update_slot(slot_id):
    conn = get_db()
    conn.execute(
        "UPDATE parking_slots SET slot_number = ?, block_name = ?, floor = ?, status = ?, distance_from_entrance = ?, ev_charging = ?, priority = ?, vehicle_size = ? WHERE id = ?",
        (request.form.get("slot_number"), request.form.get("block_name"), request.form.get("floor"), request.form.get("status"), request.form.get("distance_from_entrance", 60), 1 if request.form.get("ev_charging") else 0, request.form.get("priority", 1), request.form.get("vehicle_size", "Sedan"), slot_id),
    )
    conn.commit()
    _broadcast_update("Slot details were updated")
    flash("Parking slot updated.", "success")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/users")
@login_required
@admin_required
def admin_users():
    term = request.args.get("q", "")
    users = search_users(term) if term else get_db().execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    return render_template("admin_users.html", users=users, q=term, current_user=_current_user_context())


@bp.route("/analytics")
@login_required
@admin_required
def analytics():
    payload = build_analytics_payload(get_db())
    return render_template("analytics.html", payload=payload, current_user=_current_user_context())


@bp.route("/api/analytics")
@login_required
@admin_required
def api_analytics():
    return {"payload": build_analytics_payload(get_db())}


@bp.route("/api/summary")
def api_summary():
    return {"stats": get_dashboard_stats()}


@bp.route('/api/ai/recommendation', methods=['GET', 'POST'])
def api_ai_recommendation():
    payload = request.get_json(silent=True) or {}
    intent = payload.get('intent') or request.args.get('intent', 'Nearest parking')
    vehicle_type = payload.get('vehicle_type') or (current_user.vehicle_type if current_user.is_authenticated else 'Sedan')
    requires_ev = bool(payload.get('requires_ev') or request.args.get('requires_ev'))
    slots = get_parking_slots({})
    return build_ai_recommendation_payload(intent, vehicle_type, requires_ev, [dict(slot) for slot in slots])


@bp.route('/api/predictions')
def api_predictions():
    return build_prediction_payload()


@bp.route('/api/city/status')
def api_city_status():
    return build_city_status_payload()


@bp.route('/api/demo/state')
def api_demo_state():
    return build_demo_mode_payload()


@bp.route("/api/slots")
def api_slots():
    slots = get_parking_slots({"status": request.args.get("status"), "block_name": request.args.get("block_name"), "floor": request.args.get("floor")})
    return {"slots": [dict(slot) for slot in slots]}


@bp.route("/prediction")
@login_required
def prediction():
    summary = build_prediction_summary()
    return render_template("prediction.html", prediction=summary, current_user=_current_user_context())


@bp.route("/chat", methods=["GET", "POST"])
def chat():
    history = session.get("chat_history") or []
    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        if user_message:
            slots = get_parking_slots({})
            reply = build_chat_reply(user_message, slots)
            history = list(history) + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]
            session["chat_history"] = history
        else:
            history = list(history) + [{"role": "assistant", "content": "Please enter a question so I can help."}]
    return render_template("chat.html", chat_history=history, current_user=_current_user_context())


@bp.route("/notifications")
def notifications():
    slots = get_parking_slots({})
    return render_template("notifications.html", notifications=get_notification_messages(slots), current_user=_current_user_context())


@bp.route("/ai-assistant")
def ai_assistant():
    slots = get_parking_slots({})
    try:
        vehicle_type = current_user.vehicle_type if current_user.is_authenticated else "Sedan"
    except:
        vehicle_type = "Sedan"
    response = build_ai_assistant_response(vehicle_type, False, slots)
    return render_template("ai_assistant.html", response=response, current_user=_current_user_context())


@bp.route("/ocr", methods=["GET", "POST"])
@login_required
def ocr_upload():
    result = None
    if request.method == "POST":
        if "image" not in request.files:
            flash("Please upload an image.", "warning")
            return render_template("ocr.html", current_user=_current_user_context())
        file = request.files["image"]
        if file.filename == "":
            flash("No file was selected.", "warning")
            return render_template("ocr.html", current_user=_current_user_context())
        upload_folder = os.path.join(os.path.dirname(__file__), "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        filename = secure_filename(file.filename)
        path = os.path.join(upload_folder, filename)
        file.save(path)
        result = get_ocr_result(path)
        if result.get("vehicle_number"):
            user_row = get_db().execute("SELECT * FROM users WHERE vehicle_number = ?", (result["vehicle_number"],)).fetchone()
            if user_row:
                flash(f"Recognized plate {result['vehicle_number']} and matched an existing user.", "success")
            else:
                flash("Plate recognized but no matching vehicle was found.", "warning")
        else:
            flash("OCR could not confidently read a plate number. Manual review is recommended.", "warning")
    return render_template("ocr.html", result=result, current_user=_current_user_context())


@bp.route("/report")
@login_required
def report():
    type_ = request.args.get("type", "daily")
    history_rows = get_history(current_user.id)
    return render_template("report.html", history=history_rows, type=type_, current_user=_current_user_context())


@bp.route("/export/history")
@login_required
def export_history():
    history_rows = get_history(current_user.id)
    output = export_history_to_csv(
        [
            {
                "full_name": row["full_name"],
                "vehicle_number": row["vehicle_number"],
                "slot_number": row["slot_number"],
                "entry_time": row["entry_time"],
                "exit_time": row["exit_time"],
                "duration": row["duration"],
            }
            for row in history_rows
        ]
    )
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=parking_history.csv"})


@socketio.on("connect")
def handle_connect():
    emit("parking_update", {"message": "Connected to live parking updates", "stats": get_dashboard_stats()})
    # Start a background updater to emit slot state and recent movements periodically
    try:
        if not getattr(handle_connect, "background_started", False):
            def background_slot_updater():
                from time import sleep

                last_history_id = 0
                while True:
                    try:
                        conn = get_db()
                        slots = get_parking_slots({})
                        slots_list = [dict(s) for s in slots]
                        for s in slots_list:
                            try:
                                s["qr_path"] = generate_qr_code(s["id"])
                            except Exception:
                                s["qr_path"] = None

                        # Recent movements in last 2 minutes
                        threshold = (datetime.now() - timedelta(minutes=2)).isoformat()
                        recent = conn.execute(
                            "SELECT ph.id, ph.user_id, ph.slot_id, ph.entry_time, ph.exit_time, ph.vehicle_number, s.slot_number FROM parking_history ph JOIN parking_slots s ON s.id = ph.slot_id WHERE ph.entry_time > ? OR (ph.exit_time IS NOT NULL AND ph.exit_time > ?) ORDER BY ph.id DESC LIMIT 50",
                            (threshold, threshold),
                        ).fetchall()
                        recent_list = [dict(r) for r in recent]
                        try:
                            reservations = get_reservations()
                            reservations_list = [dict(r) for r in reservations]
                        except Exception:
                            reservations_list = []
                        payload = {"message": "state", "stats": get_dashboard_stats(), "slots": slots_list, "recent_movements": recent_list, "reservations": reservations_list}
                        socketio.emit("parking_state", payload, broadcast=True)
                    except Exception:
                        pass
                    sleep(3)

            socketio.start_background_task(background_slot_updater)
            setattr(handle_connect, "background_started", True)
    except Exception:
        pass
