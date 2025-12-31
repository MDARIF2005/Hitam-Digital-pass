from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from firebase_admin import firestore, auth
from datetime import datetime
import uuid
from .jumma_scheduler import generate_automatic_jumma_passes

student_bp = Blueprint('student', __name__, url_prefix='/student', template_folder='templates')

# --- Decorators & Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# --- Routes ---

@student_bp.route('/dashboard')
@login_required
def dashboard():
    user_uid = session['user_id']
    db = firestore.client()
    student_data = {}
    system_settings = {}
    is_open = False
    closed_reason = "System settings could not be loaded."

    try:
        student_ref = db.collection('students').document(user_uid)
        student_doc = student_ref.get()
        if student_doc.exists:
            student_data = student_doc.to_dict()
        else:
            flash('Could not find your student profile.', 'danger')
            return redirect(url_for('auth.logout'))
    except Exception as e:
        flash(f"Error fetching your profile: {e}", "danger")
        return redirect(url_for('auth.logout'))

    try:
        settings_ref = db.collection('settings').document('system').get()
        if settings_ref.exists:
            system_settings = settings_ref.to_dict()
        
        # Check if pass application is open
        start_time_str = system_settings.get('student_pass_start_time', '00:00')
        end_time_str = system_settings.get('student_pass_end_time', '23:59')
        working_days = system_settings.get('student_working_days', [])
        today_str = datetime.now().strftime('%A')
        now = datetime.now().time()
        
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()

        if today_str not in working_days:
            is_open = False
            closed_reason = "Pass applications are only available on working days."
        elif not (start_time <= now <= end_time):
            is_open = False
            closed_reason = f"Gate pass requests are only accepted between {start_time_str} and {end_time_str}."
        else:
            is_open = True
            closed_reason = ""

    except Exception as e:
        flash(f"Error fetching system settings: {e}", "danger")

    return render_template('student/dashboard.html', 
                             student=student_data, 
                             settings=system_settings,
                             is_pass_application_open=is_open,
                             closed_reason=closed_reason)


@student_bp.route('/gate-pass', methods=['GET', 'POST'])
@login_required
def gate_pass():
    user_uid = session['user_id']
    db = firestore.client()
    student_data = {}
    existing_pass = None
    is_open = False
    closed_reason = "System settings could not be loaded."

    try:
        student_ref = db.collection('students').document(user_uid)
        student_doc = student_ref.get()
        if student_doc.exists:
            student_data = student_doc.to_dict()
        else:
            flash('Could not find your student profile.', 'danger')
            return redirect(url_for('auth.logout'))
    except Exception as e:
        flash(f"Error fetching your profile: {e}", "danger")
        return redirect(url_for('auth.logout'))

    approved_passes = []
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        passes_ref = db.collection('passes').where('applicant_id', '==', user_uid).where('date', '>=', today_start).stream()
        for p in passes_ref:
            existing_pass = p.to_dict()
            existing_pass['id'] = p.id
            break
    except Exception as e:
        flash(f"Error checking for existing passes: {e}", "danger")
    
    # Fetch all approved passes (all time) for this student
    try:
        all_passes = db.collection('passes').where('applicant_id', '==', user_uid).where('status', '==', 'approved').order_by('date', direction=firestore.Query.DESCENDING).stream()
        for p in all_passes:
            pass_data = p.to_dict()
            pass_data['id'] = p.id
            approved_passes.append(pass_data)
    except Exception as e:
        # Query might fail, which is fine
        pass

    # Check if pass application is open (within working hours/days)
    try:
        settings_ref = db.collection('settings').document('system').get()
        if settings_ref.exists:
            system_settings = settings_ref.to_dict()
            
            start_time_str = system_settings.get('student_pass_start_time', '00:00')
            end_time_str = system_settings.get('student_pass_end_time', '23:59')
            working_days = system_settings.get('student_working_days', [])
            today_str = datetime.now().strftime('%a')
            now = datetime.now().time()
            
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()

            if today_str not in working_days:
                is_open = False
                closed_reason = "Gate pass requests are only available on working days."
            elif not (start_time <= now <= end_time):
                is_open = False
                closed_reason = f"Gate pass requests are only accepted between {start_time_str} and {end_time_str}."
            else:
                is_open = True
                closed_reason = ""
    except Exception as e:
        flash(f"Error fetching system settings: {e}", "danger")

    if request.method == 'POST':
        if not is_open:
            flash(f"Gate pass requests are not available right now. {closed_reason}", "warning")
            return redirect(url_for('student.gate_pass'))

        if existing_pass:
            flash("You have already applied for a pass today.", "warning")
            return redirect(url_for('student.dashboard'))

        try:
            pass_data = {
                "pass_id": str(uuid.uuid4()),
                "applicant_id": user_uid,
                "applicant_name": student_data.get('name'),
                "applicant_type": "student",
                "roll_number": student_data.get('roll_number'),
                "department": student_data.get('branch'),
                "academic_year": student_data.get('academic_year'),
                    "pass_out_year": student_data.get('pass_out_year'),
                    "pass_type": request.form.get('pass_type'),
                "reason": request.form.get('reason'),
                "date": firestore.SERVER_TIMESTAMP,
                "out_time": datetime.now().strftime('%H:%M'),
                "status": "pending",
                "approvals": [
                    {'role': f"mentor_{student_data.get('academic_year')}_{student_data.get('branch')}_{student_data.get('section')}", 'status': 'pending'},
                    {'role': f"hod_{student_data.get('branch')}", 'status': 'pending'}
                ],
                "current_approver": f"mentor_{student_data.get('academic_year')}_{student_data.get('branch')}_{student_data.get('section')}"
            }
            db.collection('passes').document(pass_data['pass_id']).set(pass_data)
            flash("Your pass has been submitted successfully!", "success")
            return redirect(url_for('student.dashboard'))
        except Exception as e:
            flash(f"An error occurred while submitting your pass: {e}", "danger")

    return render_template('student/gate_pass.html', 
                         student=student_data, 
                         existing_pass=existing_pass,
                         approved_passes=approved_passes,
                         is_pass_application_open=is_open,
                         closed_reason=closed_reason)


@student_bp.route('/profile')
@login_required
def profile():
    user_uid = session['user_id']
    db = firestore.client()
    student_data = {}

    try:
        student_ref = db.collection('students').document(user_uid)
        student_doc = student_ref.get()
        if student_doc.exists:
            student_data = student_doc.to_dict()
        else:
            flash('Could not find your student profile.', 'danger')
            return redirect(url_for('auth.logout'))
    except Exception as e:
        flash(f"Error fetching your profile: {e}", "danger")
        return redirect(url_for('auth.logout'))

    return render_template('student/profile.html', student=student_data)


@student_bp.route('/generate-jumma-passes', methods=['POST'])
@login_required
def trigger_jumma_pass_generation():
    """
    Manual trigger for Jumma pass generation (for testing/admin purposes).
    This endpoint manually generates Jumma passes for eligible students.
    """
    # Check if user is admin (has access to this function)
    user_uid = session['user_id']
    db = firestore.client()
    
    try:
        user_ref = db.collection('users').document(user_uid).get()
        if not user_ref.exists:
            flash("Unauthorized access", "danger")
            return redirect(url_for('student.dashboard'))
        
        user_data = user_ref.to_dict()
        if user_data.get('role') != 'admin':
            flash("Only administrators can trigger Jumma pass generation", "danger")
            return redirect(url_for('student.dashboard'))
    except:
        # User is student, not admin - proceed (can be called by admin or scheduler)
        pass
    
    # Generate Jumma passes
    result = generate_automatic_jumma_passes()
    
    if result.get('status') == 'success':
        flash(f"Successfully generated {result.get('generated', 0)} Jumma passes!", "success")
    elif result.get('status') == 'disabled':
        flash("Automatic Jumma pass generation is disabled in system settings", "warning")
    else:
        flash(f"Error: {result.get('message', 'Unknown error')}", "danger")
    
    return redirect(url_for('student.dashboard'))

