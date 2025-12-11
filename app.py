from flask import Flask, jsonify, request, abort
import psycopg2
import os

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("PG_DB", "cars_db"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "rms100605"),
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
    )


@app.get("/dealers")
def list_dealers():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, city, address, area, rating FROM dealers ORDER BY id")
            rows = cur.fetchall()
    dealers = [
        {
            "id": r[0],
            "name": r[1],
            "city": r[2],
            "address": r[3],
            "area": r[4],
            "rating": float(r[5]) if r[5] is not None else None,
        }
        for r in rows
    ]
    return jsonify(dealers)


@app.get("/dealers/<int:dealer_id>")
def get_dealer(dealer_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, city, address, area, rating FROM dealers WHERE id=%s",
                (dealer_id,),
            )
            r = cur.fetchone()
    if not r:
        abort(404)
    dealer = {
        "id": r[0],
        "name": r[1],
        "city": r[2],
        "address": r[3],
        "area": r[4],
        "rating": float(r[5]) if r[5] is not None else None,
    }
    return jsonify(dealer)


@app.post("/dealers")
def create_dealer():
    data = request.get_json(silent=True) or {}
    required = ["name", "city", "address", "area", "rating"]
    if any(k not in data for k in required):
        abort(400)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dealers (name, city, address, area, rating)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (data["name"], data["city"], data["address"], data["area"], data["rating"]),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    return jsonify({"id": new_id}), 201


@app.put("/dealers/<int:dealer_id>")
def update_dealer(dealer_id: int):
    data = request.get_json(silent=True) or {}
    required = ["name", "city", "address", "area", "rating"]
    if any(k not in data for k in required):
        abort(400)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE dealers
                SET name=%s, city=%s, address=%s, area=%s, rating=%s
                WHERE id=%s
                """,
                (
                    data["name"],
                    data["city"],
                    data["address"],
                    data["area"],
                    data["rating"],
                    dealer_id,
                ),
            )
            if cur.rowcount == 0:
                abort(404)
            conn.commit()
    return jsonify({"id": dealer_id})


@app.delete("/dealers/<int:dealer_id>")
def delete_dealer(dealer_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM dealers WHERE id=%s", (dealer_id,))
            if cur.rowcount == 0:
                abort(404)
            conn.commit()
    return ("", 204)


@app.get("/cars")
def list_cars():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, firm, model, year, power, color, price, dealer_id FROM cars ORDER BY id"
            )
            rows = cur.fetchall()
    cars = [
        {
            "id": r[0],
            "firm": r[1],
            "model": r[2],
            "year": r[3],
            "power": r[4],
            "color": r[5],
            "price": float(r[6]) if r[6] is not None else None,
            "dealer_id": r[7],
        }
        for r in rows
    ]
    return jsonify(cars)


@app.get("/cars/<int:car_id>")
def get_car(car_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, firm, model, year, power, color, price, dealer_id FROM cars WHERE id=%s",
                (car_id,),
            )
            r = cur.fetchone()
    if not r:
        abort(404)
    car = {
        "id": r[0],
        "firm": r[1],
        "model": r[2],
        "year": r[3],
        "power": r[4],
        "color": r[5],
        "price": float(r[6]) if r[6] is not None else None,
        "dealer_id": r[7],
    }
    return jsonify(car)


@app.post("/cars")
def create_car():
    data = request.get_json(silent=True) or {}
    required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
    if any(k not in data for k in required):
        abort(400)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cars (firm, model, year, power, color, price, dealer_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    data["firm"],
                    data["model"],
                    data["year"],
                    data["power"],
                    data["color"],
                    data["price"],
                    data["dealer_id"],
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    return jsonify({"id": new_id}), 201


@app.put("/cars/<int:car_id>")
def update_car(car_id: int):
    data = request.get_json(silent=True) or {}
    required = ["firm", "model", "year", "power", "color", "price", "dealer_id"]
    if any(k not in data for k in required):
        abort(400)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cars
                SET firm=%s, model=%s, year=%s, power=%s, color=%s, price=%s, dealer_id=%s
                WHERE id=%s
                """,
                (
                    data["firm"],
                    data["model"],
                    data["year"],
                    data["power"],
                    data["color"],
                    data["price"],
                    data["dealer_id"],
                    car_id,
                ),
            )
            if cur.rowcount == 0:
                abort(404)
            conn.commit()
    return jsonify({"id": car_id})


@app.delete("/cars/<int:car_id>")
def delete_car(car_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cars WHERE id=%s", (car_id,))
            if cur.rowcount == 0:
                abort(404)
            conn.commit()
    return ("", 204)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


