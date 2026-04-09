@echo off
"C:\Users\Harsha\AppData\Local\Programs\Python\Python312\python.exe" manage.py makemigrations api
"C:\Users\Harsha\AppData\Local\Programs\Python\Python312\python.exe" manage.py migrate api
dir
echo "Done"
