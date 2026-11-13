# toxage-sim: app with data engine and risk models in one container.
# Build from the repository root:  docker build -t toxage-sim .
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOXAGE_DEBUG=0 \
    TOXAGE_DATA_DIR=/data \
    TOXAGE_ALLOWED_HOSTS=*

WORKDIR /srv/toxage
# The Python environment comes from pyproject.toml and uv.lock, as in development.
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-cache
ENV PATH=/srv/toxage/.venv/bin:$PATH

# The app reads the engine, the risk models, the schema and the documents
# from the repository, so all of them are part of the image. The project
# folder (prompt log, internal notes) is for developers and stays out.
COPY README.md ./
COPY schema schema
COPY engine engine
COPY risk-model risk-model
COPY background background
COPY app app

# Every build gets its own stamp: the time of the build and, if given, the
# commit, e.g. GIT_COMMIT=$(git rev-parse --short HEAD). The app shows it in
# the footer and on the about page.
ARG GIT_COMMIT=""
RUN echo "$(date -u +%Y%m%d.%H%M)${GIT_COMMIT:+ ($GIT_COMMIT)}" > BUILD

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
