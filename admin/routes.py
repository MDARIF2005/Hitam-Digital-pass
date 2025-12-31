import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, session
from firebase_admin import auth, firestore, storage
from admin.utils import send_password_reset_email
from firebase_admin.auth import EmailAlreadyExistsError
import io
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from functools import wraps
import json

logging.basicConfig(level=logging.INFO)

admin_bp = Blueprint(
    'admin',
    __name__,
    url_prefix='/admin',
    template_folder='templates',
    static_folder='static'
)

def get_db():
    return firestore.client()

# --- Image Upload Helper ---
def _upload_image(file, item_type, item_id):
    if not file:
        return None
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f'{item_type}/{item_id}/{file.filename}')
        blob.upload_from_file(file, content_type=file.content_type)
        return blob.public_url
    except Exception as e:
        flash(f"Error uploading image: {e}", "danger")
        return None

# --- Authorization ---
def is_main_admin():
    return session.get('is_main_admin', False)

def main_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_main_admin():
            flash("This action requires main administrator privileges.", "danger")
            return redirect(request.referrer or url_for('admin.index'))
        return f(*args, **kwargs)
    return decorated_function
    
@admin_bp.route('/add/<item_type>', methods=['GET', 'POST'])
def add_item(item_type):
    if item_type == 'user':
        # logic for adding user
        pass
    elif item_type == 'faculty':
        # logic for adding faculty
        pass
    # ...
    pass


@admin_bp.route('/')
def index():
    db = get_db()
    try:
        students_count = len(list(db.collection('students').stream()))
        faculty_count = len(list(db.collection('faculty').stream()))
        admins_count = len(list(db.collection('admins').stream()))
        # Temporarily simplified queries to avoid index errors
        stats_cards = {
            "total_students": students_count,
            "total_faculty": faculty_count,
            "total_admins": admins_count,
            "total_passes": {"pending": 0, "approved": 0, "rejected": 0}
        }
        pass_trends = {'labels': [], 'data': []}
        department_chart_data = {'labels': [], 'datasets': []}
        activity_feed = []
    except Exception as e:
        flash(f"Error fetching dashboard data: {e}", "danger")
        logging.error(f"Dashboard Error: {e}")
        stats_cards = {"total_students": 0, "total_faculty": 0, "total_passes": {"pending": 0, "approved": 0, "rejected": 0}, "total_admins": 0}
        pass_trends = {'labels': [], 'data': []}
        department_chart_data = {'labels': [], 'datasets': []}
        activity_feed = []

    return render_template('dashboard.html', stats_cards=stats_cards, pass_trends=pass_trends, department_chart_data=department_chart_data, activity_feed=activity_feed)


@admin_bp.route('/manage-students', methods=['GET', 'POST'])
def manage_students():
    db = get_db()
    students_query = db.collection('students')
    try:
        students_docs = students_query.stream()
        students = [{**doc.to_dict(), 'id': doc.id} for doc in students_docs]
    except Exception as e:
        flash(f"Error fetching students: {e}", "danger")
        students = []
    
    try:
        roles_docs = db.collection('roles').stream()
        roles = [{**doc.to_dict(), "role_id": doc.id} for doc in roles_docs]
    except Exception as e:
        flash(f"Error fetching roles: {e}", "danger")
        roles = []
        
    return render_template('manage_students.html', students=students, roles=roles)


@admin_bp.route('/manage-faculty', methods=['GET', 'POST'])
def manage_faculty():
    db = get_db()
    faculty_query = db.collection('faculty')
    try:
        faculty_docs = faculty_query.stream()
        faculty = [{**doc.to_dict(), 'id': doc.id} for doc in faculty_docs]
    except Exception as e:
        flash(f"Error fetching faculty: {e}", "danger")
        faculty = []
    
    try:
        roles_docs = db.collection('roles').stream()
        roles = [{**doc.to_dict(), "role_id": doc.id} for doc in roles_docs]
    except Exception as e:
        flash(f"Error fetching roles: {e}", "danger")
        roles = []
        
    return render_template('manage_faculty.html', faculty=faculty, roles=roles)


@admin_bp.route('/manage-admins', methods=['GET'])
@main_admin_required
def manage_admins():
    db = get_db()
    try:
        admins_docs = db.collection('admins').stream()
        admins = [{**doc.to_dict(), 'id': doc.id} for doc in admins_docs]
    except Exception as e:
        flash(f"Error fetching admins: {e}", "danger")
        admins = []
    return render_template('manage_admins.html', admins=admins)

@admin_bp.route('/roles-settings', methods=['GET'])
@main_admin_required
def roles_settings():
    db = get_db()
    try:
        roles_docs = db.collection('roles').order_by("priority").stream()
        roles = {
            "student_pass": [],
            "faculty_pass": [],
            "head_approval": []
        }
        all_roles = []
        for doc in roles_docs:
            role_data = {**doc.to_dict(), 'role_id': doc.id}
            all_roles.append(role_data)
            approval_type = role_data.get('approval_type')
            if approval_type in roles:
                roles[approval_type].append(role_data)
    except Exception as e:
        flash(f"Error fetching roles: {e}", "danger")
        roles = {}
        all_roles = []
    return render_template('roles_settings.html', roles=roles, all_roles=all_roles)


@admin_bp.route('/system-settings', methods=['GET', 'POST'])
@main_admin_required
def system_settings():
    db = get_db()
    settings_ref = db.collection('settings').document('system')
    if request.method == 'POST':
        try:
            settings_data = {
                'institute_name': request.form.get('institute_name'),
                'institute_logo': request.form.get('institute_logo'),
                'theme_mode': request.form.get('theme_mode'),
                'notifications_enabled': 'notifications_enabled' in request.form,
                'email_alerts_enabled': 'email_alerts_enabled' in request.form,
                'auto_jumma_pass_enabled': 'auto_jumma_pass_enabled' in request.form,
                'student_working_days': request.form.getlist('student_working_days'),
                'faculty_working_days': request.form.getlist('faculty_working_days'),
                'student_pass_start_time': request.form.get('student_pass_start_time'),
                'student_pass_end_time': request.form.get('student_pass_end_time'),
                'faculty_pass_start_time': request.form.get('faculty_pass_start_time'),
                'faculty_pass_end_time': request.form.get('faculty_pass_end_time'),
                'jumma_pass_start_time': request.form.get('jumma_pass_start_time'),
                'jumma_pass_end_time': request.form.get('jumma_pass_end_time'),
                'auto_approve_absent_faculty': 'auto_approve_absent_faculty' in request.form,
            }
            settings_ref.set(settings_data, merge=True)
            flash("System settings updated successfully!", "success")
        except Exception as e:
            flash(f"Error updating settings: {e}", "danger")
        return redirect(url_for('admin.system_settings'))

    try:
        settings = settings_ref.get().to_dict() or {}
    except Exception as e:
        flash(f"Error fetching settings: {e}", "danger")
        settings = {}
    return render_template('system_settings.html', settings=settings)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@main_admin_required
def settings():
    """Render the more detailed settings page used for Jumma pass and other nested settings.
    This endpoint backs the `admin/templates/settings.html` template which posts to `admin.settings`.
    """
    db = get_db()
    settings_ref = db.collection('settings').document('system')

    if request.method == 'POST':
        try:
            # Load current settings, update nested fields from form
            current = settings_ref.get().to_dict() or {}
            student = current.get('student', {})
            faculty = current.get('faculty', {})

            if request.form.get('student_start_time'):
                student['start_time'] = request.form.get('student_start_time')
            if request.form.get('student_end_time'):
                student['end_time'] = request.form.get('student_end_time')
            if request.form.get('faculty_start_time'):
                faculty['start_time'] = request.form.get('faculty_start_time')
            if request.form.get('faculty_end_time'):
                faculty['end_time'] = request.form.get('faculty_end_time')

            # Jumma pass toggle
            current['jumma_pass_enabled'] = 'jumma_pass_enabled' in request.form

            current['student'] = student
            current['faculty'] = faculty

            settings_ref.set(current, merge=True)
            flash("Settings saved successfully!", "success")
        except Exception as e:
            flash(f"Error saving settings: {e}", "danger")
        return redirect(url_for('admin.settings'))

    try:
        settings = settings_ref.get().to_dict() or {}
    except Exception as e:
        flash(f"Error fetching settings: {e}", "danger")
        settings = {}

    return render_template('settings.html', settings=settings, title='System Settings')

@admin_bp.route('/pass-overview', methods=['GET'])
def pass_overview():
    db = get_db()
    passes_query = db.collection_group('passes')
    try:
        passes_docs = passes_query.order_by('date', direction=firestore.Query.DESCENDING).stream()
        passes = [{**p.to_dict(), 'id': p.id} for p in passes_docs]
    except Exception as e:
        flash(f"Error fetching passes: {e}", "danger")
        passes = []
    return render_template('pass_overview.html', passes=passes)

@admin_bp.route('/notifications', methods=['GET', 'POST'])
@main_admin_required
def notifications():
    db = get_db()
    if request.method == 'POST':
        try:
            target = request.form.get('target')
            message = request.form.get('message')
            db.collection('notifications').add({
                'message': message,
                'target': target,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            flash("Notification sent successfully!", "success")
        except Exception as e:
            flash(f"Error sending notification: {e}", "danger")
        return redirect(url_for('admin.notifications'))

    try:
        notifications_docs = db.collection('notifications').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        notifications = [doc.to_dict() for doc in notifications_docs]
    except Exception as e:
        flash(f"Error fetching notifications: {e}", "danger")
        notifications = []
    return render_template('notifications.html', notifications=notifications)

# --- Bulk Upload ---
@admin_bp.route('/bulk-upload/<item_type>', methods=['GET', 'POST'])
@main_admin_required
def bulk_upload(item_type):
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash("No file selected.", "danger")
            return redirect(request.url)

        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                flash("Invalid file type. Please upload a CSV or XLSX file.", "danger")
                return redirect(request.url)

            process_bulk_upload(df, item_type)

        except Exception as e:
            flash(f"An error occurred during bulk upload: {e}", "danger")
            logging.error(f"BULK UPLOAD ERROR: {e}")
        
        return redirect(url_for(f'admin.manage_{item_type}'))

    return render_template('bulk_upload.html', item_type=item_type)

def process_bulk_upload(df, item_type):
    db = get_db()
    collection_name = item_type
    required_fields = []
    # Password is optional in uploads; we'll provide sensible defaults when missing
    if item_type == 'students':
        required_fields = ['name', 'email', 'roll_number', 'branch', 'section', 'academic_year']
    elif item_type == 'faculty':
        # faculty_id is optional but helpful to derive a default password
        required_fields = ['name', 'email', 'department']

    if not all(field in df.columns for field in required_fields):
        missing = [field for field in required_fields if field not in df.columns]
        flash(f"Missing required columns in the uploaded file: {', '.join(missing)}", "danger")
        return

    success_count = 0
    error_count = 0
    for index, row in df.iterrows():
        try:
            email = row['email']
            name = row['name']
            # choose password: prefer provided, otherwise sensible defaults
            if 'password' in row and pd.notna(row.get('password')):
                password = str(row['password'])
            else:
                if item_type == 'students':
                    password = 'Hitam@123'
                elif item_type == 'faculty':
                    # prefer faculty_id column if present
                    faculty_id_val = row.get('faculty_id') if 'faculty_id' in row else None
                    password = str(faculty_id_val) if faculty_id_val and pd.notna(faculty_id_val) else 'Hitam@123'

            try:
                user = auth.create_user(email=email, password=password, display_name=name)
                item_id = user.uid
            except EmailAlreadyExistsError:
                logging.warning(f"Email {email} already exists. Skipping Auth creation.")
                user = auth.get_user_by_email(email)
                item_id = user.uid

            if item_type == 'students':
                data = _build_student_data_from_row(row)
            elif item_type == 'faculty':
                data = _build_faculty_data_from_row(row)
            
            db.collection(collection_name).document(item_id).set(data, merge=True)
            success_count += 1

        except Exception as e:
            error_count += 1
            logging.error(f"Error processing row {index + 2}: {e}")

    flash(f"Bulk upload complete! {success_count} records processed, {error_count} errors.", "success" if error_count == 0 else "warning")

def _build_student_data_from_row(row):
    data = {
        "name": row.get('name'),
        "email": row.get('email'),
        "roll_number": row.get('roll_number'),
        "branch": row.get('branch'),
        "section": row.get('section'),
        "gender": row.get('gender'),
        "religion": row.get('religion'),
        "phone": row.get('phone'),
        "created_at": firestore.SERVER_TIMESTAMP
    }

    academic_year_str = row.get('academic_year')
    if academic_year_str:
        try:
            start_year = str(academic_year_str).split('-')[0].strip()
            data['academic_year'] = int(start_year)
        except (ValueError, IndexError):
            data['academic_year'] = None
    else:
        data['academic_year'] = None
    
    # Add pass_out_year from bulk upload
    pass_out_year_str = row.get('pass_out_year')
    if pass_out_year_str:
        try:
            data['pass_out_year'] = int(pass_out_year_str)
        except (ValueError, TypeError):
            data['pass_out_year'] = None
    else:
        data['pass_out_year'] = None
        
    parents = []
    if row.get('parent1_name'):
        parents.append({
            "name": row.get('parent1_name'),
            "email": row.get('parent1_email'),
            "phone": row.get('parent1_phone'),
        })
    if row.get('parent2_name'):
        parents.append({
            "name": row.get('parent2_name'),
            "email": row.get('parent2_email'),
            "phone": row.get('parent2_phone'),
        })
    data['parents'] = parents
    
    return data

def _build_faculty_data_from_row(row):
    data = {
        "name": row.get('name'),
        "email": row.get('email'),
        "phone": row.get('phone'),
        "department": row.get('department'),
        "faculty_id": row.get('faculty_id'),
        "gender": row.get('gender'),
        "religion": row.get('religion'),
        "status": row.get('status', 'present'),
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    if 'assigned_roles' in row and pd.notna(row['assigned_roles']):
      try:
          roles_json = row.get('assigned_roles', '[]')
          data["assigned_roles"] = json.loads(roles_json)
      except (json.JSONDecodeError, TypeError):
          data["assigned_roles"] = []
          logging.warning(f"Could not parse assigned_roles for {row.get('email')}. Setting to empty.")
    else:
        data["assigned_roles"] = []
    return data

# --- CRUD Operations ---
def _build_student_data(form, item_id=None):
    data = {
        "name": form.get('name'),
        "email": form.get('email'),
        "roll_number": form.get('roll_number'),
        "branch": form.get('branch'),
        "section": form.get('section'),
        "gender": form.get('gender'),
        "religion": form.get('religion'),
        "phone": form.get('phone'),
        "image_url": form.get('image_url'),
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    if not item_id:
        data['created_at'] = firestore.SERVER_TIMESTAMP

    academic_year_str = form.get('academic_year')
    if academic_year_str:
        try:
            start_year = academic_year_str.split('-')[0].strip()
            data['academic_year'] = int(start_year)
        except (ValueError, IndexError):
            data['academic_year'] = None
    else:
        data['academic_year'] = None
    
    # Add pass_out_year field
    pass_out_year_str = form.get('pass_out_year')
    if pass_out_year_str:
        try:
            data['pass_out_year'] = int(pass_out_year_str)
        except ValueError:
            data['pass_out_year'] = None
    else:
        data['pass_out_year'] = None

    parents = []
    if form.get('parent1_name'):
        parents.append({
            "name": form.get('parent1_name'),
            "email": form.get('parent1_email'),
            "phone": form.get('parent1_phone'),
        })
    if form.get('parent2_name'):
        parents.append({
            "name": form.get('parent2_name'),
            "email": form.get('parent2_email'),
            "phone": form.get('parent2_phone'),
        })
    data['parents'] = parents

    return data

def _build_faculty_data(form, item_id=None):
    db = get_db()
    data = {
        "name": form.get('name'),
        "email": form.get('email'),
        "phone": form.get('phone'),
        "department": form.get('department'),
        "gender": form.get('gender'),
        "religion": form.get('religion'),
        "faculty_id": form.get('faculty_id'),
        "status": form.get('status', 'present'),
        "image_url": form.get('image_url'),
        "updated_at": firestore.SERVER_TIMESTAMP
    }
    if not item_id:
        data['created_at'] = firestore.SERVER_TIMESTAMP

    assigned_roles_data = []
    try:
        assigned_roles_json = form.getlist('assigned_roles')
        for role_json_str in assigned_roles_json:
            role_data = json.loads(role_json_str)
            role_id = role_data.get('role_id')
            
            if not role_id:
                continue

            role_ref = db.collection('roles').document(role_id)
            role_doc = role_ref.get()
            if not role_doc.exists:
                continue
                
            role_details = role_doc.to_dict()
            role_name = role_details.get('role_name')

            final_role_obj = {
                "role_id": role_id,
                "role_name": role_name,
                "approval_type": role_details.get('approval_type'),
                "fallback_roles": role_details.get('fallback_roles', [])
            }

            if role_name in ["Teacher", "Mentor"] and 'mapping' in role_data:
                if not all(role_data['mapping'].values()):
                    flash(f"Mapping for {role_name} is incomplete.", "danger")
                    continue
                final_role_obj["mapping"] = role_data['mapping']
            
            assigned_roles_data.append(final_role_obj)

    except json.JSONDecodeError:
        flash("Error decoding role data. Please check the format.", "danger")
    except Exception as e:
        flash(f"An error occurred while processing roles: {e}", "danger")
    
    data["assigned_roles"] = assigned_roles_data
    return data

@admin_bp.route('/add/user/<role>', methods=['GET', 'POST'])
def add_user(role):
    if request.method == 'GET':
        return render_template('add_user.html', role=role)

    db = get_db()
    # Normalize collection names: 'faculty' collection is named 'faculty' (not 'facultys')
    collection_map = {
        'faculty': 'faculty',
        'student': 'students',
        'admin': 'admins'
    }
    collection_name = collection_map.get(role, (role + 's') if not role.endswith('s') else role)
    
    try:
        if role == 'student':
            data = _build_student_data(request.form)
        elif role == 'faculty':
            data = _build_faculty_data(request.form)
        else:
            flash("Invalid user role.", "danger")
            return redirect(url_for('admin.index'))

        # Provide default passwords when not supplied:
        # - Students: default to 'Hitam@123'
        # - Faculty: default to provided faculty_id (if present) else 'Hitam@123'
        password = request.form.get('password')
        if not password:
            if role == 'student':
                password = 'Hitam@123'
            elif role == 'faculty':
                password = request.form.get('faculty_id') or 'Hitam@123'

        try:
            user = auth.create_user(email=data['email'], password=password, display_name=data.get('name'))
            item_id = user.uid
        except EmailAlreadyExistsError:
            flash(f"A user with email {data['email']} already exists.", "danger")
            return render_template('add_user.html', role=role, user=request.form)

        image_file = request.files.get('image')
        if image_file:
            data['image_url'] = _upload_image(image_file, collection_name, item_id)
        
        db.collection(collection_name).document(item_id).set(data)
        flash(f"{role.capitalize()} added successfully!", "success")

    except Exception as e:
        flash(f"Error adding {role}: {e}", "danger")
        logging.error(f"ADD {role.upper()} ERROR: {e}")
        return render_template('add_user.html', role=role, user=request.form)

    return redirect(url_for(f'admin.manage_{collection_name}'))


@admin_bp.route('/edit/student/<item_id>', methods=['POST'])
def edit_student(item_id):
    db = get_db()
    try:
        data = _build_student_data(request.form, item_id=item_id)
        
        auth_updates = {'display_name': data.get('name')}
        if request.form.get('password'):
            auth_updates['password'] = request.form.get('password')
        else:
            # If admin left password blank while editing, reset student password to default
            auth_updates['password'] = 'Hitam@123'
        
        original_doc = db.collection('students').document(item_id).get()
        if original_doc.exists:
            original_email = original_doc.to_dict().get('email')
            if data.get('email') != original_email:
                auth_updates['email'] = data.get('email')
        
        password_used = auth_updates.get('password')
        if len(auth_updates) > 1 or 'email' in auth_updates:
            auth.update_user(item_id, **auth_updates)
            # attempt to send notification email about password reset; ignore failures
            try:
                send_password_reset_email(data.get('email'), password_used, data.get('name'))
            except Exception:
                pass

        image_file = request.files.get('image')
        if image_file:
            data['image_url'] = _upload_image(image_file, 'students', item_id)
        
        db.collection('students').document(item_id).set(data, merge=True)
        flash("Student updated successfully!", "success")

    except Exception as e:
        flash(f"Error updating student: {e}", "danger")
        logging.error(f"EDIT STUDENT ERROR: {e}")

    return redirect(url_for('admin.manage_students'))

@admin_bp.route('/edit/faculty/<item_id>', methods=['POST'])
def edit_faculty(item_id):
    db = get_db()
    try:
        data = _build_faculty_data(request.form, item_id=item_id)
        
        auth_updates = {'display_name': data.get('name')}
        if request.form.get('password'):
            auth_updates['password'] = request.form.get('password')
        
        original_doc = db.collection('faculty').document(item_id).get()
            # Get faculty_id for password reset
        faculty_id = data.get('faculty_id')
        
        if original_doc.exists:
            original_email = original_doc.to_dict().get('email')
            if data.get('email') != original_email:
                auth_updates['email'] = data.get('email')
        
            # If password field is empty but faculty_id exists, use faculty_id as password
            if not request.form.get('password') and faculty_id:
                auth_updates['password'] = faculty_id
        
        password_used = auth_updates.get('password')
        if len(auth_updates) > 1 or 'email' in auth_updates:
            auth.update_user(item_id, **auth_updates)
            try:
                send_password_reset_email(data.get('email'), password_used, data.get('name'))
            except Exception:
                pass

        image_file = request.files.get('image')
        if image_file:
            data['image_url'] = _upload_image(image_file, 'faculty', item_id)
        
        db.collection('faculty').document(item_id).set(data, merge=True)
        flash("Faculty member updated successfully!", "success")

    except Exception as e:
        flash(f"Error updating faculty member: {e}", "danger")
        logging.error(f"EDIT FACULTY ERROR: {e}")

    return redirect(url_for('admin.manage_faculty'))


@admin_bp.route('/delete/<item_type>/<item_id>', methods=['POST'])
def delete_item(item_type, item_id):
    db = get_db()
    try:
        if item_type in ['faculty', 'students', 'admins']:
            try:
                auth.delete_user(item_id)
            except auth.UserNotFoundError:
                logging.warning(f"User with ID {item_id} not found in Auth, but proceeding with Firestore deletion.")
        
        db.collection(item_type).document(item_id).delete()
        flash(f"{item_type.capitalize()} deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting {item_type}: {e}", "danger")
        logging.error(f"DELETE {item_type.upper()} ERROR: {e}")
    
    return redirect(url_for(f'admin.manage_{item_type}'))

@admin_bp.route('/reset-password/faculty/<item_id>', methods=['POST'])
def reset_faculty_password(item_id):
    db = get_db()
    try:
        doc_ref = db.collection('faculty').document(item_id)
        doc = doc_ref.get()
        if not doc.exists:
            flash("Faculty member not found.", "danger")
            return redirect(url_for('admin.manage_faculty'))
        data = doc.to_dict()
        faculty_id_val = data.get('faculty_id')
        email = data.get('email')
        if not faculty_id_val:
            flash("Faculty ID is not set for this member; cannot reset password.", "danger")
            return redirect(url_for('admin.manage_faculty'))
        try:
            auth.update_user(item_id, password=str(faculty_id_val))
            flash("Password reset to Faculty ID successfully.", "success")
            try:
                send_password_reset_email(email, str(faculty_id_val), data.get('name'))
            except Exception:
                pass
            try:
                db.collection('audit').add({
                    'type': 'password_reset',
                    'target_id': item_id,
                    'admin_id': session.get('user_id'),
                    'method': 'reset_to_faculty_id',
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            except Exception:
                pass
        except Exception as e:
            flash(f"Error resetting password: {e}", "danger")
            logging.error(f"RESET FACULTY PASSWORD ERROR: {e}")
    except Exception as e:
        flash(f"Error accessing faculty data: {e}", "danger")
        logging.error(f"RESET FACULTY FETCH ERROR: {e}")
    return redirect(url_for('admin.manage_faculty'))


@admin_bp.route('/reset-password/student/<item_id>', methods=['POST'])
def reset_student_password(item_id):
    db = get_db()
    try:
        doc_ref = db.collection('students').document(item_id)
        doc = doc_ref.get()
        if not doc.exists:
            flash("Student not found.", "danger")
            return redirect(url_for('admin.manage_students'))
        data = doc.to_dict()
        email = data.get('email')
        default_password = 'Hitam@123'
        try:
            auth.update_user(item_id, password=default_password)
            flash("Password reset to default (Hitam@123) successfully.", "success")
            try:
                send_password_reset_email(email, default_password, data.get('name'))
            except Exception:
                pass
            try:
                db.collection('audit').add({
                    'type': 'password_reset',
                    'target_id': item_id,
                    'admin_id': session.get('user_id'),
                    'method': 'reset_to_default',
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
            except Exception:
                pass
        except Exception as e:
            flash(f"Error resetting password: {e}", "danger")
            logging.error(f"RESET STUDENT PASSWORD ERROR: {e}")
    except Exception as e:
        flash(f"Error accessing student data: {e}", "danger")
        logging.error(f"RESET STUDENT FETCH ERROR: {e}")
    return redirect(url_for('admin.manage_students'))


@admin_bp.route('/add/role', methods=['POST'])
@main_admin_required
def add_role():
    db = get_db()
    try:
        fallback_roles = request.form.getlist('fallback_roles')
        role_data = {
            "role_name": request.form.get('role_name'),
            "approval_type": request.form.get('approval_type'),
            "priority": int(request.form.get('priority', 99)),
            "fallback_roles": fallback_roles,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        db.collection('roles').add(role_data)
        flash("Role added successfully!", "success")
    except Exception as e:
        flash(f"Error adding role: {e}", "danger")
    return redirect(url_for('admin.roles_settings'))

@admin_bp.route('/edit/role/<role_id>', methods=['POST'])
@main_admin_required
def edit_role(role_id):
    db = get_db()
    try:
        fallback_roles = request.form.getlist('fallback_roles')
        role_data = {
            "role_name": request.form.get('role_name'),
            "approval_type": request.form.get('approval_type'),
            "priority": int(request.form.get('priority', 99)),
            "fallback_roles": fallback_roles
        }
        db.collection('roles').document(role_id).set(role_data, merge=True)
        flash("Role updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating role: {e}", "danger")
    return redirect(url_for('admin.roles_settings'))
