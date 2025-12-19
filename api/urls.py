from django.urls import path

from . import views

urlpatterns = [
    # Dealers
    path("dealers", views.dealers_list),
    path("dealers/<int:dealer_id>", views.dealer_detail),
    # Cars
    path("cars", views.cars_list),
    path("cars/<int:car_id>", views.car_detail),
    # Simple UI for cars
    path("cars-ui", views.cars_ui),
]


