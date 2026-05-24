@echo off
cd C:\Users\KIIT\Downloads\outfit-gen-tool\backend
call venv\Scripts\activate
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\KIIT\Downloads\outfit-gen-tool\backend\service-account-key.json
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause