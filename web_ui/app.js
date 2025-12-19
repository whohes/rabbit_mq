const API_BASE = "";

const statusEl = document.getElementById("status");
const carsContainer = document.getElementById("cars-container");
const searchInput = document.getElementById("search-id");
const searchBtn = document.getElementById("search-btn");
const reloadBtn = document.getElementById("reload-btn");

let carsCache = [];

function setStatus(message, type = "") {
  statusEl.textContent = message || "";
  statusEl.className = "status" + (type ? " status-" + type : "");
}

function buildImageUrl(car) {
  // Используем локальную заглушку вместо Unsplash
  return "/static/images.png";
}

function renderCars(cars, highlightId = null) {
  carsContainer.innerHTML = "";
  if (!cars.length) {
    carsContainer.innerHTML = "<p>Нет автомобилей</p>";
    return;
  }
  cars.forEach((car) => {
    const card = document.createElement("div");
    card.className = "car-card";
    card.dataset.id = car.id;
    if (highlightId && Number(highlightId) === car.id) {
      card.classList.add("highlight");
    }

    const img = document.createElement("img");
    img.className = "car-image";
    img.alt = car.firm + " " + car.model;
    img.src = buildImageUrl(car);
    card.appendChild(img);

    const body = document.createElement("div");
    body.className = "car-body";

    const title = document.createElement("div");
    title.className = "car-title";
    title.innerHTML = `
      <span>${car.firm} ${car.model}</span>
      <small>#${car.id}</small>
    `;
    body.appendChild(title);

    const attrs = document.createElement("div");
    attrs.className = "car-attrs";
    attrs.innerHTML = `
      <div><span class="car-attr-label">Год:</span> ${car.year}</div>
      <div><span class="car-attr-label">Мощность:</span> ${car.power} л.с.</div>
      <div><span class="car-attr-label">Цвет:</span> ${car.color}</div>
      <div><span class="car-attr-label">Цена:</span> ${car.price ?? "—"}</div>
      <div><span class="car-attr-label">Дилер ID:</span> ${car.dealer_id}</div>
    `;
    body.appendChild(attrs);

    const actions = document.createElement("div");
    actions.className = "car-actions";
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "REST";
    actions.appendChild(badge);

    const right = document.createElement("div");
    right.className = "car-actions-right";

    const editBtn = document.createElement("button");
    editBtn.className = "btn-secondary";
    editBtn.textContent = "Редактировать";
    editBtn.onclick = () => openEditForm(card, car);

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn-danger";
    deleteBtn.textContent = "Удалить";
    deleteBtn.onclick = () => deleteCar(car.id);

    right.appendChild(editBtn);
    right.appendChild(deleteBtn);
    actions.appendChild(right);

    body.appendChild(actions);
    card.appendChild(body);

    carsContainer.appendChild(card);
  });
}

function openEditForm(card, car) {
  const existingForm = card.querySelector(".edit-fields");
  if (existingForm) {
    existingForm.remove();
    return;
  }

  const form = document.createElement("div");
  form.className = "edit-fields";
  form.innerHTML = `
    <label>Фирма
      <input type="text" name="firm" value="${car.firm}" />
    </label>
    <label>Модель
      <input type="text" name="model" value="${car.model}" />
    </label>
    <label>Год
      <input type="number" name="year" value="${car.year}" />
    </label>
    <label>Мощность
      <input type="number" name="power" value="${car.power}" />
    </label>
    <label>Цвет
      <input type="text" name="color" value="${car.color}" />
    </label>
    <label>Цена
      <input type="number" step="0.01" name="price" value="${car.price ?? ""}" />
    </label>
    <label>Дилер ID
      <input type="number" name="dealer_id" value="${car.dealer_id}" />
    </label>
    <div style="grid-column: 1 / -1; display:flex; gap:6px; margin-top:4px;">
      <button type="button" class="btn-primary" id="save-${car.id}">Сохранить</button>
      <button type="button" class="btn-secondary" id="cancel-${car.id}">Отмена</button>
    </div>
  `;

  card.querySelector(".car-body").appendChild(form);

  document.getElementById("cancel-" + car.id).onclick = () => {
    form.remove();
  };
  document.getElementById("save-" + car.id).onclick = async () => {
    const data = Object.fromEntries(
      Array.from(form.querySelectorAll("input")).map((input) => [input.name, input.value])
    );
    try {
      const payload = {
        firm: String(data.firm || "").trim(),
        model: String(data.model || "").trim(),
        year: Number(data.year),
        power: Number(data.power),
        color: String(data.color || "").trim(),
        price: Number(data.price),
        dealer_id: Number(data.dealer_id),
      };
      setStatus("Сохраняем изменения для #" + car.id + "...");
      const resp = await fetch(API_BASE + "/cars/" + car.id, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error("Ошибка PUT: " + resp.status + " " + text);
      }
      setStatus("Изменения сохранены", "success");
      form.remove();
      await loadCars(car.id);
    } catch (err) {
      console.error(err);
      setStatus("Не удалось сохранить изменения: " + err.message, "error");
    }
  };
}

async function deleteCar(id) {
  if (!confirm("Удалить автомобиль #" + id + "?")) {
    return;
  }
  try {
    setStatus("Удаляем #" + id + "...");
    const resp = await fetch(API_BASE + "/cars/" + id, { method: "DELETE" });
    if (resp.status !== 204) {
      const text = await resp.text();
      throw new Error("Ошибка DELETE: " + resp.status + " " + text);
    }
    setStatus("Автомобиль удалён", "success");
    await loadCars();
  } catch (err) {
    console.error(err);
    setStatus("Не удалось удалить автомобиль: " + err.message, "error");
  }
}

async function loadCars(highlightId = null) {
  try {
    setStatus("Загружаем список автомобилей...");
    const resp = await fetch(API_BASE + "/cars");
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error("Ошибка GET /cars: " + resp.status + " " + text);
    }
    const cars = await resp.json();
    carsCache = cars;
    renderCars(cars, highlightId);
    setStatus("Загружено автомобилей: " + cars.length, "success");
  } catch (err) {
    console.error(err);
    setStatus("Не удалось загрузить список: " + err.message, "error");
  }
}

async function searchById() {
  const id = Number(searchInput.value);
  if (!id) {
    setStatus("Укажите корректный ID", "error");
    return;
  }
  const fromCache = carsCache.find((c) => c.id === id);
  if (fromCache) {
    renderCars(carsCache, id);
    const card = carsContainer.querySelector('[data-id="' + id + '"]');
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    setStatus("Автомобиль #" + id + " найден в текущем списке", "success");
    return;
  }
  try {
    setStatus("Ищем автомобиль #" + id + "...");
    const resp = await fetch(API_BASE + "/cars/" + id);
    if (resp.status === 404) {
      setStatus("Автомобиль #" + id + " не найден", "error");
      return;
    }
    if (!resp.ok) {
      const text = await resp.text();
      throw new Error("Ошибка GET /cars/" + id + ": " + resp.status + " " + text);
    }
    const car = await resp.json();
    renderCars([car], id);
    setStatus("Показан автомобиль #" + id, "success");
  } catch (err) {
    console.error(err);
    setStatus("Ошибка поиска: " + err.message, "error");
  }
}

searchBtn.addEventListener("click", searchById);
reloadBtn.addEventListener("click", () => loadCars());
searchInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    searchById();
  }
});

loadCars();
