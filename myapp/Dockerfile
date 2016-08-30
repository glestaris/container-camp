FROM python:3.5
ADD . /opt/myapp
RUN pip install -r /opt/myapp/requirements.txt
ENTRYPOINT python /opt/myapp/manage.py runserver 0.0.0.0:8000
