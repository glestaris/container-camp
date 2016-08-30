FROM python:3.5
ADD . /myapp
RUN pip install -r /myapp/requirements.txt
ENTRYPOINT python /myapp/manage.py runserver 0.0.0.0:8000
