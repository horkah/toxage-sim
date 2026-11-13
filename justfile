# Tasks of toxage-sim. List them with: just
# Python runs in the environment that uv creates from pyproject.toml and uv.lock.

set shell := ["bash", "-euo", "pipefail", "-c"]

py := "uv run python"
manage := "uv run python app/manage.py"

# List the tasks
default:
    @just --list --unsorted

# --- Environment -----------------------------------------------------------

# Create or update the Python environment
setup:
    uv sync

# Update the locked package versions
lock:
    uv lock --upgrade

# --- Tests -----------------------------------------------------------------

# Run all tests
test: test-engine test-risk test-app test-js

# Tests of the data engine
test-engine:
    {{py}} -m unittest discover engine/tests

# Tests of the risk models
test-risk:
    {{py}} -m unittest discover risk-model/tests

# Tests of the app (Python)
test-app:
    cd app && uv run python manage.py test explorer

# Tests of the chart helpers of the app (needs Node.js)
# The shell expands the file pattern: node --test reads patterns itself only from Node.js 21 on.
test-js:
    cd app && node --test explorer/tests/*.test.mjs

# --- Engine ----------------------------------------------------------------

# Generate synthetic patients as CSV files, e.g.: just generate 3000 1 engine/output
generate n="3000" seed="1" out="engine/output" *scenarios="":
    {{py}} engine/generate.py --n {{n}} --seed {{seed}} --out {{out}} {{ if scenarios == "" { "" } else { "--scenarios " + scenarios } }}

# Match the event rates to the literature; needed after changes of model or parameters
calibrate:
    {{py}} engine/calibrate.py

# --- Risk models -----------------------------------------------------------

# Risk scores for generated patients, e.g.: just score engine/output
score data="engine/output" out="risk-model/output/risk_score.csv":
    {{py}} risk-model/score.py --baseline {{data}}/baseline.csv --out {{out}}

# Discrimination and calibration of the risk models on generated data
evaluate data="engine/output" *args="":
    {{py}} risk-model/evaluate.py --data {{data}} {{args}}

# Estimate the coefficients of the risk models from generated data
fit data="engine/output" out="risk-model/output/fitted.json":
    {{py}} risk-model/fit.py --data {{data}} --out {{out}}

# --- App -------------------------------------------------------------------

# Create or update the database of the app
migrate:
    {{manage}} migrate

# Start the app for development at http://localhost:8000
serve port="8000": migrate
    {{manage}} runserver {{port}}

# Generate a data set for the app from the command line, e.g.: just load 1500 1
load n="1500" seed="1" *args="":
    {{manage}} load_cohort --n {{n}} --seed {{seed}} {{args}}

# Start the app as in the container: gunicorn with one worker
serve-prod port="8000": migrate
    cd app && TOXAGE_DEBUG=0 TOXAGE_ALLOWED_HOSTS='*' uv run gunicorn toxage_app.wsgi --bind 0.0.0.0:{{port}} --workers 1 --threads 8 --timeout 120

# Delete the database of the app
reset-db:
    rm -f app/db.sqlite3 app/db.sqlite3-wal app/db.sqlite3-shm

# --- Docker ----------------------------------------------------------------

# Build the container image; the build stamp carries the commit
docker-build:
    GIT_COMMIT=$(git rev-parse --short HEAD) docker compose build

# Start the container at http://localhost:8000
docker-up:
    GIT_COMMIT=$(git rev-parse --short HEAD) docker compose up -d --build

# Stop the container; the data stay in the volume
docker-down:
    docker compose down

# Follow the log of the container
docker-logs:
    docker compose logs -f

# --- Housekeeping ----------------------------------------------------------

# Delete generated files: outputs and Python caches
clean:
    rm -rf engine/output risk-model/output
    find . -name __pycache__ -type d -not -path "./.venv/*" -prune -exec rm -rf {} +
