import sys
import os


broker_url = 'amqp://guest:guest@rabbitmq:5672'
result_backend = "rpc://"
tasks_queues = "unoconv"
broker_heartbeat = None

"""
Set config values based on environment variables
environment variables should be prefixed with the value of
CELERY_CONFIG_PREFIX (defaults to: CELERY_) 
"""
config_prefix = os.getenv("CELERY_CONFIG_PREFIX", "CELERY_")
celery_vars = {
    varname[len(config_prefix) :].lower(): os.environ[varname]
    for varname in os.environ.keys()
    if varname.startswith(config_prefix)
}

this_module = sys.modules[__name__]
for config_name, config_value in celery_vars.items():
    setattr(this_module, config_name, config_value)
