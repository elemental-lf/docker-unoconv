# Running the test setup

The `docker-compose.yml` file provides a basic test setup.

Start the environment with:
```bash
$ docker-compose up
```

If you want to have multiple workers use:
```bash
$ docker-compose up --scale worker=3
```