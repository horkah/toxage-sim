# toxage-sim: app with data engine and risk models in one container.
# Build from the repository root:  docker build -t toxage-sim .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOXAGE_DEBUG=0 \
    TOXAGE_DATA_DIR=/data \
    TOXAGE_ALLOWED_HOSTS=*

WORKDIR /srv/toxage
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt

# The app reads the engine, the risk models, the schema and the documents
# from the repository, so all of them are part of the image.
COPY README.md ./
COPY schema schema
COPY engine engine
COPY risk-model risk-model
COPY background background
COPY project project
COPY app app

# The database and the secret key live in /data, which is a volume.
RUN useradd --system --create-home toxage && mkdir /data && chown toxage /data
USER toxage
VOLUME /data
EXPOSE 8000
WORKDIR /srv/toxage/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/disclaimer/', timeout=4)"

# One worker process: data sets are generated in a thread of this process,
# and the rows of a scenario are kept in its memory. Threads serve the requests.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn toxage_app.wsgi --bind 0.0.0.0:8000 --workers 1 --threads 8 --timeout 120"]
