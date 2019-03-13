#!/usr/bin/env bash

if [ $# != 1 -o "$1" == "help" ];
then
    1>&2 cat <<EOF
    Please run this image with one of these commands:

    unoconv-listener Run the unoconv listener
    celery-worker    Run the unoconv Celery worker
EOF
    exit 64 # EX_USAGE
fi

COMMAND="$1"
case "$COMMAND" in
    unoconv-listener)
        /usr/bin/dumb-init -- /usr/bin/unoconv --listener --server=127.0.0.1 --port=2002 -v
    ;;
    celery-worker)
        export PYTHONPATH=/celery-worker/lib
        exec /usr/bin/dumb-init -- /usr/local/bin/celery worker --loglevel=INFO --task-events \
                        --concurrency=1 -n "${POD_NAME:-%h}" -A celery_unoconv
    ;;
    *)
        echo 'Unknown command. Valid commands are "unoconv-listener" and "celery-worker".' 1>&2
        exit 64 # EX_USAGE
    ;;
esac

# Not reached
exit 0
