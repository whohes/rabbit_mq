"""Модуль для работы с событиями RabbitMQ."""
import json
import logging
import os
import time
from typing import Literal

import pika
import pika.exceptions

from .repository import Car

logger = logging.getLogger(__name__)

EventType = Literal["CREATE", "UPDATE", "DELETE"]


class RabbitMQEventPublisher:
    """Публикует события в RabbitMQ."""

    def __init__(self) -> None:
        self.exchange = "cars_events_exchange"
        self.queue = "cars_events_queue"
        self.connection = None
        self.channel = None
        self.routing_key = "cars_events"
        self.topology_ready = False
        self._setup_connection()
        self._create_topology()

    def _setup_connection(self):
        """Настройка параметров подключения."""
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.vhost = os.getenv("RABBITMQ_VHOST", "/")

    def _get_connection(self):
        """Создаёт или возвращает существующее подключение к RabbitMQ."""
        if self.connection is None or self.connection.is_closed:
            credentials = pika.PlainCredentials(self.user, self.password)
            params = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
            )
            self.connection = pika.BlockingConnection(params)
        return self.connection

    def _get_channel(self):
        """Создаёт или возвращает существующий канал."""
        connection = self._get_connection()
        if self.channel is None or self.channel.is_closed:
            self.channel = connection.channel()
        return self.channel

    def _create_topology(self):
        """Создаёт exchange и очередь при инициализации."""
        try:
            channel = self._get_channel()
            try:
                self._ensure_topology(channel)
                self.topology_ready = True
                logger.info(f"✅ Топология создана: exchange '{self.exchange}' -> queue '{self.queue}'")
            except Exception as e:
                if "EXCHANGE_TYPE_MISMATCH" in str(e):
                    logger.warning(f"Exchange '{self.exchange}' существует с другим типом, удаляем и пересоздаём...")
                    if self.channel and not self.channel.is_closed:
                        self.channel.close()
                    self.channel = None

                    channel = self._get_channel()
                    try:
                        try:
                            channel.queue_delete(queue=self.queue)
                            logger.info(f"Старая очередь '{self.queue}' удалена")
                        except Exception:
                            pass

                        channel.exchange_delete(exchange=self.exchange)
                        logger.info(f"Старый exchange '{self.exchange}' удалён")
                    except Exception as del_err:
                        logger.warning(f"Не удалось удалить старый exchange/очередь: {del_err}")

                    if self.channel and not self.channel.is_closed:
                        self.channel.close()
                    self.channel = None
                    channel = self._get_channel()

                    self._ensure_topology(channel)
                    self.topology_ready = True
                    logger.info(f"✅ Топология пересоздана: exchange '{self.exchange}' -> queue '{self.queue}'")
                else:
                    raise
        except Exception as e:
            logger.error(f"❌ Не удалось создать топологию при инициализации: {e}", exc_info=True)
            logger.warning("Топология будет создана при первой отправке события")
            self.topology_ready = False

    def _ensure_topology(self, channel):
        """Создаёт exchange и очередь, если их нет."""
        try:
            channel.exchange_declare(
                exchange=self.exchange,
                exchange_type="direct",
                durable=True,
            )
        except pika.exceptions.ChannelClosedByBroker as e:
            if "inequivalent arg 'type'" in str(e):
                raise Exception("EXCHANGE_TYPE_MISMATCH")
            else:
                raise

        try:
            channel.queue_declare(
                queue=self.queue,
                durable=True,
                auto_delete=False,
                exclusive=False,
            )
        except Exception:
            # Очередь уже существует - это нормально
            pass

        try:
            channel.queue_bind(
                exchange=self.exchange,
                queue=self.queue,
                routing_key=self.routing_key,
            )
        except Exception:
            # Привязка уже существует - это нормально
            pass

    def publish_event(self, event_type: EventType, car: Car) -> None:
        """Публикует событие в RabbitMQ."""
        event_data = {
            "eventType": event_type,
            "car": {
                "firm": car.firm,
                "model": car.model,
                "year": car.year,
                "power": car.power,
                "color": car.color,
                "price": float(car.price) if car.price is not None else None,
            },
        }

        body = json.dumps(event_data, ensure_ascii=False).encode("utf-8")

        try:
            channel = self._get_channel()

            if not self.topology_ready:
                self._ensure_topology(channel)
                self.topology_ready = True

            channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )

            self.connection.process_data_events(time_limit=0.1)

            logger.info(f"Событие {event_type} отправлено в RabbitMQ для автомобиля ID={car.id}")

        except Exception as e:
            logger.error(f"Ошибка отправки события в RabbitMQ: {e}", exc_info=True)
            if self.channel and self.channel.is_closed:
                self.channel = None
            if self.connection and self.connection.is_closed:
                self.connection = None


class CarRepositoryWithEvents:
    """Декоратор для CarRepository, добавляющий отправку событий в RabbitMQ."""

    def __init__(self, repository, publisher: RabbitMQEventPublisher):
        self._repository = repository
        self._publisher = publisher

    def list_cars(self):
        """Получить список всех автомобилей."""
        return self._repository.list_cars()

    def get_car(self, car_id: int):
        """Получить автомобиль по ID."""
        return self._repository.get_car(car_id)

    def create_car(self, data):
        """Создать автомобиль и отправить событие CREATE."""
        car = self._repository.create_car(data)
        self._publisher.publish_event("CREATE", car)
        return car

    def update_car(self, car_id: int, data):
        """Обновить автомобиль и отправить событие UPDATE."""
        car = self._repository.update_car(car_id, data)
        if car is not None:
            self._publisher.publish_event("UPDATE", car)
        return car

    def delete_car(self, car_id: int) -> bool:
        """Удалить автомобиль и отправить событие DELETE."""
        car = self._repository.get_car(car_id)
        result = self._repository.delete_car(car_id)
        if result and car is not None:
            self._publisher.publish_event("DELETE", car)
        return result

