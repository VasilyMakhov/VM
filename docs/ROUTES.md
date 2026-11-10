# Маршруты и обработчики VM²

Документ содержит все HTTP-маршруты проекта, права доступа, используемые шаблоны и краткое описание логики.

Обозначения:

- **Гость** — пользователь без авторизации;
- **Пользователь** — любой авторизованный пользователь;
- **Покупатель** — роль 1;
- **Продавец** — роль 2;
- **Модератор** — роль 3;
- **Владелец** — пользователь, которому принадлежит объект (заказ, товар, запись).

---

## 1. Сводная таблица

| URL | Методы | Blueprint.Функция | Доступ | Шаблон | Назначение |
|---|---|---|---|---|---|
| `/` | GET | `main.index` | Гость / Пользователь | `index.html` | главная или личный кабинет |
| `/login` | GET, POST | `auth.login` | Гость | `login.html` | вход |
| `/register` | GET, POST | `auth.register` | Гость | `register.html` | регистрация |
| `/logout` | GET | `auth.logout` | Пользователь | — | выход |
| `/edit-profile` | GET, POST | `auth.edit_profile` | Пользователь | `edit_profile.html` | редактирование профиля |
| `/catalog` | GET | `catalog.catalog` | Все | `catalog.html` | каталог с фильтрами |
| `/product/<int:product_id>` | GET | `catalog.product` | Все | `product.html` | карточка товара |
| `/favorites` | GET | `favorites.favorites` | Пользователь | `favorites.html` | избранное |
| `/favorites/add/<int:product_id>` | POST | `favorites.favorites_add` | Пользователь | — | добавить в избранное |
| `/favorites/remove/<int:product_id>` | POST | `favorites.favorites_remove` | Пользователь | — | убрать из избранного |
| `/cart` | GET | `cart.cart` | Пользователь | `cart.html` | корзина |
| `/cart/add/<int:product_id>` | POST | `cart.cart_add` | Пользователь | — | добавить в корзину |
| `/cart/select` | POST | `cart.cart_select` | Пользователь | — | выбрать товары |
| `/cart/update/<int:cart_id>` | POST | `cart.cart_update` | Пользователь | — | изменить количество |
| `/cart/remove/<int:cart_id>` | POST | `cart.cart_remove` | Пользователь | — | удалить из корзины |
| `/checkout` | GET, POST | `orders.checkout` | Пользователь | `checkout.html` | оформление заказа |
| `/payment/sbp/<int:order_id>` | GET | `orders.sbp_payment` | Владелец | `sbp_payment.html` | страница оплаты СБП |
| `/payment/sbp/<int:order_id>/confirm` | POST | `orders.confirm_payment` | Владелец | — | «Я оплатил» |
| `/my-orders` | GET | `orders.my_orders` | Пользователь | `my_orders.html` | история заказов |
| `/orders/<int:order_id>/confirm-receipt` | POST | `orders.confirm_receipt` | Владелец | — | подтвердить получение |
| `/my-products` | GET | `catalog.my_products` | Продавец | `my_products.html` | товары продавца |
| `/my-products/create` | GET, POST | `catalog.create_product` | Продавец | `create_product.html` | создать товар |
| `/my-products/<int:product_id>/edit` | GET, POST | `catalog.edit_product` | Продавец + владелец | `edit_product.html` | редактировать товар |
| `/my-products/<int:product_id>/delete` | POST | `catalog.delete_product` | Продавец + владелец | — | удалить товар |
| `/seller-orders` | GET | `catalog.seller_orders` | Продавец | `seller_orders.html` | заказы продавца |
| `/seller-orders/<int:order_id>/confirm-payment` | POST | `catalog.seller_confirm_payment` | Продавец + участник заказа | — | подтвердить оплату |
| `/seller-orders/<int:order_id>/handover` | POST | `catalog.seller_handover` | Продавец + участник заказа | — | передать в доставку |
| `/moderator/categories` | GET | `moderator.categories_list` | Модератор | `moderator/categories.html` | список категорий |
| `/moderator/categories/add` | GET, POST | `moderator.category_add` | Модератор | `moderator/category_form.html` | добавить категорию |
| `/moderator/categories/<int:cat_id>/edit` | GET, POST | `moderator.category_edit` | Модератор | `moderator/category_form.html` | редактировать категорию |
| `/moderator/categories/<int:cat_id>/delete` | POST | `moderator.category_delete` | Модератор | — | удалить категорию |
| `/moderator/warehouses` | GET | `moderator.warehouses_list` | Модератор | `moderator/warehouses.html` | список складов |
| `/moderator/warehouses/add` | GET, POST | `moderator.warehouse_add` | Модератор | `moderator/warehouse_form.html` | добавить склад |
| `/moderator/warehouses/<int:wh_id>/edit` | GET, POST | `moderator.warehouse_edit` | Модератор | `moderator/warehouse_form.html` | редактировать склад |
| `/moderator/warehouses/<int:wh_id>/delete` | POST | `moderator.warehouse_delete` | Модератор | — | удалить склад |

---

## 2. Карта файлов и строк

| Файл | Строка | Функция |
|---|---|---|
| `app.py` | 1–26 | создание приложения и регистрация blueprints |
| `db.py` | 4–9 | `get_connection()` |
| `routes/main.py` | 6–29 | `index()` |
| `routes/auth.py` | 7–39 | `login()` |
| `routes/auth.py` | 41–92 | `register()` |
| `routes/auth.py` | 94–97 | `logout()` |
| `routes/auth.py` | 99–188 | `edit_profile()` |
| `routes/catalog.py` | 10–28 | `remove_local_image()` |
| `routes/catalog.py` | 30–99 | `catalog()` |
| `routes/catalog.py` | 101–154 | `product()` |
| `routes/catalog.py` | 156–188 | `my_products()` |
| `routes/catalog.py` | 190–290 | `seller_orders()` |
| `routes/catalog.py` | 292–384 | `seller_confirm_payment()` |
| `routes/catalog.py` | 386–471 | `seller_handover()` |
| `routes/catalog.py` | 473–642 | `create_product()` |
| `routes/catalog.py` | 644–832 | `edit_product()` |
| `routes/catalog.py` | 834–898 | `delete_product()` |
| `routes/cart.py` | 6–78 | `cart_add()` |
| `routes/cart.py` | 80–137 | `cart()` |
| `routes/cart.py` | 139–167 | `cart_select()` |
| `routes/cart.py` | 169–235 | `cart_update()` |
| `routes/cart.py` | 237–271 | `cart_remove()` |
| `routes/orders.py` | 6–222 | `checkout()` |
| `routes/orders.py` | 224–250 | `sbp_payment()` |
| `routes/orders.py` | 252–286 | `confirm_payment()` |
| `routes/orders.py` | 288–326 | `my_orders()` |
| `routes/orders.py` | 328–392 | `confirm_receipt()` |
| `routes/favorites.py` | 6–44 | `favorites_add()` |
| `routes/favorites.py` | 46–83 | `favorites_remove()` |
| `routes/favorites.py` | 85–110 | `favorites()` |
| `routes/moderator.py` | 6–10 | `check_moderator_access()` |
| `routes/moderator.py` | 12–32 | `categories_list()` |
| `routes/moderator.py` | 34–60 | `category_add()` |
| `routes/moderator.py` | 62–112 | `category_edit()` |
| `routes/moderator.py` | 114–135 | `category_delete()` |
| `routes/moderator.py` | 137–157 | `warehouses_list()` |
| `routes/moderator.py` | 159–185 | `warehouse_add()` |
| `routes/moderator.py` | 187–237 | `warehouse_edit()` |
| `routes/moderator.py` | 239–258 | `warehouse_delete()` |

---

## 3. Подробное описание маршрутов

### 3.1. `main`

#### `GET /`

- **Функция:** `main.index`
- **Доступ:** все
- **Шаблон:** `index.html`

Если пользователь авторизован, загружает из БД:

- логин;
- почту;
- имя;
- фамилию;
- название роли.

и показывает личный кабинет. Иначе — приветственную страницу.

---

### 3.2. `auth`

#### `GET, POST /login`

- **Функция:** `auth.login`
- **Доступ:** гость
- **Шаблон:** `login.html`

POST-поля:

| Поле | Обязательное |
|---|---|
| `login` | да |
| `password` | да |

Логика:

1. Проверяет заполнение.
2. Ищет пользователя по логину.
3. Сравнивает пароль.
4. Записывает в сессию `user_id`, `user_login`, `user_role`.
5. Перенаправляет в каталог.

При ошибке возвращает `400` и шаблон с сообщением.

#### `GET, POST /register`

- **Функция:** `auth.register`
- **Доступ:** гость
- **Шаблон:** `register.html`

POST-поля:

| Поле | Обязательное | Примечание |
|---|---|---|
| `login` | да | уникальный |
| `email` | да | уникальный |
| `password` | да | без хеширования |
| `first_name` | да | |
| `last_name` | да | |
| `role_id` | да | `1` — покупатель, `2` — продавец |

Проверки:

- все поля заполнены;
- роль только `1` или `2`;
- логин и почта не заняты.

#### `GET /logout`

- **Функция:** `auth.logout`
- Очищает сессию и перенаправляет на главную.

#### `GET, POST /edit-profile`

- **Функция:** `auth.edit_profile`
- **Доступ:** авторизованный пользователь
- **Шаблон:** `edit_profile.html`

POST-поля:

| Поле | Обязательное |
|---|---|
| `login` | да |
| `email` | да |
| `first_name` | да |
| `last_name` | да |
| `password` | нет |

Если пароль пустой — он не меняется. Проверяется уникальность логина и почты среди других пользователей.

---

### 3.3. `catalog`

#### `GET /catalog`

- **Функция:** `catalog.catalog`
- **Доступ:** все
- **Шаблон:** `catalog.html`

Query-параметры:

| Параметр | Пример | Назначение |
|---|---|---|
| `category` | `1` | ID категории |
| `search` | `наушники` | поиск по названию (`CONTAINING`) |
| `min_price` | `1000` | минимальная цена |
| `max_price` | `5000` | максимальная цена |
| `sort` | `price_asc`, `price_desc`, `name` | сортировка |

#### `GET /product/<int:product_id>`

- **Функция:** `catalog.product`
- **Доступ:** все
- **Шаблон:** `product.html`

Показывает:

- название;
- описание;
- изображение;
- категорию;
- цену;
- суммарный остаток;
- кнопку «Добавить в корзину»;
- кнопку избранного (если пользователь авторизован).

#### `GET /my-products`

- **Функция:** `catalog.my_products`
- **Доступ:** продавец
- **Шаблон:** `my_products.html`

Список товаров текущего продавца.

#### `GET, POST /my-products/create`

- **Функция:** `catalog.create_product`
- **Доступ:** продавец
- **Шаблон:** `create_product.html`

POST-поля:

| Поле | Обязательное | Примечание |
|---|---|---|
| `name` | да | |
| `description` | да | |
| `category_id` | да | должен существовать |
| `price` | да | `Decimal`, неотрицательная |
| `image` | да | `.jpg`, `.jpeg`, `.png`, `.webp` |
| `quantity_<warehouse_id>` | да | целое ≥ 0 для каждого склада |

Создаёт:

1. `PRODUCTS`;
2. `SELLER_PRODUCTS`;
3. `WAREHOUSE_PRODUCTS` для каждого склада.

При ошибке удаляет загруженный файл и откатывает транзакцию.

#### `GET, POST /my-products/<int:product_id>/edit`

- **Функция:** `catalog.edit_product`
- **Доступ:** продавец + владелец товара
- **Шаблон:** `edit_product.html`

Позволяет изменить:

- название;
- категорию;
- описание;
- изображение (необязательно);
- цену;
- остатки по складам.

Если изображение не выбрано — старое остаётся. Если выбрано — новое сохраняется, старое удаляется после успешного коммита.

#### `POST /my-products/<int:product_id>/delete`

- **Функция:** `catalog.delete_product`
- **Доступ:** продавец + владелец товара

Удаляет:

1. `WAREHOUSE_PRODUCTS` продавца;
2. `SELLER_PRODUCTS`;
3. `PRODUCTS`.

Если товар используется в заказах, удаление упадёт на внешнем ключе и будет показано сообщение.

#### `GET /seller-orders`

- **Функция:** `catalog.seller_orders`
- **Доступ:** продавец
- **Шаблон:** `seller_orders.html`

Показывает заказы, в которых есть товары продавца. Для каждого заказа:

- дата;
- покупатель;
- адрес;
- товары продавца;
- сумма только по товарам продавца;
- статусы;
- флаги подтверждения оплаты и передачи.

#### `POST /seller-orders/<int:order_id>/confirm-payment`

- **Функция:** `catalog.seller_confirm_payment`
- **Доступ:** продавец, участвующий в заказе

Условия:

- способ оплаты — СБП (`PAYMENT_METHOD_ID = 1`);
- оплата ожидает проверки (`PAYMENT_STATUS_ID = 2`);
- заказ не в статусах 4, 5, 6.

Ставит `ORDER_SELLERS.PAYMENT_CONFIRMED = 1`. Если все продавцы подтвердили:

- `ORDERS.PAYMENT_STATUS_ID = 3`;
- `ORDERS.STATUS_ID = 2`.

#### `POST /seller-orders/<int:order_id>/handover`

- **Функция:** `catalog.seller_handover`
- **Доступ:** продавец, участвующий в заказе

Условия:

- заказ не в статусах 5, 6;
- доставка не в статусах 3, 4;
- оплата не отклонена (`PAYMENT_STATUS_ID != 4`);
- для СБП: продавец уже подтвердил оплату (`PAYMENT_CONFIRMED = 1`), а `PAYMENT_STATUS_ID` равен 2 или 3;
- для оплаты при получении (`PAYMENT_METHOD_ID = 2`) подтверждение оплаты не требуется.

Ставит `ORDER_SELLERS.HANDED_TO_DELIVERY = 1`. Если все продавцы передали товары:

- `ORDERS.STATUS_ID = 4`;
- `ORDERS.DELIVERY_STATUS_ID = 2`.

---

### 3.4. `cart`

#### `GET /cart`

- **Функция:** `cart.cart`
- **Доступ:** авторизованный пользователь
- **Шаблон:** `cart.html`

Показывает позиции корзины, остатки, выбранные товары, сумму и количество.

#### `POST /cart/add/<int:product_id>`

- **Функция:** `cart.cart_add`
- **Доступ:** авторизованный пользователь

Алгоритм:

1. Находит `SELLER_PRODUCTS` по `PRODUCT_ID`.
2. Считает суммарный остаток.
3. Ищет существующую позицию в корзине.
4. Если количество + 1 превышает остаток — ошибка.
5. Иначе вставляет новую позицию или увеличивает количество.

#### `POST /cart/select`

- **Функция:** `cart.cart_select`
- **Доступ:** авторизованный пользователь

Формы:

- `action=clear` — снять выбор;
- `select_all=1` — выбрать всё;
- `selected_items` — список ID позиций корзины.

Результат сохраняется в `session["cart_selected"]`.

#### `POST /cart/update/<int:cart_id>`

- **Функция:** `cart.cart_update`
- **Доступ:** авторизованный пользователь + владелец позиции

Поле `quantity`. Проверяет:

- количество ≥ 1;
- количество ≤ остатка.

#### `POST /cart/remove/<int:cart_id>`

- **Функция:** `cart.cart_remove`
- **Доступ:** авторизованный пользователь + владелец позиции

Удаляет позицию из `CART_ITEMS` и из `session["cart_selected"]`.

---

### 3.5. `orders`

#### `GET, POST /checkout`

- **Функция:** `orders.checkout`
- **Доступ:** авторизованный пользователь
- **Шаблон:** `checkout.html`

GET:

- берёт `cart_selected`;
- загружает выбранные позиции;
- считает сумму;
- загружает способы оплаты.

POST-поля:

| Поле | Обязательное |
|---|---|
| `delivery_address` | да |
| `payment_method_id` | да |

Создаёт заказ, строки `ORDER_SELLERS`, `ORDER_ITEMS`, списывает остатки и очищает выбранные позиции корзины.

Если способ оплаты — СБП, перенаправляет на `/payment/sbp/<order_id>`.

#### `GET /payment/sbp/<int:order_id>`

- **Функция:** `orders.sbp_payment`
- **Доступ:** владелец заказа
- **Шаблон:** `sbp_payment.html`

Показывает сумму и QR-код.

#### `POST /payment/sbp/<int:order_id>/confirm`

- **Функция:** `orders.confirm_payment`
- **Доступ:** владелец заказа

Ставит `PAYMENT_STATUS_ID = 2` («Ожидает проверки») для СБП-заказа со статусом 1.

#### `GET /my-orders`

- **Функция:** `orders.my_orders`
- **Доступ:** авторизованный пользователь
- **Шаблон:** `my_orders.html`

Список заказов пользователя со статусами.

#### `POST /orders/<int:order_id>/confirm-receipt`

- **Функция:** `orders.confirm_receipt`
- **Доступ:** владелец заказа

Требует:

- `STATUS_ID = 4`;
- `DELIVERY_STATUS_ID = 2`.

Ставит:

- `STATUS_ID = 5`;
- `DELIVERY_STATUS_ID = 3`;
- для оплаты при получении — `PAYMENT_STATUS_ID = 3`.

---

### 3.6. `favorites`

#### `GET /favorites`

- **Функция:** `favorites.favorites`
- **Доступ:** авторизованный пользователь
- **Шаблон:** `favorites.html`

Список избранных товаров.

#### `POST /favorites/add/<int:product_id>`

- **Функция:** `favorites.favorites_add`
- **Доступ:** авторизованный пользователь

Добавляет товар, если его ещё нет. Иначе показывает сообщение «Товар уже в избранном».

#### `POST /favorites/remove/<int:product_id>`

- **Функция:** `favorites.favorites_remove`
- **Доступ:** авторизованный пользователь

Удаляет товар из избранного.

---

### 3.7. `moderator`

Все маршруты требуют роль 3. Проверка — `check_moderator_access()`.

#### `GET /moderator/categories`

- **Функция:** `moderator.categories_list`
- **Шаблон:** `moderator/categories.html`

Список категорий.

#### `GET, POST /moderator/categories/add`

- **Функция:** `moderator.category_add`
- **Шаблон:** `moderator/category_form.html`

Поля:

- `name` — обязательно;
- `description` — обязательно.

#### `GET, POST /moderator/categories/<int:cat_id>/edit`

- **Функция:** `moderator.category_edit`
- **Шаблон:** `moderator/category_form.html`

Редактирование категории.

#### `POST /moderator/categories/<int:cat_id>/delete`

- **Функция:** `moderator.category_delete`

Удаление. Если в категории есть товары — ошибка внешнего ключа и сообщение пользователю.

#### `GET /moderator/warehouses`

- **Функция:** `moderator.warehouses_list`
- **Шаблон:** `moderator/warehouses.html`

Список складов.

#### `GET, POST /moderator/warehouses/add`

- **Функция:** `moderator.warehouse_add`
- **Шаблон:** `moderator/warehouse_form.html`

Поля:

- `name` — обязательно;
- `address` — обязательно.

#### `GET, POST /moderator/warehouses/<int:wh_id>/edit`

- **Функция:** `moderator.warehouse_edit`
- **Шаблон:** `moderator/warehouse_form.html`

Редактирование склада.

#### `POST /moderator/warehouses/<int:wh_id>/delete`

- **Функция:** `moderator.warehouse_delete`

Удаление. Если со складом связаны остатки — ошибка внешнего ключа.

---

## 4. Сессия

В cookie-сессии Flask хранятся:

| Ключ | Тип | Назначение |
|---|---|---|
| `user_id` | int | ID авторизованного пользователя |
| `user_login` | str | логин для отображения |
| `user_role` | int | роль: 1, 2 или 3 |
| `cart_selected` | list[int] | ID выбранных позиций корзины |

Сессия подписана `secret_key` из `app.py`. Данные хранятся на стороне клиента, поэтому не стоит класть туда секреты.

---

## 5. Flash-сообщения

Категории сообщений:

- `success` — успешная операция;
- `error` — ошибка;
- `info` — нейтральная информация.

Отображаются в `base.html` через `get_flashed_messages(with_categories=true)`.

---

## 6. HTTP-статусы

| Код | Когда |
|---|---|
| `200` | успешная страница |
| `302` | редирект после POST или при отсутствии прав |
| `400` | ошибка валидации формы (логин, регистрация, создание товара) |
| `404` | стандартный ответ Flask, если маршрут не найден |
| `500` | необработанное исключение |

---

## 7. Известные особенности маршрутов

1. **`/catalog` с некорректными числами.** `category=abc` или `min_price=abc` вызовут `ValueError` и `500`.
2. **`/cart/add/<product_id>` не различает продавцов.** Если товар продают несколько продавцов, берётся первая запись `SELLER_PRODUCTS`.
3. **GET-запрос `/logout`.** Выход через GET нарушает REST-подход, но для учебного проекта допустим.
4. **Нет CSRF-токенов.** Все POST-формы можно отправить с чужого сайта.
