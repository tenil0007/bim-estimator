@echo off
echo ==============================================
echo 🏗️ BIM AI Cost ^& Time Estimator Setup
echo ==============================================

echo [1/4] Checking Python version...
python --version
py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 is not installed. Please install Python 3.12 and try again.
    exit /b 1
)

echo [2/4] Setting up backend environment...
cd backend
if not exist "venv_312" (
    echo Creating Python 3.12 virtual environment...
    py -3.12 -m venv venv_312
)
echo Installing backend dependencies...
call venv_312\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo [3/4] Checking for .env configuration...
if not exist ".env" (
    echo Creating default .env file from .env.example...
    copy .env.example .env
)

echo [4/4] Setting up frontend environment...
cd frontend
if exist "package.json" (
    echo Installing frontend dependencies...
    call npm install
) else (
    echo [WARN] package.json not found in frontend directory. Is it initialized?
)
cd ..

echo ==============================================
echo ✅ Setup complete!
echo To run the backend: cd backend ^& call venv_312\Scripts\activate ^& uvicorn app.main:app --reload
echo To run the frontend: cd frontend ^& npm run dev
echo ==============================================
exit /b 0
