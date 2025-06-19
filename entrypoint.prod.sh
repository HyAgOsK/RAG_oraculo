#!/bin/sh

python manage.py migrate --noinput &&
python manage.py collectstatic --noinput &&
python manage.py qcluster &

gunicorn core.wsgi