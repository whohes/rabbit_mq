Контейнер для RabbitMQ

docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=guest -e RABBITMQ_DEFAULT_PASS=guest rabbitmq:3.13-management

Cоздание очереди

cars_events_queue

Создание exchange

cars_events_exchange
