from flask import Flask, render_template, request, redirect, url_for, flash, session,send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError
import bcrypt
from flask_mysqldb import MySQL
import MySQLdb
from datetime import datetime
import os
from werkzeug.utils import secure_filename


app = Flask(__name__, static_url_path='/static')
app.secret_key = 'your_secret_key'  # Change this to a strong secret key in production

# Database configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'jayanthi@21'  # Use environment variables for sensitive data(Put the same password as in the MySQL server)
app.config['MYSQL_DB'] = 'Siddhi2' #Name this your SQL Database
app.config['UPLOAD_FOLDER'] = 'static/images'  


mysql = MySQL(app)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/<filename>')
def custom_static(filename):
    return send_from_directory( filename)

# Form classes
class RegisterForm(FlaskForm):
    role = SelectField("Role", choices=[
        ('admin', 'Admin'),
        ('radio_oncologist', 'Radio Oncologist'),
        ('surgical_oncologist', 'Surgical Oncologist'),
        ('medical_oncologist', 'Medical Oncologist'),
        ('pathologist', 'Pathologist'),
        ('operator', 'Operator')
    ], validators=[DataRequired()])

    userName = StringField("Username", validators=[
        DataRequired(),
        Length(min=3, max=50, message="Username must be between 3 and 50 characters long.")
    ])

    password = PasswordField("Password", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long."),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
               message="Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character.")
    ])

    submit = SubmitField("Register")

    def validate_userName(self, field):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE userName=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Username already exists')

class LoginForm(FlaskForm):
    userName = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])    
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        role = form.role.data
        userName = form.userName.data
        password = form.password.data

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("INSERT INTO users (role, userName, password) VALUES (%s, %s, %s)",
                       (role, userName, hashed_password))
        mysql.connection.commit()
        cursor.close()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f' {error}', 'error')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])    
def login():
    form = LoginForm()
    if form.validate_on_submit():
        userName = form.userName.data
        password = form.password.data

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) 
        cursor.execute("SELECT * FROM users WHERE userName=%s", (userName,))
        user = cursor.fetchone()
        cursor.close()
        print(user)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['userId'] = user['userId']
            session['userName'] = user['userName']
            session['role'] = user['role']
            print(user['role'])
            
            # Redirect admin to 'personaldetails' and all other roles to 'existingpatients'
            if user['role'] == 'admin':
                return redirect(url_for('personaldetails'))
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('existingpatients'))
            
            
        else:
            flash('Invalid credentials, please try again.', 'error')

    return render_template('login.html', form=form)

@app.route('/logout')    
def logout():
    session.pop('userId', None)
    session.pop('userName', None)
    session.pop('role', None) 
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/existingpatients', methods=['GET', 'POST'])
def existingpatients():
    if 'role' not in session :
        return redirect(url_for('login'))  

    search_unid = request.form.get('search_unid')  # Get UNID from search bar
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if search_unid:
        cursor.execute("SELECT * FROM personaldetails WHERE unid = %s", (search_unid,))
        personaldetails = cursor.fetchall()

        if not personaldetails:
            flash('Patient does not exist.', 'error')  # Flash message for non-existing patient
    else:
        cursor.execute("SELECT * FROM personaldetails")
        personaldetails = cursor.fetchall()

    cursor.close()
    return render_template('existingpatients.html', personaldetails=personaldetails)
  
@app.route('/personaldetails', methods=['GET', 'POST'])
def personaldetails():
    next_unid = None

    if 'role' in session:
        if request.method == 'POST':
            # Get form data
            patient_name = request.form.get('patient_name')
            address = request.form.get('address')
            phone_number = request.form.get('phone_number')
            dob = request.form.get('dob')
            diagnosis_date = request.form.get('diagnosis_date') or None
            insurance_company = request.form.get('insurance_company')
            insurance_id = request.form.get('insurance_id')

            try:
                dob_date = datetime.strptime(dob, '%Y-%m-%d')

                # Calculate age at diagnosis if diagnosis_date is provided
                age_at_diagnosis = None
                if diagnosis_date:
                    diagnosis_date = datetime.strptime(diagnosis_date, '%Y-%m-%d')

                    if diagnosis_date < dob_date:
                        flash('Error: Date of birth cannot be after the date of diagnosis.', 'error')
                        return render_template('personaldetails.html', next_unid=next_unid)

                    age_at_diagnosis = diagnosis_date.year - dob_date.year
                    if (diagnosis_date.month, diagnosis_date.day) < (dob_date.month, dob_date.day):
                        age_at_diagnosis -= 1

                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute("SELECT * FROM personaldetails WHERE insurance_id=%s", (insurance_id,))
                existing_insurance = cursor.fetchone()

                if existing_insurance:
                    flash('Insurance ID already exists. Please use a different ID.', 'error')
                    return render_template('personaldetails.html', next_unid=next_unid)

                cursor.execute("SELECT MAX(UNID) AS max_unid FROM personaldetails")
                result = cursor.fetchone()
                next_unid = (result['max_unid'] + 1) if result and 'max_unid' in result else 1

                cursor.execute("INSERT INTO personaldetails (UNID, patient_name, address, phone_number, dob, diagnosis_date, age_at_diagnosis, insurance_company, insurance_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               (next_unid, patient_name, address, phone_number, dob, diagnosis_date, age_at_diagnosis, insurance_company, insurance_id))
                mysql.connection.commit()
                flash('Patient added successfully!', 'success')
                return redirect(url_for('currenthealth', UNID=next_unid))

            except MySQLdb.Error as db_err:
                flash(f'Database error occurred: {str(db_err)}', 'error')
            except ValueError: 
                flash('Error: Invalid date format. Please use YYYY-MM-DD.', 'error')
            except Exception as e:
                flash(f'An error occurred: {str(e)}', 'error')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT MAX(UNID) AS max_unid FROM personaldetails")
    result = cursor.fetchone()
    next_unid = (result['max_unid'] + 1) if result and 'max_unid' in result else 1
    cursor.close()

    return render_template('personaldetails.html', next_unid=next_unid)


@app.route('/viewdetails/<unid>', methods=['GET', 'POST'])
def viewdetails(unid):
    
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch patient details from each table
        cursor.execute("SELECT * FROM personaldetails WHERE UNID = %s", (unid,))
        patient = cursor.fetchone()
        
        cursor.execute("SELECT * FROM symptom_evaluation WHERE UNID = %s", (unid,))
        symptoms = cursor.fetchone()
        
        cursor.execute("SELECT * FROM previous_breast_surgeries WHERE UNID = %s", (unid,))
        surgeries = cursor.fetchone()
        
        cursor.execute("SELECT * FROM previous_therapy_sessions WHERE UNID = %s", (unid,))
        therapies = cursor.fetchone()
        
        cursor.execute("SELECT * FROM other_details WHERE UNID = %s", (unid,))
        other_details = cursor.fetchone()
        
        cursor.execute("SELECT * FROM family_health_history WHERE UNID = %s", (unid,))
        family_history = cursor.fetchone()
        
        cursor.execute("SELECT * FROM uploaded_files WHERE UNID = %s", (unid,))
        uploaded_files = cursor.fetchone()

        # Check if patient exists
        if not patient:
            flash('Patient not found.', 'error')
            return redirect(url_for('existingpatients'))

        # Handle form submission to update personal details
        if request.method == 'POST':
            # Implement form processing logic here
            pass  # Include update logic as in your initial code

        return render_template(
            'viewpatient.html',
            patient=patient,
            symptoms=symptoms,
            surgeries=surgeries,
            therapies=therapies,
            other_details=other_details,
            family_history=family_history,
            uploaded_files=uploaded_files
        )




@app.route('/addappointment/<unid>', methods=['GET', 'POST'])
def addappointment(unid):   
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Fetch patient details from personaldetails table
        cursor.execute("SELECT * FROM personaldetails WHERE UNID = %s", (unid,))
        patient = cursor.fetchone()
        
        # Check if patient exists
        if not patient:
            flash('Patient not found.', 'error')
            return redirect(url_for('existingpatients'))

        # Handle form submission to add a new appointment
        if request.method == 'POST':
            doctor = request.form.get('doctor')
            appointment_date = request.form.get('appointment_date')
            comments = request.form.get('comments')

            # Insert the new appointment into the database
            cursor.execute(
                "INSERT INTO appointments (UNID, doctor, appointment_date, comments) VALUES (%s, %s, %s, %s)",
                (unid, doctor, appointment_date, comments)
            )
            mysql.connection.commit()
            flash('Appointment added successfully!', 'success')

            # Redirect to avoid form resubmission on refresh
            return redirect(url_for('addappointment', unid=unid))

        # Fetch existing appointments for this patient (after the form is handled)
        cursor.execute("SELECT * FROM appointments WHERE UNID = %s ORDER BY appointment_date DESC", (unid,))
        appointments = cursor.fetchall()

        return render_template(
            'addappointment.html',
            patient=patient,
            appointments=appointments
        )
   

@app.route('/updateappointment/<int:id>', methods=['POST'])
def updateappointment(id):
    if 'role' in session :
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get the updated data from the form
        doctor = request.form.get('doctor')
        appointment_date = request.form.get('appointment_date')
        comments = request.form.get('comments')  # This can be None if not provided
        unid = request.form.get('unid')

        # Ensure that required fields are filled
        if not doctor or not appointment_date:
            flash('Doctor and Appointment Date are required fields!', 'error')
            return redirect(url_for('addappointment', unid=unid))

        # Update the appointment in the database
        cursor.execute("""
            UPDATE appointments 
            SET doctor = %s, appointment_date = %s, comments = %s 
            WHERE appointment_id = %s
        """, (doctor, appointment_date, comments, id))

        mysql.connection.commit()

        flash('Appointment updated successfully!', 'success')

        return redirect(url_for('addappointment', unid=unid))

    flash('Unauthorized access.', 'error')
    return redirect(url_for('login'))


@app.route('/deleteappointment/<int:id>', methods=['POST'])
def deleteappointment(id):
    if 'role' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        unid = request.form.get('unid')

        # Delete the appointment from the database
        cursor.execute("DELETE FROM appointments WHERE appointment_id = %s", (id,))
        mysql.connection.commit()

        flash('Appointment deleted successfully!', 'success')
        return redirect(url_for('addappointment',unid=unid))  # Redirect back to the patients page or another relevant page

    flash('Unauthorized access.', 'error')
    return redirect(url_for('login'))



@app.route('/deletepatient/<int:unid>', methods=['POST'])
def deletepatient(unid):
    if 'role' in session and session['role'] == 'admin':  # Check for admin role
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        try:
            # Start a transaction to ensure that all deletes are done atomically
            cursor.execute("START TRANSACTION;")

            # Delete associated records from other tables
            cursor.execute("DELETE FROM appointments WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM uploaded_files WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM family_health_history WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM other_details WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM previous_therapy_sessions WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM previous_breast_surgeries WHERE UNID = %s", (unid,))
            cursor.execute("DELETE FROM symptom_evaluation WHERE UNID = %s", (unid,))

            # Now delete the patient from the personaldetails table
            cursor.execute("DELETE FROM personaldetails WHERE UNID = %s", (unid,))

            # Commit all changes if no error occurred
            mysql.connection.commit()

            flash('Patient and all associated details have been deleted successfully!', 'success')
            return redirect(url_for('existingpatients'))  # Redirect back to the list of existing patients

        except Exception as e:
            # If an error occurs, rollback the transaction
            mysql.connection.rollback()
            flash(f'Error occurred while deleting patient: {str(e)}', 'error')
            return redirect(url_for('existingpatients'))

    flash('Unauthorized access.', 'error')
    return redirect(url_for('login'))


@app.route('/edit_personaldetails/<int:unid>', methods=['GET', 'POST'])
def edit_personaldetails(unid):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        # Get updated form data
        patient_name = request.form.get('patient_name')
        address = request.form.get('address')
        phone_number = request.form.get('phone_number')
        dob = request.form.get('dob')
        diagnosis_date = request.form.get('diagnosis_date') or None
        insurance_company = request.form.get('insurance_company')
        insurance_id = request.form.get('insurance_id')

        try:
            dob_date = datetime.strptime(dob, '%Y-%m-%d')

            # Calculate age at diagnosis if diagnosis_date is provided
            age_at_diagnosis = None
            if diagnosis_date:
                diagnosis_date = datetime.strptime(diagnosis_date, '%Y-%m-%d')

                if diagnosis_date < dob_date:
                    flash('Error: Date of birth cannot be after the date of diagnosis.', 'error')
                    return redirect(url_for('edit_personaldetails', unid=unid))

                age_at_diagnosis = diagnosis_date.year - dob_date.year
                if (diagnosis_date.month, diagnosis_date.day) < (dob_date.month, dob_date.day):
                    age_at_diagnosis -= 1

            # Check if the insurance ID already exists in another record
            cursor.execute("SELECT * FROM personaldetails WHERE insurance_id=%s AND UNID != %s", (insurance_id, unid))
            existing_insurance = cursor.fetchone()

            if existing_insurance:
                flash('Insurance ID already exists. Please use a different ID.', 'error')
                return redirect(url_for('edit_personaldetails', unid=unid))

            # Update the personal details in the database
            cursor.execute("""
                UPDATE personaldetails
                SET patient_name=%s, address=%s, phone_number=%s, dob=%s, diagnosis_date=%s, age_at_diagnosis=%s, insurance_company=%s, insurance_id=%s
                WHERE UNID=%s
            """, (patient_name, address, phone_number, dob, diagnosis_date, age_at_diagnosis, insurance_company, insurance_id, unid))

            mysql.connection.commit()
            flash('Patient details updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))  # Redirect to the view details page

        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except ValueError: 
            flash('Error: Invalid date format. Please use YYYY-MM-DD.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Fetch existing data for the specified UNID
    cursor.execute("SELECT * FROM personaldetails WHERE UNID=%s", (unid,))
    patient = cursor.fetchone()
    cursor.close()

    if patient:
        return render_template('edit_personaldetails.html', **patient)
    else:
        flash('Error: Patient not found.', 'error')
        return redirect(url_for('personaldetails'))  # Redirect to personal details page


    
@app.route('/currenthealth', methods=['GET', 'POST'])
def currenthealth():
    if request.method == 'POST':
        UNID = request.form['UNID']
        
        # Retrieve symptoms from the form
        right_symptoms = request.form['right_symptoms'] 
        right_other_symptoms = request.form['right_other_symptoms']
        left_symptoms = request.form['left_symptoms'] 
        left_other_symptoms = request.form['left_other_symptoms']

        # Check for empty symptoms and convert to None
        right_symptoms_str = right_symptoms if right_symptoms else None
        left_symptoms_str = left_symptoms if left_symptoms else None

        try:
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if the entry for this UNID exists
            cur.execute("SELECT * FROM symptom_evaluation WHERE UNID = %s", (UNID,))
            existing_entry = cur.fetchone()
            
            if existing_entry:
                # Update the record if it exists
                cur.execute("""
                    UPDATE symptom_evaluation 
                    SET right_symptoms=%s, right_other_symptoms=%s, left_symptoms=%s, left_other_symptoms=%s
                    WHERE UNID = %s
                """, (right_symptoms_str, right_other_symptoms, left_symptoms_str, left_other_symptoms, UNID))
                flash('Symptoms updated successfully!', 'success')
            else:
                # Insert new record if it does not exist
                cur.execute("""
                    INSERT INTO symptom_evaluation (UNID, right_symptoms, right_other_symptoms, left_symptoms, left_other_symptoms)
                    VALUES (%s, %s, %s, %s, %s)
                """, (UNID, right_symptoms_str, right_other_symptoms, left_symptoms_str, left_other_symptoms))
                flash('Symptoms evaluated successfully!', 'success')

            mysql.connection.commit()
            return redirect(url_for('previousdetails', UNID=UNID))
        
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
            return render_template('currenthealth.html', UNID=UNID)

    # If not POST, render the template with UNID
    UNID = request.args.get('UNID')  # Ensure we get UNID if accessing via GET
    return render_template('currenthealth.html', UNID=UNID)


@app.route('/edit_currenthealth/<int:unid>', methods=['GET', 'POST'])
def edit_currenthealth(unid):
    if request.method == 'POST':
        # Collect data from the form
        right_symptoms = request.form.get('right_symptoms')
        right_other_symptoms = request.form.get('right_other_symptoms')
        left_symptoms = request.form.get('left_symptoms')
        left_other_symptoms = request.form.get('left_other_symptoms')

        # Set symptoms to None if empty
        right_symptoms_str = right_symptoms if right_symptoms else None
        left_symptoms_str = left_symptoms if left_symptoms else None

        try:
            # Connect to the database
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("""
                    UPDATE symptom_evaluation
                    SET right_symptoms = %s, right_other_symptoms = %s, 
                        left_symptoms = %s, left_other_symptoms = %s
                    WHERE UNID = %s
                """, (right_symptoms_str, right_other_symptoms, left_symptoms_str, left_other_symptoms, unid))
                
            mysql.connection.commit()
            flash('Current health details updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))

        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Retrieve existing current health details to pre-fill the form
    try:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM symptom_evaluation WHERE UNID = %s", (unid,))
        current_health = cur.fetchone()

        if not current_health:
            flash('No current health details found for this patient.', 'error')
            return redirect(url_for('currenthealth', UNID=unid))

    except MySQLdb.Error as db_err:
        flash(f'Failed to retrieve details: {str(db_err)}', 'error')
        current_health = {}

    return render_template('edit_currenthealth.html', current_health=current_health, UNID=unid)



@app.route('/previousdetails', methods=['GET', 'POST'])
def previousdetails():
    if request.method == 'POST':
        UNID = request.form['UNID']  # Assuming you have a hidden input for UNID

        # Define fields to retrieve from the form
        fields = [
            'biopsy_left', 'biopsy_left_date',
            'biopsy_right', 'biopsy_right_date',
            'mastectomy_left', 'mastectomy_left_date',
            'mastectomy_right', 'mastectomy_right_date',
            'lumpectomy_left', 'lumpectomy_left_date',
            'lumpectomy_right', 'lumpectomy_right_date',
            'implant_left_silicon', 'implant_left_saline', 'implant_left_date',
            'implant_right_silicon', 'implant_right_saline', 'implant_right_date'
        ]

        # Use a dictionary to hold the extracted values
        data = {}
        for field in fields:
            # For checkbox fields, convert to boolean; for date fields, allow empty to be None
            if 'date' in field:
                data[field] = request.form.get(field) or None
            else:
                data[field] = request.form.get(field) == 'on'

        # Insert into the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("""
                INSERT INTO previous_breast_surgeries (UNID, biopsy_left, biopsy_left_date, 
                biopsy_right, biopsy_right_date, mastectomy_left, mastectomy_left_date,
                mastectomy_right, mastectomy_right_date, lumpectomy_left, lumpectomy_left_date,
                lumpectomy_right, lumpectomy_right_date, implant_left_silicon, implant_left_saline,
                implant_left_date, implant_right_silicon, implant_right_saline, implant_right_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                UNID,
                data['biopsy_left'], data['biopsy_left_date'],
                data['biopsy_right'], data['biopsy_right_date'],
                data['mastectomy_left'], data['mastectomy_left_date'],
                data['mastectomy_right'], data['mastectomy_right_date'],
                data['lumpectomy_left'], data['lumpectomy_left_date'],
                data['lumpectomy_right'], data['lumpectomy_right_date'],
                data['implant_left_silicon'], data['implant_left_saline'], data['implant_left_date'],
                data['implant_right_silicon'], data['implant_right_saline'], data['implant_right_date']
            ))
            mysql.connection.commit()
            flash('Previous surgery details submitted successfully!', 'success')
            return redirect(url_for('previoustherapies', UNID=UNID))  # Ensure this route exists
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    UNID = request.args.get('UNID')  # Ensure we get UNID if accessing via GET
    return render_template('previousdetails.html', UNID=UNID)

@app.route('/edit_previousdetails/<int:unid>', methods=['GET', 'POST'])
def edit_previousdetails(unid):
    if request.method == 'POST':
        
        # Define fields to retrieve from the form
        fields = [
            'biopsy_left', 'biopsy_left_date',
            'biopsy_right', 'biopsy_right_date',
            'mastectomy_left', 'mastectomy_left_date',
            'mastectomy_right', 'mastectomy_right_date',
            'lumpectomy_left', 'lumpectomy_left_date',
            'lumpectomy_right', 'lumpectomy_right_date',
            'implant_left_silicon', 'implant_left_saline', 'implant_left_date',
            'implant_right_silicon', 'implant_right_saline', 'implant_right_date'
        ]

        # Extract form data into a dictionary
        data = {}
        for field in fields:
            # Convert checkbox fields to boolean; allow date fields to be None if empty
            if 'date' in field:
                data[field] = request.form.get(field) or None
            else:
                data[field] = request.form.get(field) == 'on'

        # Update existing record in the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("""
                UPDATE previous_breast_surgeries
                SET biopsy_left=%s, biopsy_left_date=%s, 
                    biopsy_right=%s, biopsy_right_date=%s, 
                    mastectomy_left=%s, mastectomy_left_date=%s, 
                    mastectomy_right=%s, mastectomy_right_date=%s,
                    lumpectomy_left=%s, lumpectomy_left_date=%s,
                    lumpectomy_right=%s, lumpectomy_right_date=%s,
                    implant_left_silicon=%s, implant_left_saline=%s, implant_left_date=%s,
                    implant_right_silicon=%s, implant_right_saline=%s, implant_right_date=%s
                WHERE UNID=%s
            """, (
                data['biopsy_left'], data['biopsy_left_date'],
                data['biopsy_right'], data['biopsy_right_date'],
                data['mastectomy_left'], data['mastectomy_left_date'],
                data['mastectomy_right'], data['mastectomy_right_date'],
                data['lumpectomy_left'], data['lumpectomy_left_date'],
                data['lumpectomy_right'], data['lumpectomy_right_date'],
                data['implant_left_silicon'], data['implant_left_saline'], data['implant_left_date'],
                data['implant_right_silicon'], data['implant_right_saline'], data['implant_right_date'],
                unid
            ))
            mysql.connection.commit()
            flash('Previous surgery details updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))  # Redirect to view details page after update
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    # Retrieve current surgery details to pre-fill the form in GET request
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM previous_breast_surgeries WHERE UNID = %s", (unid,))
        surgery_details = cursor.fetchone()
         # Redirect if no previous details are found
        if not surgery_details:
            flash('No previous surgery details found. Please fill.', 'error')
            return redirect(url_for('previousdetails', UNID=unid))

    except MySQLdb.Error as db_err: 
        flash(f'Failed to retrieve details: {str(db_err)}', 'error')
        surgery_details = {}

    return render_template('edit_previousdetails.html', UNID=unid, surgery_details=surgery_details)


@app.route('/previoustherapies', methods=['GET', 'POST'])
def previoustherapies():
    if request.method == 'POST':
        UNID = request.form['UNID']

        # Radiation Therapy Data
        radiation_preference = request.form.get('radiation_preference')
        radiation_comments = request.form.get('radiation_comments')
        radiation_image_path = None
        
        if radiation_preference == 'yes':  # Check if user opted for Radiation Therapy
            radiation_image = request.files.get('radiation_image')
            if radiation_image:
                # Validate file type
                if not radiation_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid radiation image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('previoustherapies', UNID=UNID))

                radiation_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(radiation_image.filename))
                # Normalize the path to use forward slashes
                radiation_image_path = os.path.normpath(radiation_image_path).replace("\\", "/")
                radiation_image.save(radiation_image_path)  # Save the uploaded file


        # Chemotherapy Data
        chemotherapy_preference = request.form.get('chemotherapy_preference')
        chemotherapy_comments = request.form.get('chemotherapy_comments')
        chemotherapy_image_path = None
        
        if chemotherapy_preference == 'yes':  # Check if user opted for Chemotherapy
            chemotherapy_image = request.files.get('chemotherapy_image')
            if chemotherapy_image:
                # Validate file type
                if not chemotherapy_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid chemotherapy image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('previoustherapies', UNID=UNID))

                chemotherapy_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(chemotherapy_image.filename))
                chemotherapy_image_path = os.path.normpath(chemotherapy_image_path).replace("\\", "/")

                chemotherapy_image.save(chemotherapy_image_path)  # Save the uploaded file

        # Hormonal Therapy Data
        hormonal_preference = request.form.get('hormonal_preference')
        hormonal_comments = request.form.get('hormonal_comments')
        hormonal_image_path = None
        
        if hormonal_preference == 'yes':  # Check if user opted for Hormonal Therapy
            hormonal_image = request.files.get('hormonal_image')
            if hormonal_image:
                # Validate file type
                if not hormonal_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid hormonal image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('previoustherapies', UNID=UNID))

                hormonal_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(hormonal_image.filename))
                hormonal_image_path = os.path.normpath(hormonal_image_path).replace("\\", "/")
                hormonal_image.save(hormonal_image_path)  # Save the uploaded file

        # Insert into the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('''INSERT INTO previous_therapy_sessions 
                              (UNID, radiation_preference, radiation_comments, radiation_image,
                               chemotherapy_preference, chemotherapy_comments, chemotherapy_image,
                               hormonal_preference, hormonal_comments, hormonal_image) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (UNID, radiation_preference, radiation_comments, radiation_image_path,
                            chemotherapy_preference, chemotherapy_comments, chemotherapy_image_path,
                            hormonal_preference, hormonal_comments, hormonal_image_path))
            mysql.connection.commit()
            flash('Therapy session details submitted successfully!', 'success')
            return redirect(url_for('otherdetails', UNID=UNID))
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Ensure we get UNID if accessing via GET
    UNID = request.args.get('UNID')
    return render_template('previoustherapies.html', UNID=UNID)

@app.route('/edit_previoustherapies/<int:unid>', methods=['GET', 'POST'])
def edit_previoustherapies(unid):
    if request.method == 'POST':
        # Radiation Therapy Data
        radiation_preference = request.form.get('radiation_preference')
        radiation_comments = request.form.get('radiation_comments')
        radiation_image_path = None
        
        if radiation_preference == 'yes':  # Check if user opted for Radiation Therapy
            radiation_image = request.files.get('radiation_image')
            if radiation_image:
                # Validate file type
                if not radiation_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid radiation image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_previoustherapies', unid=unid))

                radiation_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(radiation_image.filename))
                radiation_image_path = os.path.normpath(radiation_image_path).replace("\\", "/")
                radiation_image.save(radiation_image_path)  # Save the uploaded file

        # Chemotherapy Data
        chemotherapy_preference = request.form.get('chemotherapy_preference')
        chemotherapy_comments = request.form.get('chemotherapy_comments')
        chemotherapy_image_path = None
        
        if chemotherapy_preference == 'yes':  # Check if user opted for Chemotherapy
            chemotherapy_image = request.files.get('chemotherapy_image')
            if chemotherapy_image:
                # Validate file type
                if not chemotherapy_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid chemotherapy image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_previoustherapies', unid=unid))

                chemotherapy_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(chemotherapy_image.filename))
                chemotherapy_image_path = os.path.normpath(chemotherapy_image_path).replace("\\", "/")
                chemotherapy_image.save(chemotherapy_image_path)  # Save the uploaded file

        # Hormonal Therapy Data
        hormonal_preference = request.form.get('hormonal_preference')
        hormonal_comments = request.form.get('hormonal_comments')
        hormonal_image_path = None
        
        if hormonal_preference == 'yes':  # Check if user opted for Hormonal Therapy
            hormonal_image = request.files.get('hormonal_image')
            if hormonal_image:
                # Validate file type
                if not hormonal_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid hormonal image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_previoustherapies', unid=unid))

                hormonal_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(hormonal_image.filename))
                hormonal_image_path = os.path.normpath(hormonal_image_path).replace("\\", "/")
                hormonal_image.save(hormonal_image_path)  # Save the uploaded file

        # Update therapy session details in the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('''UPDATE previous_therapy_sessions 
                              SET radiation_preference=%s, radiation_comments=%s, radiation_image=%s,
                                  chemotherapy_preference=%s, chemotherapy_comments=%s, chemotherapy_image=%s,
                                  hormonal_preference=%s, hormonal_comments=%s, hormonal_image=%s
                              WHERE UNID=%s''',
                           (radiation_preference, radiation_comments, radiation_image_path,
                            chemotherapy_preference, chemotherapy_comments, chemotherapy_image_path,
                            hormonal_preference, hormonal_comments, hormonal_image_path,
                            unid))
            mysql.connection.commit()
            flash('Therapy session details updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))  # Redirect to view details page after update
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Retrieve current therapy session details to pre-fill the form in GET request
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM previous_therapy_sessions WHERE UNID = %s", (unid,))
        therapy_details = cursor.fetchone()
        # Redirect if no therapy details are found
        if not therapy_details:
            flash('No previous therapy details found. Please fill.', 'error')
            return redirect(url_for('previoustherapies', UNID=unid))

    except MySQLdb.Error as db_err: 
        flash(f'Failed to retrieve details: {str(db_err)}', 'error')
        therapy_details = {}

    return render_template('edit_previoustherapies.html', UNID=unid, therapy_details=therapy_details)



@app.route('/otherdetails', methods=['GET', 'POST'])
def otherdetails():
    if request.method == 'POST':
        UNID = request.form['UNID']

        # Hysterectomy Data
        hysterectomy = request.form.get('hysterectomy')
        hysterectomy_comments = request.form.get('hysterectomy_comments')
        hysterectomy_image_path = None
        
        if hysterectomy == 'yes':  # Check if user opted for Hysterectomy
            hysterectomy_image = request.files.get('hysterectomy_image')
            if hysterectomy_image:
                # Validate file type
                if not hysterectomy_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid hysterectomy image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('otherdetails', UNID=UNID))

                hysterectomy_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(hysterectomy_image.filename))
                hysterectomy_image_path = os.path.normpath(hysterectomy_image_path).replace("\\", "/")
                hysterectomy_image.save(hysterectomy_image_path)  # Save the uploaded file

        # Estrogen Data
        estrogen = request.form.get('estrogen')
        estrogen_comments = request.form.get('estrogen_comments')
        estrogen_image_path = None
        
        if estrogen == 'yes':  # Check if user opted for Estrogen
            estrogen_image = request.files.get('estrogen_image')
            if estrogen_image:
                # Validate file type
                if not estrogen_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid estrogen image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('otherdetails', UNID=UNID))

                estrogen_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(estrogen_image.filename))
                estrogen_image_path = os.path.normpath(estrogen_image_path).replace("\\", "/")
                estrogen_image.save(estrogen_image_path)  # Save the uploaded file

        # Progesterone Data
        progesterone = request.form.get('progesterone')
        progesterone_comments = request.form.get('progesterone_comments')
        progesterone_image_path = None
        
        if progesterone == 'yes':  # Check if user opted for Progesterone
            progesterone_image = request.files.get('progesterone_image')
            if progesterone_image:
                # Validate file type
                if not progesterone_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash('Invalid progesterone image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('otherdetails', UNID=UNID))

                progesterone_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(progesterone_image.filename))
                progesterone_image_path = os.path.normpath(progesterone_image_path).replace("\\", "/")
                progesterone_image.save(progesterone_image_path)  # Save the uploaded file

        # Additional Data
        menstrual_age = request.form.get('menstrual_age')
        menopause_age = request.form.get('menopause_age')
        pregnancy_count = request.form.get('pregnancy_count')

        # Initialize pregnancy-related variables
        first_pregnancy_age = None
        delivery_type = None
        breastfeeding = None

        # Only retrieve these details if the pregnancy count is greater than zero
        if pregnancy_count != "0":
            first_pregnancy_age = request.form.get('first_pregnancy_age')
            delivery_type = request.form.get('delivery_type')
            breastfeeding = request.form.get('breastfeeding')

        # Insert into the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('''INSERT INTO other_details 
                              (UNID, hysterectomy, hysterectomy_comments, hysterectomy_image,
                               estrogen, estrogen_comments, estrogen_image,
                               progesterone, progesterone_comments, progesterone_image,
                               menstrual_age, menopause_age, pregnancy_count, 
                               first_pregnancy_age, delivery_type, breastfeeding) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (UNID, hysterectomy, hysterectomy_comments, hysterectomy_image_path,
                            estrogen, estrogen_comments, estrogen_image_path,
                            progesterone, progesterone_comments, progesterone_image_path,
                            menstrual_age, menopause_age, pregnancy_count,
                            first_pregnancy_age, delivery_type, breastfeeding))
            mysql.connection.commit()
            flash('Other details submitted successfully!', 'success')
            return redirect(url_for('familyhistory', UNID=UNID))  # Replace 'next_page' with the appropriate route
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Ensure we get UNID if accessing via GET
    UNID = request.args.get('UNID')
    return render_template('otherdetails.html', UNID=UNID)


@app.route('/edit_otherdetails/<int:unid>', methods=['GET', 'POST'])
def edit_otherdetails(unid):
    if request.method == 'POST':
        # Hysterectomy Data
        hysterectomy = request.form.get('hysterectomy')
        hysterectomy_comments = request.form.get('hysterectomy_comments')
        hysterectomy_image_path = None
        
        if hysterectomy == 'yes':  # Check if user opted for Hysterectomy
            hysterectomy_image = request.files.get('hysterectomy_image')
            if hysterectomy_image:
                # Validate file type
                if not hysterectomy_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')): 
                    flash('Invalid hysterectomy image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_otherdetails', unid=unid))

                hysterectomy_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(hysterectomy_image.filename))
                hysterectomy_image_path = os.path.normpath(hysterectomy_image_path).replace("\\", "/")
                hysterectomy_image.save(hysterectomy_image_path)  # Save the uploaded file

        # Estrogen Data
        estrogen = request.form.get('estrogen')
        estrogen_comments = request.form.get('estrogen_comments')
        estrogen_image_path = None
        
        if estrogen == 'yes':  # Check if user opted for Estrogen
            estrogen_image = request.files.get('estrogen_image')
            if estrogen_image:
                # Validate file type
                if not estrogen_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')): 
                    flash('Invalid estrogen image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_otherdetails', unid=unid))

                estrogen_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(estrogen_image.filename))
                estrogen_image_path = os.path.normpath(estrogen_image_path).replace("\\", "/")
                estrogen_image.save(estrogen_image_path)  # Save the uploaded file

        # Progesterone Data
        progesterone = request.form.get('progesterone')
        progesterone_comments = request.form.get('progesterone_comments')
        progesterone_image_path = None
        
        if progesterone == 'yes':  # Check if user opted for Progesterone
            progesterone_image = request.files.get('progesterone_image')
            if progesterone_image:
                # Validate file type
                if not progesterone_image.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')): 
                    flash('Invalid progesterone image file type. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_otherdetails', unid=unid))

                progesterone_image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(progesterone_image.filename))
                progesterone_image_path = os.path.normpath(progesterone_image_path).replace("\\", "/")
                progesterone_image.save(progesterone_image_path)  # Save the uploaded file

        # Additional Data
        menstrual_age = request.form.get('menstrual_age')
        menopause_age = request.form.get('menopause_age')
        pregnancy_count = request.form.get('pregnancy_count')

        # Initialize pregnancy-related variables
        first_pregnancy_age = None
        delivery_type = None
        breastfeeding = None

        # Only retrieve these details if the pregnancy count is greater than zero
        if pregnancy_count != "0":
            first_pregnancy_age = request.form.get('first_pregnancy_age')
            delivery_type = request.form.get('delivery_type')
            breastfeeding = request.form.get('breastfeeding')

        # Update other details in the database
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('''UPDATE other_details 
                              SET hysterectomy=%s, hysterectomy_comments=%s, hysterectomy_image=%s,
                                  estrogen=%s, estrogen_comments=%s, estrogen_image=%s,
                                  progesterone=%s, progesterone_comments=%s, progesterone_image=%s,
                                  menstrual_age=%s, menopause_age=%s, pregnancy_count=%s,
                                  first_pregnancy_age=%s, delivery_type=%s, breastfeeding=%s
                              WHERE UNID=%s''',
                           (hysterectomy, hysterectomy_comments, hysterectomy_image_path,
                            estrogen, estrogen_comments, estrogen_image_path,
                            progesterone, progesterone_comments, progesterone_image_path,
                            menstrual_age, menopause_age, pregnancy_count,
                            first_pregnancy_age, delivery_type, breastfeeding, unid))
            mysql.connection.commit()
            flash('Other details updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))  # Redirect to view details page after update
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Retrieve current other details to pre-fill the form in GET request
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM other_details WHERE UNID = %s", (unid,))
        other_details = cursor.fetchone()
        # Redirect if no other details are found
        if not other_details:
            flash('No other details found. Please fill.', 'error')
            return redirect(url_for('otherdetails', UNID=unid))

    except MySQLdb.Error as db_err: 
        flash(f'Failed to retrieve details: {str(db_err)}', 'error')
        other_details = {}

    return render_template('edit_otherdetails.html', UNID=unid, other_details=other_details)


@app.route('/familyhistory', methods=['GET', 'POST'])
def familyhistory():
    if request.method == 'POST':
        # Collect data from the form
        UNID = request.form.get('UNID')
        benign_biopsies_you = 1 if request.form.get('benign-biopsies-you') == 'on' else 0
        benign_biopsies_count_you = int(request.form.get('benign-biopsies-count-you') or 0)
        benign_biopsies_family = 1 if request.form.get('benign-biopsies-family') == 'on' else 0
        benign_biopsies_count_family = int(request.form.get('benign-biopsies-count-family') or 0)
        family_member_comment_1 = request.form.get('family-member-comment-1', '')

        biopsy_atypical_you = 1 if request.form.get('biopsy-atypical-you') == 'on' else 0
        biopsy_atypical_family = 1 if request.form.get('biopsy-atypical-family') == 'on' else 0
        family_member_comment_2 = request.form.get('family-member-comment-2', '')

        cancer_before_50_you = 1 if request.form.get('cancer-before-50-you') == 'on' else 0
        cancer_before_50_family = 1 if request.form.get('cancer-before-50-family') == 'on' else 0
        family_member_comment_3 = request.form.get('family-member-comment-3', '')

        cancer_after_50_you = 1 if request.form.get('cancer-after-50-you') == 'on' else 0
        cancer_after_50_family = 1 if request.form.get('cancer-after-50-family') == 'on' else 0
        family_member_comment_4 = request.form.get('family-member-comment-4', '')

        ovarian_cancer_you = 1 if request.form.get('ovarian-cancer-you') == 'on' else 0
        ovarian_cancer_family = 1 if request.form.get('ovarian-cancer-family') == 'on' else 0
        family_member_comment_5 = request.form.get('family-member-comment-5', '')

        radiation_treatment_you = 1 if request.form.get('radiation-treatment-you') == 'on' else 0
        radiation_treatment_family = 1 if request.form.get('radiation-treatment-family') == 'on' else 0
        family_member_comment_6 = request.form.get('family-member-comment-6', '')

        try:
            # Connect to the database
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Insert data into the database
            query = """
            INSERT INTO family_health_history (
                UNID, benign_biopsies_you, benign_biopsies_count_you,
                benign_biopsies_family, benign_biopsies_count_family,
                family_member_comment_1, biopsy_atypical_you,
                biopsy_atypical_family, family_member_comment_2,
                cancer_before_50_you, cancer_before_50_family,
                family_member_comment_3, cancer_after_50_you,
                cancer_after_50_family, family_member_comment_4,
                ovarian_cancer_you, ovarian_cancer_family,
                family_member_comment_5, radiation_treatment_you,
                radiation_treatment_family, family_member_comment_6
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                UNID, benign_biopsies_you, benign_biopsies_count_you,
                benign_biopsies_family, benign_biopsies_count_family,
                family_member_comment_1, biopsy_atypical_you,
                biopsy_atypical_family, family_member_comment_2,
                cancer_before_50_you, cancer_before_50_family,
                family_member_comment_3, cancer_after_50_you,
                cancer_after_50_family, family_member_comment_4,
                ovarian_cancer_you, ovarian_cancer_family,
                family_member_comment_5, radiation_treatment_you,
                radiation_treatment_family, family_member_comment_6
            ))
            mysql.connection.commit()

            flash('Data submitted successfully!', 'success')
            return redirect(url_for('filescans', UNID=UNID)) 
         
        
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Ensure we get UNID if accessing via GET
    UNID = request.args.get('UNID')

    return render_template('familyhistory.html', UNID=UNID)

@app.route('/edit_familyhistory/<int:unid>', methods=['GET', 'POST'])
def edit_familyhistory(unid):
    if request.method == 'POST':
        # Collect data from the form
        benign_biopsies_you = 1 if request.form.get('benign-biopsies-you') == 'on' else 0
        benign_biopsies_count_you = int(request.form.get('benign-biopsies-count-you') or 0)
        benign_biopsies_family = 1 if request.form.get('benign-biopsies-family') == 'on' else 0
        benign_biopsies_count_family = int(request.form.get('benign-biopsies-count-family') or 0)
        family_member_comment_1 = request.form.get('family-member-comment-1', '')

        biopsy_atypical_you = 1 if request.form.get('biopsy-atypical-you') == 'on' else 0
        biopsy_atypical_family = 1 if request.form.get('biopsy-atypical-family') == 'on' else 0
        family_member_comment_2 = request.form.get('family-member-comment-2', '')

        cancer_before_50_you = 1 if request.form.get('cancer-before-50-you') == 'on' else 0
        cancer_before_50_family = 1 if request.form.get('cancer-before-50-family') == 'on' else 0
        family_member_comment_3 = request.form.get('family-member-comment-3', '')

        cancer_after_50_you = 1 if request.form.get('cancer-after-50-you') == 'on' else 0
        cancer_after_50_family = 1 if request.form.get('cancer-after-50-family') == 'on' else 0
        family_member_comment_4 = request.form.get('family-member-comment-4', '')

        ovarian_cancer_you = 1 if request.form.get('ovarian-cancer-you') == 'on' else 0
        ovarian_cancer_family = 1 if request.form.get('ovarian-cancer-family') == 'on' else 0
        family_member_comment_5 = request.form.get('family-member-comment-5', '')

        radiation_treatment_you = 1 if request.form.get('radiation-treatment-you') == 'on' else 0
        radiation_treatment_family = 1 if request.form.get('radiation-treatment-family') == 'on' else 0
        family_member_comment_6 = request.form.get('family-member-comment-6', '')

        try:
            # Connect to the database
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Update data in the database
            query = """
            UPDATE family_health_history 
            SET benign_biopsies_you = %s, benign_biopsies_count_you = %s,
                benign_biopsies_family = %s, benign_biopsies_count_family = %s,
                family_member_comment_1 = %s, biopsy_atypical_you = %s,
                biopsy_atypical_family = %s, family_member_comment_2 = %s,
                cancer_before_50_you = %s, cancer_before_50_family = %s,
                family_member_comment_3 = %s, cancer_after_50_you = %s,
                cancer_after_50_family = %s, family_member_comment_4 = %s,
                ovarian_cancer_you = %s, ovarian_cancer_family = %s,
                family_member_comment_5 = %s, radiation_treatment_you = %s,
                radiation_treatment_family = %s, family_member_comment_6 = %s
            WHERE UNID = %s
            """
            cursor.execute(query, (
                benign_biopsies_you, benign_biopsies_count_you,
                benign_biopsies_family, benign_biopsies_count_family,
                family_member_comment_1, biopsy_atypical_you,
                biopsy_atypical_family, family_member_comment_2,
                cancer_before_50_you, cancer_before_50_family,
                family_member_comment_3, cancer_after_50_you,
                cancer_after_50_family, family_member_comment_4,
                ovarian_cancer_you, ovarian_cancer_family,
                family_member_comment_5, radiation_treatment_you,
                radiation_treatment_family, family_member_comment_6,
                unid
            ))
            mysql.connection.commit()

            flash('Family health history updated successfully!', 'success')
            return redirect(url_for('viewdetails', unid=unid))

        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Fetch existing family history details to pre-fill the form
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM family_health_history WHERE UNID = %s", (unid,))
        family_history = cursor.fetchone()

        if not family_history:
            flash('No family health history found for this patient.', 'error')
            return redirect(url_for('familyhistory', UNID=unid))

    except MySQLdb.Error as db_err:
        flash(f'Failed to retrieve details: {str(db_err)}', 'error')
        family_history = {}
        
    return render_template('edit_familyhistory.html', family_history=family_history, UNID=unid)
     


@app.route('/filescans', methods=['GET', 'POST'])
def filescans():
    if request.method == 'POST':
        UNID = request.form.get('UNID')
        
        # Prepare to handle uploaded files
        uploaded_files = {
            'biopsy_report': request.files.get('biopsy-report'),
            'biomarker_report': request.files.get('biomarker-report'),
            'routine_report': request.files.get('routine-report'),
            'xray_chest': request.files.get('xray-chest'),
            'usg_breast': request.files.get('usg-breast'),
            'mmg_breast': request.files.get('mmg-breast'),
            'mri_breast': request.files.get('mri-breast'),
            'usg_abdomen': request.files.get('usg-abdomen'),
            'ct_chest': request.files.get('ct-chest'),
            'ct_abdomen': request.files.get('ct-abdomen'),
            'bone_scan': request.files.get('bone-scan'),
            'pet_scan': request.files.get('pet-scan'),
            'hormonal_receptor': request.files.get('hormonal-receptor')
        }


        file_paths = {}
        # Validate and save files
        for file_key, file in uploaded_files.items():
            if file:
                # Validate file type
                if not file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash(f'Invalid file type for {file_key.replace("_", " ").title()}. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('filescans', UNID=UNID))

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
                # Normalize the path to use forward slashes
                file_path = os.path.normpath(file_path).replace("\\", "/")
                file.save(file_path)  # Save the uploaded file
                file_paths[file_key] = file_path
        # Here you can insert the file paths into the database if needed
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''INSERT INTO uploaded_files 
                              (UNID, biopsy_report, biomarker_report, routine_report, 
                               xray_chest, usg_breast, mmg_breast, mri_breast, 
                               usg_abdomen, ct_chest, ct_abdomen, bone_scan, 
                               pet_scan, hormonal_receptor) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (UNID, 
                            file_paths.get('biopsy_report'), 
                            file_paths.get('biomarker_report'),
                            file_paths.get('routine_report'), 
                            file_paths.get('xray_chest'),
                            file_paths.get('usg_breast'), 
                            file_paths.get('mmg_breast'),
                            file_paths.get('mri_breast'), 
                            file_paths.get('usg_abdomen'),
                            file_paths.get('ct_chest'), 
                            file_paths.get('ct_abdomen'), 
                            file_paths.get('bone_scan'),
                            file_paths.get('pet_scan'),
                            file_paths.get('hormonal_receptor')))
            mysql.connection.commit()
            flash('Files uploaded successfully!', 'success')
            return redirect(url_for('existingpatients'))  # Change to your next page
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    UNID = request.args.get('UNID')
    return render_template('filescans.html', UNID=UNID)


@app.route('/edit_filescans/<int:unid>', methods=['GET', 'POST'])
def edit_filescans(unid):
    # Initialize file_scans as an empty dictionary at the start
    file_scans = {}

    if request.method == 'POST':
        # Prepare to handle uploaded files
        uploaded_files = {
            'biopsy_report': request.files.get('biopsy-report'),
            'biomarker_report': request.files.get('biomarker-report'),
            'routine_report': request.files.get('routine-report'),
            'xray_chest': request.files.get('xray-chest'),
            'usg_breast': request.files.get('usg-breast'),
            'mmg_breast': request.files.get('mmg-breast'),
            'mri_breast': request.files.get('mri-breast'),
            'usg_abdomen': request.files.get('usg-abdomen'),
            'ct_chest': request.files.get('ct-chest'),
            'ct_abdomen': request.files.get('ct-abdomen'),
            'bone_scan': request.files.get('bone-scan'),
            'pet_scan': request.files.get('pet-scan'),
            'hormonal_receptor': request.files.get('hormonal-receptor')
        }

        file_paths = {}
        
        # Validate and save files
        for file_key, file in uploaded_files.items():
            if file:
                # Validate file type
                if not file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    flash(f'Invalid file type for {file_key.replace("_", " ").title()}. Please upload a PDF or an image file (JPG, JPEG, PNG).', 'error')
                    return redirect(url_for('edit_filescans', unid=unid))
                
                # Save the new file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
                file_path = os.path.normpath(file_path).replace("\\", "/")  # Normalize the path
                file.save(file_path)
                file_paths[file_key] = file_path  # Store the file path for database update
            else:
                # If no new file is uploaded, keep the existing file path from the database
                file_paths[file_key] = file_scans.get(file_key, '') # Fallback to empty string if file_scans is empty

        # Update file paths in the database
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''UPDATE uploaded_files 
                              SET biopsy_report=%s, biomarker_report=%s, routine_report=%s, 
                                  xray_chest=%s, usg_breast=%s, mmg_breast=%s, mri_breast=%s, 
                                  usg_abdomen=%s, ct_chest=%s, ct_abdomen=%s, bone_scan=%s, 
                                  pet_scan=%s, hormonal_receptor=%s 
                              WHERE UNID=%s''', (
                                file_paths.get('biopsy_report'),
                                file_paths.get('biomarker_report'),
                                file_paths.get('routine_report'),
                                file_paths.get('xray_chest'),
                                file_paths.get('usg_breast'),
                                file_paths.get('mmg_breast'),
                                file_paths.get('mri_breast'),
                                file_paths.get('usg_abdomen'),
                                file_paths.get('ct_chest'),
                                file_paths.get('ct_abdomen'),
                                file_paths.get('bone_scan'),
                                file_paths.get('pet_scan'),
                                file_paths.get('hormonal_receptor'),
                                unid
            ))
            mysql.connection.commit()
            flash('File scans updated successfully!', 'success')
            return redirect(url_for('existingpatients'))  # Redirect to the appropriate page
        except MySQLdb.Error as db_err:
            flash(f'Database error occurred: {str(db_err)}', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    # Retrieve current file scan paths for pre-filling the form in a GET request
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM uploaded_files WHERE UNID = %s", (unid,))
        file_scans = cursor.fetchone()
      
        if not file_scans:
            flash('No file scans found. Please upload new scans.', 'error')
            return redirect(url_for('filescans', unid=unid))
    except MySQLdb.Error as db_err: 
        flash(f'Failed to retrieve file scans: {str(db_err)}', 'error')

    return render_template('edit_filescans.html', UNID=unid, file_scans=file_scans)

if __name__ == '__main__':
    app.run(debug=True)
