import os
from flask import Flask
from firebase_admin import credentials, initialize_app

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # --- Configuration ---
    # Load secret key from environment variable
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_default_secret_key_for_development')

    # --- Firebase Admin SDK Initialization ---
    try:
        # Check if the app is already initialized
        if not initialize_app._apps:
            # Get the path to the service account key from environment variable
            cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "instance/firebase_credentials.json")
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)
        print("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")


    with app.app_context():
        # --- Blueprints ---
        from auth.routes import auth_bp
        from admin.routes import admin_bp
        from student.routes import student_bp
        from faculty.routes import faculty_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(student_bp)
        app.register_blueprint(faculty_bp)

        return app
