from flask import Flask

from config import Config
from models import close_db, init_db
from routes import bp, login_manager, socketio


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    login_manager.init_app(app)
    app.register_blueprint(bp)
    socketio.init_app(app, cors_allowed_origins="*")

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    return app


app = create_app()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
