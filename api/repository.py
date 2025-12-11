from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import List, Optional

from .models import Car, Dealer


@dataclass
class CarData:
    firm: str
    model: str
    year: int
    power: int
    color: str
    price: float
    dealer_id: int

    @classmethod
    def from_dict(cls, data: dict) -> "CarData":
        return cls(
            firm=data["firm"],
            model=data["model"],
            year=data["year"],
            power=data["power"],
            color=data["color"],
            price=data["price"],
            dealer_id=data["dealer_id"],
        )


def car_to_dict(car: Car) -> dict:
    return {
        "id": car.id,
        "firm": car.firm,
        "model": car.model,
        "year": car.year,
        "power": car.power,
        "color": car.color,
        "price": float(car.price) if car.price is not None else None,
        "dealer_id": car.dealer_id,
    }


class CarRepository:
    """Отвечает только за работу с БД (без событий)."""

    def list_cars(self) -> List[Car]:
        return list(Car.objects.all().order_by("id"))

    def get_car(self, car_id: int) -> Optional[Car]:
        try:
            return Car.objects.get(pk=car_id)
        except Car.DoesNotExist:
            return None

    def create_car(self, data: CarData) -> Car:
        dealer = Dealer.objects.get(pk=data.dealer_id)
        car = Car.objects.create(
            firm=data.firm,
            model=data.model,
            year=data.year,
            power=data.power,
            color=data.color,
            price=data.price,
            dealer=dealer,
        )
        return car

    def update_car(self, car_id: int, data: CarData) -> Optional[Car]:
        car = self.get_car(car_id)
        if car is None:
            return None
        dealer = Dealer.objects.get(pk=data.dealer_id)
        car.firm = data.firm
        car.model = data.model
        car.year = data.year
        car.power = data.power
        car.color = data.color
        car.price = data.price
        car.dealer = dealer
        car.save()
        return car

    def delete_car(self, car_id: int) -> bool:
        car = self.get_car(car_id)
        if car is None:
            return False
        car.delete()
        return True



