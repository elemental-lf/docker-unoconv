#!/bin/bash

set -euo pipefail

function mc 
{
  port=$1; shift
  command="$@"
  
  docker run -it --net=host --entrypoint=/bin/sh minio/mc -c "/usr/bin/mc -q --insecure config host add s3 http://localhost:$port/ minio minio123; /usr/bin/mc -q --insecure $command"
}

mc 9000 mb s3/unoconv
