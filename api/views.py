import json
from pathlib import Path

from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Dealer, Car
from .repository import CarRepository, CarData, car_to_dict
from .events import CarRepositoryWithEvents, RabbitMQEventPublisher

# Глобальный экземпляр publisher'а для переиспользования соединения
_rabbitmq_publisher = RabbitMQEventPublisher()


# Функция _parse_json больше не нужна, используем request.data из DRF


dealer_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "city": openapi.Schema(type=openapi.TYPE_STRING),
        "address": openapi.Schema(type=openapi.TYPE_STRING),
        "area": openapi.Schema(type=openapi.TYPE_STRING),
        "rating": openapi.Schema(type=openapi.TYPE_NUMBER),
    },
)

dealer_create_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["name", "city", "address", "area", "rating"],
    properties={
        "name": openapi.Schema(type=openapi.TYPE_STRING),
        "city": openapi.Schema(type=openapi.TYPE_STRING),
        "address": openapi.Schema(type=openapi.TYPE_STRING),
        "area": openapi.Schema(type=openapi.TYPE_STRING),
        "rating": openapi.Schema(type=openapi.TYPE_NUMBER),
    },
)

car_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "firm": openapi.Schema(type=openapi.TYPE_STRING),
        "model": openapi.Schema(type=openapi.TYPE_STRING),
        "year": openapi.Schema(type=openapi.TYPE_INTEGER),
        "power": openapi.Schema(type=openapi.TYPE_INTEGER),
        "color": openapi.Schema(type=openapi.TYPE_STRING),
        "price": openapi.Schema(type=openapi.TYPE_NUMBER),
        "dealer_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)

car_create_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["firm", "model", "year", "power", "color", "price", "dealer_id"],
    properties={
        "firm": openapi.Schema(type=openapi.TYPE_STRING),
        "model": openapi.Schema(type=openapi.TYPE_STRING),
        "year": openapi.Schema(type=openapi.TYPE_INTEGER),
        "power": openapi.Schema(type=openapi.TYPE_INTEGER),
        "color": openapi.Schema(type=openapi.TYPE_STRING),
        "price": openapi.Schema(type=openapi.TYPE_NUMBER),
        "dealer_id": openapi.Schema(type=openapi.TYPE_INTEGER),
    },
)


@api_view(["GET", "POST"])
@swagger_auto_schema(
    method="get",
    operation_summary="Получить список дилеров",
    responses={200: openapi.Response("Список дилеров", schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=dealer_schema))},
)
@swagger_auto_schema(
    method="post",
    operation_summary="Создать дилера",
    request_body=dealer_create_schema,
    responses={201: openapi.Response("ID созданного дилера", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={"id": openapi.Schema(type=openapi.TYPE_INTEGER)}))},
)
@api_view(["GET", "POST"])
def dealers_list(request):
    if request.method == "GET":
        dealers = [
            {
                "id": d.id,
                "name": d.name,
                "city": d.city,
                "address": d.address,
                "area": d.area,
                "rating": float(d.rating) if d.rating is not None else None,
            }
            for d in Dealer.objects.all().order_by("id")
        ]
        return Response(dealers)

    if request.method == "POST":
        data = request.data
        required = ["name", "city", "address", "area", "rating"]
        if any(k not in data for k in required):
            return Response({"error": "Missing required fields"}, status=400)
        dealer = Dealer.objects.create(
            name=data["name"],
            city=data["city"],
            address=data["address"],
            area=data["area"],
            rating=data["rating"],
        )
        return Response({"id": dealer.id}, status=201)


@swagger_auto_schema(
    method="get",
    operation_summary="Получить дилера по ID",
    responses={200: dealer_schema, 404: "Дилер не найден"},
)
@swagger_auto_schema(
    method="put",
    operation_summary="Обновить дилера",
    request_body=dealer_create_schema,
    responses={200: openapi.Response("ID обновлённого дилера", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={"id": openapi.Schema(type=openapi.TYPE_INTEGER)}))},
)
@swagger_auto_schema(
    method="delete",
    operation_summary="Удалить дилера",
    responses={204: "Дилер удалён", 404: "Дилер не найден"},
)
@api_view(["GET", "PUT", "DELETE"])
def dealer_detail(request, dealer_id: int):
    try:
        dealer = Dealer.objects.get(pk=dealer_id)
    except Dealer.DoesNotExist:
        return Response(status=404)

    if request.method == "GET":
        data = {
            "id": dealer.id,
            "name": dealer.name,
            "city": dealer.city,
            "address": dealer.address,
            "area": dealer.area,
            "rating": float(dealer.rating) if dealer.rating is not None else None,
        }
        return Response(data)

    if request.method == "PUT":
        data = request.data
        required = ["name", "city", "address", "area", "rating"]
        if any(k not in data for k in required):
            return Response({"error": "Missing required fields"}, status=400)
        dealer.name = data["name"]
        dealer.city = data["city"]
        dealer.address = data["address"]
        dealer.area = data["area"]
        dealer.rating = data["rating"]
        dealer.save()
        return Response({"id": dealer.id})

    if request.method == "DELETE":
        dealer.delete()
        return Response(status=204)


@swagger_auto_schema(
    method="get",
    operation_summary="Получить список автомобилей",
    operation_description="Возвращает список всех автомобилей. При создании/обновлении/удалении автомобиля отправляется событие в RabbitMQ.",
    responses={200: openapi.Response("Список автомобилей", schema=openapi.Schema(type=openapi.TYPE_ARRAY, items=car_schema))},
)
@swagger_auto_schema(
    method="post",
    operation_summary="Создать автомобиль",
    operation_description="Создаёт новый автомобиль и отправляет событие CREATE в RabbitMQ.",
    request_body=car_create_schema,
    responses={
        201: openapi.Response("ID созданного автомобиля", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={"id": openapi.Schema(type=openapi.TYPE_INTEGER)})),
        400: "Ошибка валидации или дилер не найден",
    },
)
@api_view(["GET", "POST"])
def cars_list(request):
    repo = CarRepositoryWithEvents(CarRepository(), _rabbitmq_publisher)

    if request.method == "GET":
        cars = [car_to_dict(c) for c in repo.list_cars()]
        return Response(cars)

    if request.method == "POST":
        data = request.data
        required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
        if any(k not in data for k in required):
            return Response({"error": "Missing required fields"}, status=400)
        # Проверка существования дилера внутри репозитория: вернёт исключение Dealer.DoesNotExist
        try:
            car_data = CarData.from_dict(data)
            car = repo.create_car(car_data)
        except Dealer.DoesNotExist:
            return Response({"error": "Dealer not found"}, status=400)
        return Response({"id": car.id}, status=201)


@swagger_auto_schema(
    method="get",
    operation_summary="Получить автомобиль по ID",
    responses={200: car_schema, 404: "Автомобиль не найден"},
)
@swagger_auto_schema(
    method="put",
    operation_summary="Обновить автомобиль",
    operation_description="Обновляет автомобиль и отправляет событие UPDATE в RabbitMQ.",
    request_body=car_create_schema,
    responses={
        200: openapi.Response("ID обновлённого автомобиля", schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={"id": openapi.Schema(type=openapi.TYPE_INTEGER)})),
        400: "Ошибка валидации или дилер не найден",
        404: "Автомобиль не найден",
    },
)
@swagger_auto_schema(
    method="delete",
    operation_summary="Удалить автомобиль",
    operation_description="Удаляет автомобиль и отправляет событие DELETE в RabbitMQ.",
    responses={204: "Автомобиль удалён", 404: "Автомобиль не найден"},
)
@api_view(["GET", "PUT", "DELETE"])
def car_detail(request, car_id: int):
    repo = CarRepositoryWithEvents(CarRepository(), _rabbitmq_publisher)

    car = repo.get_car(car_id)
    if car is None:
        return Response(status=404)

    if request.method == "GET":
        data = {
            "id": car.id,
            "firm": car.firm,
            "model": car.model,
            "year": car.year,
            "power": car.power,
            "color": car.color,
            "price": float(car.price) if car.price is not None else None,
            "dealer_id": car.dealer_id,
        }
        return Response(data)

    if request.method == "PUT":
        data = request.data
        required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
        if any(k not in data for k in required):
            return Response({"error": "Missing required fields"}, status=400)
        try:
            car_data = CarData.from_dict(data)
            car = repo.update_car(car_id, car_data)
        except Dealer.DoesNotExist:
            return Response({"error": "Dealer not found"}, status=400)
        if car is None:
            return Response(status=404)
        return Response({"id": car.id})

    if request.method == "DELETE":
        ok = repo.delete_car(car_id)
        if not ok:
            return Response(status=404)
        return Response(status=204)


def cars_ui(request):
    """Простой одностраничный UI поверх REST API."""
    from pathlib import Path
    import os

    base_dir = Path(__file__).resolve().parent.parent
    web_ui_dir = base_dir / "web_ui"

    # Читаем HTML
    html_path = web_ui_dir / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Встраиваем CSS и JS прямо в HTML
    css_path = web_ui_dir / "style.css"
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    js_path = web_ui_dir / "app.js"
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()

    # Встраиваем CSS и JS в HTML
    html = html.replace(
        '  <!-- CSS будет встроен через views.py -->',
        f'  <style>{css_content}</style>'
    )
    html = html.replace(
        '  <!-- JS будет встроен через views.py -->',
        f'  <script>{js_content}</script>'
    )

    return HttpResponse(html)
