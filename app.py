
import os
from flask import Flask, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables from .env file
load_dotenv()

# Global scheduler instance
scheduler = BackgroundScheduler()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'a-default-fallback-secret-key'),
    )

    # --- Firebase Admin SDK Initialization ---
    try:
        if not firebase_admin._apps:
            cred_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
            if not os.path.exists(cred_path):
                raise FileNotFoundError("Firebase credentials file not found.")
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")

    except Exception as e:
        print(f"CRITICAL: Failed to initialize Firebase Admin SDK: {e}")

    # --- Register Blueprints ---
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from student.routes import student_bp
    from faculty.routes import faculty_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)

    # --- Register Jinja Filters ---
    from admin.utils import format_datetime
    app.jinja_env.filters['format_datetime'] = format_datetime

    # --- Initialize Scheduler for Automatic Jumma Pass Generation ---
    try:
        if not scheduler.running:
            from student.jumma_scheduler import schedule_jumma_pass_generation
            
            # Get the configured Jumma time from system settings
            db = firestore.client()
            settings_ref = db.collection('settings').document('system').get()
            
            if settings_ref.exists:
                settings = settings_ref.to_dict()
                jumma_time = settings.get('jumma_pass_start_time', '12:00')
            else:
                jumma_time = '12:00'  # Default to noon
            
            schedule_jumma_pass_generation(scheduler, jumma_time)
            scheduler.start()
            print(f"Background scheduler started. Jumma passes will be generated at {jumma_time} every Friday.")
    except Exception as e:
        print(f"Warning: Failed to initialize background scheduler: {e}")

    # --- Root URL Logic ---
    @app.route('/')
    def index():
        # Corrected redirect to point to the auth blueprint's main index view
        return redirect(url_for('auth.index'))

    return app
