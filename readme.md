# RiaBot Chatbot App

## Project Version Requirements

To ensure full compatibility across the different components of the RiaBot Chatbot application, please use the following version requirements for the project:

### 1. Backend (Django)
- **Python**: `3.10.11`

### 2. Frontend (React JS)
- **Node.js**: `22.18.0`

### 3. Rasa
- **Python**: `3.10.11`

---

## Step-by-Step Setup Guide

Follow these simple instructions to run the project on a fresh machine. 

### Prerequisites
- **Python 3.10.11** installed
- **Node.js 22.18.0** installed
- **PostgreSQL Database**
- **Redis Server** (For Celery Task Queue)

### Environment Variables Setup
Before starting the servers, create a `.env` file in the root of the project (you can copy `.env.example` as a template). 
You will need to generate secure keys for `SECRET_KEY` (Django) and `RASA_TOKEN_SECRET` (Rasa). Run this command twice to generate two separate keys:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Place them in your `.env` file along with your database credentials.

### 1. Backend (Django)
Open a terminal and set up the Django Backend:
```bash
cd backend

# Create Virtual Environment & Activate
python -m venv venv
venv\Scripts\activate   # (Mac/Linux: source venv/bin/activate)

# Install Dependencies
pip install -r requirements.txt

# Run Database Migrations & Create Superuser (Make sure Postgres is running)
python manage.py migrate
python manage.py createsuperuser

# Start the Backend Server
python manage.py runserver
```

### 2. Rasa Server & Actions
Open a **new terminal** and set up the Rasa Core server:
```bash
cd rasa

# Create Virtual Environment & Activate
python -m venv venv
venv\Scripts\activate   # (Mac/Linux: source venv/bin/activate)

# Install Dependencies
pip install -r requirements.txt

# Train Rasa Model (If it's the first time, or if you made changes to training data)
rasa train

# Run Rasa Server
rasa run -m models --enable-api --cors "*"
```

Open another **new terminal** for Rasa Actions:
```bash
cd rasa
venv\Scripts\activate

# Run Rasa Action Server
rasa run actions
```

### 3. Frontend (React)
Open a **new terminal** for the React Frontend:
```bash
cd frontend

# Install Dependencies
npm install

# Start Local Dev Server
npm run dev
```

---

## How to Use the Website

Once all three servers are running (Backend, Rasa, and Frontend), follow these steps to use the application:

1. **Access the Application**: 
   Open your browser and navigate to `http://localhost:5173` (or the port specified by Vite when you started the frontend dev server).

2. **Register or Login**:
   - If this is your first time, click on the **Register** link to create a new user account.
   - If you already have an account, enter your credentials to **Login**.

3. **Chatting with RiaBot**:
   - Once logged in, you will be redirected to the main **Chat Interface**.
   - Start typing your messages! The chatbot will process your messages through the backend and connect with Rasa for NLP and intent recognition to give you the appropriate responses.

4. **Accessing the Backend Admin Panel** *(Optional)*:
   - Navigate to `http://localhost:8000/admin` in your browser.
   - Log in using the superuser credentials you created during the setup step (`python manage.py createsuperuser`).
   - Here, you can manage users, view chat histories, and access administrative backend features.
