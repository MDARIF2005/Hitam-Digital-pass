
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from firebase_admin import firestore, auth

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty', template_folder='templates')


@faculty_bp.route('/dashboard', endpoint='dashboard')
def dashboard():
    if 'user_uid' not in session:
        flash('Please log in to access your dashboard.', 'danger')
        return redirect(url_for('auth.login'))

    db = firestore.client()
    user_uid = session['user_uid']

    try:
        user_ref = db.collection('faculty').document(user_uid)
        user_doc = user_ref.get()
        if not user_doc.exists:
            flash('Could not find your user profile.', 'danger')
            return redirect(url_for('auth.logout'))
        user = user_doc.to_dict()

        # Fetch passes this faculty member needs to approve
        assigned_student_roles = user.get('assigned_student_roles', [])
        assigned_faculty_roles = user.get('assigned_faculty_roles', [])
        assigned_head_roles = user.get('assigned_head_roles', [])

        pending_passes = {
            'student': [],
            'faculty': [],
            'head': []
        }

        def fetch_passes(role_ids, pass_type):
            if not role_ids:
                return
            passes_ref = db.collection('passes').where('current_approver', 'in', role_ids).where('status', '==', 'pending').stream()
            for p in passes_ref:
                pass_data = p.to_dict()
                pass_data['id'] = p.id

                # Get applicant details
                applicant_ref = db.collection('students').document(pass_data['applicant_id']).get()
                if not applicant_ref.exists:
                    applicant_ref = db.collection('faculty').document(pass_data['applicant_id']).get()
                
                if applicant_ref.exists:
                    applicant_data = applicant_ref.to_dict()
                    pass_data['applicant_name'] = applicant_data.get('name', 'N/A')
                    pass_data['applicant_roll'] = applicant_data.get('roll_number', 'N/A')
                    pass_data['department'] = applicant_data.get('branch', applicant_data.get('department', 'N/A'))
                    pass_data['academic_year'] = applicant_data.get('academic_year', 'N/A')
                else:
                    pass_data['applicant_name'] = 'N/A'
                    pass_data['applicant_roll'] = 'N/A'
                    pass_data['department'] = 'N/A'
                    pass_data['academic_year'] = 'N/A'

                pending_passes[pass_type].append(pass_data)

        fetch_passes(assigned_student_roles, 'student')
        fetch_passes(assigned_faculty_roles, 'faculty')
        fetch_passes(assigned_head_roles, 'head')

        # Fetch personal passes
        personal_passes_ref = db.collection('passes').where('applicant_id', '==', user_uid).stream()
        personal_passes = [p.to_dict() for p in personal_passes_ref]

    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        pending_passes = {'student': [], 'faculty': [], 'head': []}
        personal_passes = []
        user = {}

    return render_template('faculty/dashboard.html', user=user, pending_passes=pending_passes, personal_passes=personal_passes)


@faculty_bp.route('/process_pass/<pass_id>/<action>', methods=['POST'], endpoint='process_pass')
def process_pass(pass_id, action):
    if 'user_uid' not in session:
        return redirect(url_for('auth.login'))

    db = firestore.client()
    user_uid = session['user_uid']
    pass_ref = db.collection('passes').document(pass_id)

    try:
        pass_doc = pass_ref.get()
        if not pass_doc.exists:
            flash('Pass not found.', 'danger')
            return redirect(url_for('faculty.dashboard'))

        pass_data = pass_doc.to_dict()
        current_approver_role = pass_data.get('current_approver')
        approvals = pass_data.get('approvals', [])

        # Find the index of the current approval step
        current_approval_index = -1
        for i, approval in enumerate(approvals):
            if approval['role'] == current_approver_role:
                current_approval_index = i
                break
        
        if current_approval_index == -1:
            flash('Error in approval chain.', 'danger')
            return redirect(url_for('faculty.dashboard'))

        # Update the current approval status
        approvals[current_approval_index]['status'] = action # 'approved' or 'rejected'
        approvals[current_approval_index]['approved_by'] = user_uid
        approvals[current_approval_index]['timestamp'] = firestore.SERVER_TIMESTAMP

        if action == 'rejected':
            # If rejected at any stage, the whole pass is rejected
            pass_ref.update({
                'status': 'rejected',
                'approvals': approvals
            })
            flash('Pass has been rejected.', 'success')
        
        elif action == 'approved':
            # If this is the last approver, the pass is approved
            if current_approval_index == len(approvals) - 1:
                pass_ref.update({
                    'status': 'approved',
                    'approvals': approvals,
                    'current_approver': None
                })
                flash('Pass has been fully approved!', 'success')
            else:
                # Move to the next approver
                next_approver_role = approvals[current_approval_index + 1]['role']
                pass_ref.update({
                    'approvals': approvals,
                    'current_approver': next_approver_role
                })
                flash('Pass approved and moved to the next stage.', 'success')

    except Exception as e:
        flash(f'An error occurred while processing the pass: {e}', 'danger')

    return redirect(url_for('faculty.dashboard'))
