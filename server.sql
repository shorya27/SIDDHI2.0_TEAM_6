CREATE DATABASE Siddhi2;
USE Siddhi2;

CREATE TABLE users (
    userId INT AUTO_INCREMENT PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    userName VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp for user creation
);

CREATE TABLE personaldetails (
    UNID INT PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone_number VARCHAR(15) NOT NULL,
    dob DATE NOT NULL,
    diagnosis_date DATE,
    age_at_diagnosis INT,
    insurance_company VARCHAR(100) NOT NULL,
    insurance_id VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp for personal details creation
);

CREATE TABLE symptom_evaluation (
    UNID INT NOT NULL,
    right_symptoms TEXT,
    right_other_symptoms TEXT,
    left_symptoms TEXT, 
    left_other_symptoms TEXT,
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp for symptom evaluation creation
);

CREATE TABLE previous_breast_surgeries (
    UNID INT NOT NULL,
    biopsy_left BOOLEAN DEFAULT FALSE,
    biopsy_left_date DATE,
    biopsy_right BOOLEAN DEFAULT FALSE,
    biopsy_right_date DATE,
    mastectomy_left BOOLEAN DEFAULT FALSE,
    mastectomy_left_date DATE,
    mastectomy_right BOOLEAN DEFAULT FALSE,
    mastectomy_right_date DATE,
    lumpectomy_left BOOLEAN DEFAULT FALSE,
    lumpectomy_left_date DATE,
    lumpectomy_right BOOLEAN DEFAULT FALSE,
    lumpectomy_right_date DATE,
    implant_left_silicon BOOLEAN DEFAULT FALSE,
    implant_left_saline BOOLEAN DEFAULT FALSE,
    implant_left_date DATE,
    implant_right_silicon BOOLEAN DEFAULT FALSE,
    implant_right_saline BOOLEAN DEFAULT FALSE,
    implant_right_date DATE,
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Timestamp for surgery details creation
);

CREATE TABLE previous_therapy_sessions (
    UNID INT NOT NULL,
    radiation_preference ENUM('yes', 'no'),
    radiation_comments TEXT,
    radiation_image VARCHAR(255),
    chemotherapy_preference ENUM('yes', 'no'),
    chemotherapy_comments TEXT,
    chemotherapy_image VARCHAR(255),
    hormonal_preference ENUM('yes', 'no'),
    hormonal_comments TEXT,
    hormonal_image VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for therapy session creation
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE
);

CREATE TABLE other_details (
    UNID INT NOT NULL,
    hysterectomy ENUM('yes', 'no') NOT NULL,
    hysterectomy_comments TEXT,
    hysterectomy_image VARCHAR(255),
    estrogen ENUM('yes', 'no') NOT NULL,
    estrogen_comments TEXT,
    estrogen_image VARCHAR(255),
    progesterone ENUM('yes', 'no') NOT NULL,
    progesterone_comments TEXT,
    progesterone_image VARCHAR(255),
    menstrual_age VARCHAR(50),
    menopause_age VARCHAR(50),
    pregnancy_count INT,
    first_pregnancy_age VARCHAR(50),
    delivery_type ENUM('normal', 'surgery'),
    breastfeeding ENUM('yes', 'no'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for other details creation
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE
);

CREATE TABLE family_health_history (
    UNID INT NOT NULL,
    benign_biopsies_you BOOLEAN,
    benign_biopsies_count_you INT,
    benign_biopsies_family BOOLEAN,
    benign_biopsies_count_family INT,
    family_member_comment_1 VARCHAR(255),
    biopsy_atypical_you BOOLEAN,
    biopsy_atypical_family BOOLEAN,
    family_member_comment_2 VARCHAR(255),
    cancer_before_50_you BOOLEAN,
    cancer_before_50_family BOOLEAN,
    family_member_comment_3 VARCHAR(255),
    cancer_after_50_you BOOLEAN,
    cancer_after_50_family BOOLEAN,
    family_member_comment_4 VARCHAR(255),
    ovarian_cancer_you BOOLEAN,
    ovarian_cancer_family BOOLEAN,
    family_member_comment_5 VARCHAR(255),
    radiation_treatment_you BOOLEAN,
    radiation_treatment_family BOOLEAN,
    family_member_comment_6 VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for family health history creation
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE
);

CREATE TABLE uploaded_files (
    UNID INT NOT NULL,
    biopsy_report VARCHAR(255),
    biomarker_report VARCHAR(255),
    routine_report VARCHAR(255),
    xray_chest VARCHAR(255),
    usg_breast VARCHAR(255),
    mmg_breast VARCHAR(255),
    mri_breast VARCHAR(255),
    usg_abdomen VARCHAR(255),
    ct_chest VARCHAR(255),
    ct_abdomen VARCHAR(255),
    bone_scan VARCHAR(255),
    pet_scan VARCHAR(255),
    hormonal_receptor VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Timestamp for file uploads creation
    PRIMARY KEY (UNID),
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE
);

CREATE TABLE appointments (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    UNID INT NOT NULL,
    doctor VARCHAR(255),
    comments VARCHAR(255),
    appointment_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UNID) REFERENCES personaldetails(UNID)  ON DELETE CASCADE
);

-- Queries to check data in tables
SELECT * FROM appointments;
SELECT * FROM uploaded_files;
SELECT * FROM family_health_history;
SELECT * FROM other_details;
SELECT * FROM previous_therapy_sessions;
SELECT * FROM previous_breast_surgeries;
SELECT * FROM symptom_evaluation;
SELECT * FROM users;
SELECT * FROM personaldetails;