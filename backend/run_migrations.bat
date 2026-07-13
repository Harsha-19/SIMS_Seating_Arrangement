@echo off
setlocal
pushd "%~dp0"
python manage.py makemigrations api
python manage.py migrate
popd
endlocal
