# 🏥 Comprehensive Hospital Management System

Welcome to the **Hospital Management System** repository! This is a robust and scalable web application built with **Django** (Python) that streamlines hospital operations, enhances patient care, and simplifies administrative tasks. 

## ✨ Key Features

### 🧑‍⚕️ For Patients
- **Quick OPD Registration**: Fast and seamless Outpatient Department registration flow.
- **Patient Dashboard**: Personalized dashboard displaying patient name, blood group, token number, and appointment details.
- **Appointment Booking**: Easy-to-use interface for scheduling appointments with specific doctors and specializations.
- **Health Metrics Tracking**: Input and track vital health metrics over time.
- **Report Uploads**: Secure mechanism for patients to upload and manage medical reports securely.

### 👨‍💼 For Hospital Staff & Administration
- **Staff Dashboard**: Dedicated portal for medical staff to manage daily operations, track patient flow, and update records.
- **Patient Management**: Complete CRM for patients, including profile viewing, medical history, and prioritization.
- **TV Board Display**: Live synchronized token and queue management system designed to be displayed on hospital waiting room TVs.
- **Appointment Prioritization**: Integrated priority queues to systematically manage emergency and regular appointments.

## 🛠️ Technology Stack
- **Backend Framework**: Django (Python)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Django Templates
- **Database**: SQLite (Development)
- **Version Control**: Git & GitHub

## 🚀 Getting Started

Follow these steps to set up the project locally on your machine.

### Prerequisites
- Python 3.8+
- pip (Python Package Installer)
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/advaithullaskumar-bit/hospital-app.git
   cd hospital-app/hospital_app_upgraded
Create a virtual environment (Recommended):

bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
Install dependencies:

bash
pip install -r requirements.txt
Environment Variables: Copy the example environment file and configure your local settings.

bash
cp .env.example .env
Apply Database Migrations:

bash
cd hospital_app
python manage.py makemigrations
python manage.py migrate
Populate Initial Data (Optional):

bash
python manage.py populate_data
Run the Development Server:

bash
python manage.py runserver
Access the Application: Open your browser and navigate to http://127.0.0.1:8000/

🤝 Contributing
Contributions, issues, and feature requests are always welcome! Feel free to check the issues page.

📄 License
This project is open-source and ready for customization.

Built with ❤️ to revolutionize healthcare administration.
