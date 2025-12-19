import json
import logging
import os
from typing import Literal, Optional

import pika

from .repository import Car

logger = logging.getLogger(__name__)
EventType = Literal["CREATE", "UPDATE", "DELETE"]


class RabbitMQEventPublisher:
    def __init__(self) -> None:
        self.exchange = "cars_events_exchange"
        self.queue = "cars_events_queue"

        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.vhost = os.getenv("RABBITMQ_VHOST", "/")

        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    def _connect(self):
        if self.connection and self.connection.is_open:
            return

        creds = pika.PlainCredentials(self.user, self.password)
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=creds,
            heartbeat=30,
            blocked_connection_timeout=30,
        )
        self.connection = pika.BlockingConnection(params)

    def _get_channel(self):
        self._connect()
        if self.channel is None or self.channel.is_closed:
            self.channel = self.connection.channel()

            # Ловим возвраты, если сообщение не смаршрутизировалось при mandatory=True [web:154]
            self.channel.add_on_return_callback(self._on_return)

        return self.channel

    def _on_return(self, ch, method, properties, body):
        logger.error(
            "Message returned (unroutable): reply_code=%s reply_text=%s exchange=%s routing_key=%s body=%s",
            method.reply_code,
            method.reply_text,
            method.exchange,
            method.routing_key,
            body.decode("utf-8", errors="ignore"),
        )

    def _ensure_topology(self):
        ch = self._get_channel()

        # FANOUT: routing_key игнорируется, всем привязанным очередям [web:237]
        ch.exchange_declare(exchange=self.exchange, exchange_type="fanout", durable=True)
        ch.queue_declare(queue=self.queue, durable=True)
        ch.queue_bind(exchange=self.exchange, queue=self.queue)

    def publish_event(self, event_type: EventType, car: Car) -> None:
        payload = {
            "eventType": event_type,
            "car": {
                "id": car.id,
                "firm": car.firm,
                "model": car.model,
                "year": car.year,
                "power": car.power,
                "color": car.color,
                "price": float(car.price) if car.price is not None else None,
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            self._ensure_topology()
            ch = self._get_channel()

            # Для fanout routing_key пустой [web:237]
            ch.basic_publish(
                exchange=self.exchange,
                routing_key="",
                body=body,
                mandatory=True,  # если exchange не сможет доставить -> вернется [web:154]
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
            logger.info("Published %s event for car_id=%s", event_type, car.id)

        except Exception:
            logger.exception("RabbitMQ publish failed")
            # сбрасываем, чтобы на следующем запросе пересоздалось
            try:
                if self.channel and self.channel.is_open:
                    self.channel.close()
            except Exception:
                pass
            try:
                if self.connection and self.connection.is_open:
                    self.connection.close()
            except Exception:
                pass
            self.channel = None
            self.connection = None


class CarRepositoryWithEvents:
    def __init__(self, repository, publisher: RabbitMQEventPublisher):
        self._repository = repository
        self._publisher = publisher

    def list_cars(self):
        return self._repository.list_cars()

    def get_car(self, car_id: int):
        return self._repository.get_car(car_id)

    def create_car(self, data):
        car = self._repository.create_car(data)
        self._publisher.publish_event("CREATE", car)
        return car

    def update_car(self, car_id: int, data):
        car = self._repository.update_car(car_id, data)
        if car is not None:
            self._publisher.publish_event("UPDATE", car)
        return car

    def delete_car(self, car_id: int) -> bool:
        car = self._repository.get_car(car_id)
        ok = self._repository.delete_car(car_id)
        if ok and car is not None:
            self._publisher.publish_event("DELETE", car)
        return ok
