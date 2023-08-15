web: gunicorn mpw.wsgi --log-file -
worker: celery worker --app=mpw.celery.app  --heartbeat-interval 30 --beat