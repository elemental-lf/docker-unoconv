[![Travis CI status](https://img.shields.io/travis/elemental-lf/docker-unoconv/master.svg?style=plastic&label=Travis%20CI)](https://travis-ci.org/elemental-lf/docker-unoconv)

# docker-unoconv

This repository contains a Docker image which can be used to generate previews and thumbnails from files in common 
office  document formats.  It uses [LibreOffice](https://www.libreoffice.org/) via 
[unoconv](https://github.com/unoconv/unoconv) for rendering and exposes several [Celery](http://www.celeryproject.org/) 
tasks to access this functionality. Documents are read and previews and thumbnails are written via
[PyFilesystem](https://www.pyfilesystem.org/), support for accessing S3 object stores via 
[`fs-s3`](https://fs-s3fs.readthedocs.io/) is included. This image is intended to be deployed with Kubernetes but can
also be used with Docker.

## Modes of operation

When instantiating the image as a container the mode the container should be running in needs to be specified. There
are two possible modes:

* `celery-worker`: In this mode a Celery worker is started which publishes four tasks with the following signatures:
    
    * `celery_unoconv.tasks.supported_import_format(*, mime_type: str = None, extension: str = None) -> bool`
    
        Returns a boolean value indicating if a document format is supported. Either `mime_type` or `extension` or both
        have to be set. The `extension` must include the leading dot.
    
    * `celery_unoconv.tasks.generate_preview_jpg(*, input_fs_url: str, input_file: str, output_fs_url: str,
        output_file: str, mime_type: str = None, extension: str = None, height: int = None, width: int = None,
        timeout: int = UNOCONV_DEFAULT_TIMEOUT)`
        
        This tasks renders the first page (or slide) of a document as a JPEG image. The document is read from 
        `input_fs_url`:`input_file` and the JPEG image is written to `output_fs_url`:`output_file`. `mime_type`
        and `extension` are interpreted just like as with `celery_unoconv.tasks.supported_import_format`. This `height` 
        and `width` specify the dimensions of the resulting image and are optional (i.e. they either must be set or 
        both be `None`). `timeout` specifies a timeout for the invoked `unoconv` command. If `extension` is `None` the 
        task tries to guess it from the supplied `input_file` name.
        
        Exceptions thrown:
        
        * `ValueError`: Input format is unsupported or the supplied dimensions are invalid
        * `FileNotFoundError`: Input file was not found
        * `RuntimeError`: All other cases
        
    * `celery_unoconv.tasks.generate_preview_png(*, input_fs_url: str, input_file: str, output_fs_url: str,
        output_file: str, mime_type: str = None, extension: str = None, height: int = None, width: int = None,
        timeout: int = UNOCONV_DEFAULT_TIMEOUT)`
        
        This task works just like `celery_unoconv.tasks.generate_preview_jpg` but generates a PNG image instead.
        
    * `celery_unoconv.tasks.generate_pdf(*, input_fs_url: str, input_file: str, output_fs_url: str,
        output_file: str, mime_type: str = None, extension: str = None, timeout: int = UNOCONV_DEFAULT_TIMEOUT)`
        
        Again this is similar to the last two task. But in this case a PDF document container *all* pages (or slides)
        is generated.    
    
    To configure the Celery workers to connect to the Celery backends the Celery configuration needs to be mounted as 
    `/celery-worker/config/celeryconfig.py` inside the container. It contains configuration variable assignments
    as per the Celery [documentation](http://docs.celeryproject.org/en/latest/userguide/configuration.html). To
    get the results of the tasks a result backend is needed.
    
    These tasks need to be called by name. It is possible to use `send_task` for this or to define a `signature` with
    one of the names above:
    
    ```python
    app = Celery()
    supported_import_format = app.signature('celery_unoconv.tasks.supported_import_format')
    generate_preview_jpg = app.signature('celery_unoconv.tasks.generate_preview_jpg')
    generate_preview_png = app.signature('celery_unoconv.tasks.generate_preview_png')
    generate_pdf = app.signature('celery_unoconv.tasks.generate_pdf')
    ``` 
    
* `unoconv-listener`: This mode starts `unoconv` as server process inside the container. This container is optional, but
    as the startup of LibreOffice is expensive it speeds things up and uses fewer resources. If this container is 
    not present, the `celery-worker` container starts up an `unoconv` server and LibreOffice instance by itself each 
    time a request comes in and terminates it again when done. 
        
The mode needs to be supplied as single argument to the container's entry-point. This is done via the 
Kubernetes `args` option in container specifications. When using `docker-compose` or Docker Swarm
this would be `command`.  

## Usage with Kubernetes

To deploy `docker-unoconv` with Kubernetes it is best to use the provided Helm chart. It can be found in `charts/unoconv`.
If you're not using Helm the manifest templates in `charts/unoconv/templates` will still be a good starting point
for building your own manifests.

The Helm chart comes with a few configuration options:

The `unoconv` listener can be disabled by setting `containers.unoconvListener.enabled` to `false`. But normally it
should always be enabled.

```yaml
containers:
  unoconvListener:
    enabled: true
```

The configuration for the Celery worker needs to be supplied under the key `containers.celeryWorker.config`. It is
injected into the container via a `ConfigMap`.

```yaml
containers:
  celeryWorker:
    config:
      broker_url = 'amqp://guest:guest@rabbitmq:5672'
      result_backend = 'rpc://'
      tasks_queues = 'unoconv'
```

By default the deployment consists of five pods. The Celery workers are just started with one worker process per pod, 
so they need to be scaled by increasing the number of `replicas`. This can be done automatically be enabling the 
horizontal autoscaler below.

```yaml
replicaCount: 5 
```
With the standard settings the Helm chart will use the `latest` image. For production deployment it is recommended 
to specify a release version instead of using `latest`. In that case the `pullPolicy` should be set to `IfNotPresent`.

```yaml
image:
  repository: elementalnet/unoconv
  tag: latest
  pullPolicy: Always
```

To access documents residing on a filesystem a data volume can be mounted into the Celery worker container:

```yaml
containers:
  celeryWorker:
    dataVolume:
      enabled: false
      # Mount path inside the Celery worker container
      mountPath: /data
      reference:
        persistentVolumeClaim:
          claimName: your-pvc
```
It is also possible to specify resources. Currently both containers use the same resource allocation. This
might turn out to be suboptimal and separate resource specifications might be needed in the future. A horizontal
pod autoscaler can be enabled to adjust the number of `replicas` automatically.

```yaml
resources: {}
  # limits:
  #  cpu: 100m
  #  memory: 128Mi
  # requests:
  #  cpu: 100m
  #  memory: 128Mi

horizontalPodAutoscaler:
  # Remember to set resources above if you enable this
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 50
```

The last three options relate to pod placement:

```yaml
nodeSelector: {}

tolerations: []

affinity: {}  
```

## Usage with Docker

Please see `tests/docker-compose.yaml` for an example on how to use this image with Docker.

## Available images

A pre-built Docker image is present on Docker Hub under https://hub.docker.com/r/elementalnet/unoconv. The current
master branch is available under the tags `latest` and `master`. Releases are available with their respective
version as the tag. All images are built automatically via Travis CI.
