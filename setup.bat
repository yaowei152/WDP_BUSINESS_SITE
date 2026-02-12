@echo off
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete!
echo To activate the virtual environment, run: venv\Scripts\activate
echo To run the application, run: python app.py
pause
