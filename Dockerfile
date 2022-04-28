FROM python:3.9

COPY requirements.txt /
RUN pip3 install -r /requirements.txt

ENV PYTHONUNBUFFERED yes
WORKDIR /


RUN mkdir /render_templates
RUN mkdir /uploads
COPY templates/ /templates
COPY main.py /


ENTRYPOINT ["gunicorn", "main:app", "-w", "2", "--threads", "8", "-b 0.0.0.0:8000", "-R"]

