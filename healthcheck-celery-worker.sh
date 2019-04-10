#!/usr/bin/env bash

export PYTHONPATH=/celery-worker/lib
HOSTNAME="$(hostname -f)"
if timeout 60 celery -A celery_unoconv status | grep -q "${POD_NAME:-$HOSTNAME}"':.*OK'; then
    echo 'SUCCESS: Celery worker is running successfully'
    exit 0
else
    echo 'FAILURE: Celery worker has failed'
    exit 1
fi
