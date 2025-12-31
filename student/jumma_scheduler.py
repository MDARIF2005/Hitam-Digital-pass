"""
Automatic Jumma Prayer Pass Generation Module
Generates automatic passes for male Muslim students during configured Jumma prayer times
"""

from firebase_admin import firestore
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_automatic_jumma_passes():
    """
    Automatically generates Jumma prayer passes for eligible male Muslim students.
    This function should be called at the start of each Jumma prayer time (typically Friday at noon).
    
    Eligibility criteria:
    - Student must have gender = "Male"
    - Student must have religion = "Muslim" or "Islam"
    - No existing pass for today
    """
    try:
        db = firestore.client()
        
        # Get system settings to check if Jumma pass automation is enabled
        settings_ref = db.collection('settings').document('system').get()
        if not settings_ref.exists:
            logger.warning("System settings not found")
            return {"status": "error", "message": "System settings not found"}
        
        settings = settings_ref.to_dict()
        
        # Check if automatic Jumma pass generation is enabled
        if not settings.get('auto_jumma_pass_enabled', False):
            logger.info("Automatic Jumma pass generation is disabled")
            return {"status": "disabled", "message": "Automatic Jumma pass generation is disabled"}
        
        jumma_start_time = settings.get('jumma_pass_start_time', '12:00')
        jumma_end_time = settings.get('jumma_pass_end_time', '14:00')
        
        # Get all male Muslim students
        students_ref = db.collection('students').where('gender', '==', 'Male').stream()
        
        eligible_students = []
        for student_doc in students_ref:
            student_data = student_doc.to_dict()
            
            # Check if student's religion is Muslim
            religion = student_data.get('religion', '').lower()
            if 'muslim' in religion or 'islam' in religion:
                eligible_students.append({
                    'id': student_doc.id,
                    'data': student_data
                })
        
        # Create passes for eligible students
        generated_count = 0
        failed_count = 0
        today = datetime.now().date()
        
        for student in eligible_students:
            try:
                student_id = student['id']
                student_data = student['data']
                
                # Check if student already has a pass for today (any type)
                today_start = datetime.combine(today, datetime.min.time())
                today_end = datetime.combine(today, datetime.max.time())
                
                existing_passes = db.collection('passes').where('applicant_id', '==', student_id).where('date', '>=', today_start).where('date', '<=', today_end).stream()
                
                has_existing_pass = False
                for _ in existing_passes:
                    has_existing_pass = True
                    break
                
                if has_existing_pass:
                    logger.info(f"Student {student_id} already has a pass for today, skipping")
                    continue
                
                # Create automatic Jumma pass
                pass_id = str(uuid.uuid4())
                pass_data = {
                    "pass_id": pass_id,
                    "applicant_id": student_id,
                    "applicant_name": student_data.get('name'),
                    "applicant_type": "student",
                    "roll_number": student_data.get('roll_number'),
                    "department": student_data.get('branch'),
                    "academic_year": student_data.get('academic_year'),
                    "pass_out_year": student_data.get('pass_out_year'),
                    "pass_type": "jumma",  # Mark as Jumma pass
                    "reason": "Jumma Prayer (Automatic)",
                    "date": firestore.SERVER_TIMESTAMP,
                    "out_time": jumma_start_time,
                    "in_time": jumma_end_time,
                    "is_automatic": True,  # Mark as automatically generated
                    "status": "auto_approved",  # Auto-approve Jumma passes
                    "approvals": [
                        {'role': f"mentor_{student_data.get('academic_year')}_{student_data.get('branch')}_{student_data.get('section')}", 'status': 'auto_approved'},
                        {'role': f"hod_{student_data.get('branch')}", 'status': 'auto_approved'}
                    ],
                    "current_approver": None,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "auto_generated_at": datetime.now()
                }
                
                # Save the pass
                db.collection('passes').document(pass_id).set(pass_data)
                generated_count += 1
                logger.info(f"Generated automatic Jumma pass for student {student_id}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to generate Jumma pass for student {student.get('id')}: {e}")
                continue
        
        logger.info(f"Jumma pass generation completed: {generated_count} generated, {failed_count} failed")
        return {
            "status": "success",
            "generated": generated_count,
            "failed": failed_count,
            "message": f"Generated {generated_count} Jumma passes successfully"
        }
        
    except Exception as e:
        logger.error(f"Error in automatic Jumma pass generation: {e}")
        return {"status": "error", "message": str(e)}


def schedule_jumma_pass_generation(scheduler, jumma_time_str="12:00"):
    """
    Schedules the automatic Jumma pass generation to run every Friday at the configured time.
    
    Args:
        scheduler: APScheduler scheduler instance
        jumma_time_str: Time in HH:MM format when to generate passes (default 12:00)
    """
    try:
        # Schedule to run every Friday at the specified time
        hours, minutes = map(int, jumma_time_str.split(':'))
        
        scheduler.add_job(
            func=generate_automatic_jumma_passes,
            trigger="cron",
            day_of_week=4,  # 4 = Friday (0 = Monday, 6 = Sunday)
            hour=hours,
            minute=minutes,
            id='jumma_pass_generation',
            name='Automatic Jumma Pass Generation',
            replace_existing=True
        )
        logger.info(f"Scheduled Jumma pass generation for every Friday at {jumma_time_str}")
        return True
    except Exception as e:
        logger.error(f"Failed to schedule Jumma pass generation: {e}")
        return False
