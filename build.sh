#!/usr/bin/env bash
# Render ejecuta esto en cada publicación, antes de arrancar la nueva versión.
# Las migraciones van aparte (preDeployCommand en render.yaml).
set -o errexit  # si un paso falla, la publicación se detiene y sigue la versión anterior

pip install -r requirements.txt
python manage.py collectstatic --no-input
