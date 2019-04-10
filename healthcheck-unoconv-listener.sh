#!/usr/bin/env bash

if timeout 60 unoconv -n -f jpg -o /tmp/example.jpg /example.docx; then
    echo 'SUCCESS: unoconv listener is running successfully'
    exit 0
else
    echo 'FAILURE: unoconv listener has failed'
    exit 1
fi
