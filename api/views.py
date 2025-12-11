import json

from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Dealer, Car
from .repository import CarRepository, CarData, car_to_dict
from .events import CarRepositoryWithEvents, RabbitMQEventPublisher

# Глобальный экземпляр publisher'а для переиспользования соединения
_rabbitmq_publisher = RabbitMQEventPublisher()


def _parse_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None
    return data


@csrf_exempt
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
        return JsonResponse(dealers, safe=False)

    if request.method == "POST":
        data = _parse_json(request) or {}
        required = ["name", "city", "address", "area", "rating"]
        if any(k not in data for k in required):
            return JsonResponse({"error": "Missing required fields"}, status=400)
        dealer = Dealer.objects.create(
            name=data["name"],
            city=data["city"],
            address=data["address"],
            area=data["area"],
            rating=data["rating"],
        )
        return JsonResponse({"id": dealer.id}, status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
def dealer_detail(request, dealer_id: int):
    try:
        dealer = Dealer.objects.get(pk=dealer_id)
    except Dealer.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == "GET":
        data = {
            "id": dealer.id,
            "name": dealer.name,
            "city": dealer.city,
            "address": dealer.address,
            "area": dealer.area,
            "rating": float(dealer.rating) if dealer.rating is not None else None,
        }
        return JsonResponse(data)

    if request.method == "PUT":
        data = _parse_json(request) or {}
        required = ["name", "city", "address", "area", "rating"]
        if any(k not in data for k in required):
            return JsonResponse({"error": "Missing required fields"}, status=400)
        dealer.name = data["name"]
        dealer.city = data["city"]
        dealer.address = data["address"]
        dealer.area = data["area"]
        dealer.rating = data["rating"]
        dealer.save()
        return JsonResponse({"id": dealer.id})

    if request.method == "DELETE":
        dealer.delete()
        return HttpResponse(status=204)

    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


@csrf_exempt
def cars_list(request):
    repo = CarRepositoryWithEvents(CarRepository(), _rabbitmq_publisher)

    if request.method == "GET":
        cars = [car_to_dict(c) for c in repo.list_cars()]
        return JsonResponse(cars, safe=False)

    if request.method == "POST":
        data = _parse_json(request) or {}
        required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
        if any(k not in data for k in required):
            return JsonResponse({"error": "Missing required fields"}, status=400)
        # Проверка существования дилера внутри репозитория: вернёт исключение Dealer.DoesNotExist
        try:
            car_data = CarData.from_dict(data)
            car = repo.create_car(car_data)
        except Dealer.DoesNotExist:
            return JsonResponse({"error": "Dealer not found"}, status=400)
        return JsonResponse({"id": car.id}, status=201)

    return HttpResponseNotAllowed(["GET", "POST"])


@csrf_exempt
def car_detail(request, car_id: int):
    repo = CarRepositoryWithEvents(CarRepository(), _rabbitmq_publisher)

    car = repo.get_car(car_id)
    if car is None:
        return HttpResponse(status=404)

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
        return JsonResponse(data)

    if request.method == "PUT":
        data = _parse_json(request) or {}
        required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
        if any(k not in data for k in required):
            return JsonResponse({"error": "Missing required fields"}, status=400)
        try:
            car_data = CarData.from_dict(data)
            car = repo.update_car(car_id, car_data)
        except Dealer.DoesNotExist:
            return JsonResponse({"error": "Dealer not found"}, status=400)
        if car is None:
            return HttpResponse(status=404)
        return JsonResponse({"id": car.id})

    if request.method == "DELETE":
        ok = repo.delete_car(car_id)
        if not ok:
            return HttpResponse(status=404)
        return HttpResponse(status=204)

    return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])



