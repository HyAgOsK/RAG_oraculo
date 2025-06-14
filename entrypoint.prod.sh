python manage.py migrate --noinput &&
python manage.py collectstatic --noinput &&

python manage.py qcluster --noinput &&

gunicorn core.wsgi