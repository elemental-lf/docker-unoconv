broker_url = 'amqp://guest:guest@rabbitmq:5672'
result_backend = 'rpc://'
tasks_queues = 'docker-unoconv'
task_serializer = 'pickle'
accept_content = ['pickle']
result_serializer = 'pickle'
