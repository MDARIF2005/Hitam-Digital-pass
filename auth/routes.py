from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from firebase_admin import auth, firestore
import requests
import os

# Blueprint setup
auth_bp = Blueprint('auth', __name__, template_folder='templates', url_prefix='/auth')

@auth_bp.route('/')
def index():
    """Redirects to the appropriate dashboard if a user is logged in, otherwise to the login page."""
    if 'user_id' in session:
        user_role = session.get('user_role')
        if user_role == 'admin':
            return redirect(url_for('admin.index'))
        elif user_role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles login for all user roles and automatically determines their role."""
    if 'user_id' in session:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            api_key = os.getenv("FIREBASE_API_KEY")
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()

            id_token = response.json()['idToken']
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token['uid']

            db = firestore.client()
            roles_to_check = ['admins', 'faculty', 'students']
            user_role = None
            user_info = None
            is_main_admin_flag = False

            for role in roles_to_check:
                user_ref = db.collection(role).document(uid).get()
                if user_ref.exists:
                    user_role = role.rstrip('s')
                    user_info = user_ref.to_dict()
                    # Check for main admin status by role or name for backward compatibility
                    if user_role == 'admin' and (user_info.get('role') == 'main_admin' or user_info.get('name') == 'Main Admin'):
                        is_main_admin_flag = True
                    break
            
            if user_role and user_info:
                session['user_id'] = uid
                session['user_role'] = user_role
                session['user_info'] = user_info
                session['is_main_admin'] = is_main_admin_flag
                flash('Logged in successfully!', 'success')
                return redirect(url_for('auth.index'))
            else:
                flash('Your account is not assigned a role. Please contact an administrator.', 'danger')

        except requests.exceptions.HTTPError:
            flash('Invalid email or password.', 'danger')
        except auth.InvalidIdTokenError:
            flash('Invalid ID token.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        
        return redirect(url_for('auth.login'))

    return render_template('login.html', title="Login")

# Forgot-password routes removed: password resets are admin-only

@auth_bp.route('/logout')
def logout():
    """Logs the user out and clears the session."""
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
