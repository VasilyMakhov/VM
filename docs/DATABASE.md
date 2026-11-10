# База данных VM²

Документ описывает схему базы данных, назначение таблиц, связи, ограничения, справочники и типовые SQL-запросы.

- СУБД: **Firebird 5.1**
- Файл базы: `/db/wb_vasa.fdb`
- Кодировка: в текущей базе `NONE`, в скриптах развёртывания используется `UTF8`
- Подключение: `firebird-driver` из Python

> Почему в текущей базе `NONE`? Исторически база создавалась без явной кодировки. Firebird в этом режиме хранит байты как есть, а клиент интерпретирует их в своей кодировке. Для нового развёртывания правильнее использовать `UTF8`, что и делает `sql/00_create_database.sql`.

---

## 1. Общая схема

```text
                        ┌─────────────┐
                        │   ROLES     │
                        └──────┬──────┘
                               │ role_id
                        ┌──────▼──────┐
                        │   USERS     │
                        └──┬───┬───┬──┘
             seller_id     │   │   │ user_id
        ┌──────────────────┘   │   └──────────────────┐
        ▼                      │                      ▼
┌─────────────────┐            │              ┌──────────────┐
│ SELLER_PRODUCTS │            │              │    ORDERS    │
└───┬────────┬────┘            │              └──┬────────┬──┘
    │        │                 │                 │        │
    │        │ product_id      │                 │        │
    │        ▼                 │                 │        │
    │  ┌─────────────┐         │                 │        │
    │  │  PRODUCTS   │◄────────┼── FAVORITES ────┘        │
    │  └──────┬──────┘         │                          │
    │         │ category_id    │                          │
    │         ▼                │                          │
    │  ┌─────────────┐         │                          │
    │  │ CATEGORIES  │         │                          │
    │  └─────────────┘         │                          │
    │                          │                          │
    ▼                          ▼                          ▼
┌──────────────────┐   ┌──────────────┐          ┌──────────────┐
│ WAREHOUSE_PRODUCTS│  │  CART_ITEMS  │          │ ORDER_ITEMS  │
└────────┬─────────┘   └──────────────┘          └──────────────┘
         │ warehouse_id
         ▼
   ┌─────────────┐
   │ WAREHOUSES  │
   └─────────────┘

   ORDERS ──► ORDER_SELLERS ◄── USERS (seller_id)
```

Основные связи:

- пользователь имеет роль;
- продавец связан с товарами через `SELLER_PRODUCTS`;
- остатки товара продавца хранятся в `WAREHOUSE_PRODUCTS` по складам;
- покупатель хранит товары в `CART_ITEMS` и избранное в `FAVORITES`;
- заказ состоит из `ORDER_ITEMS`;
- заказ связан с продавцами через `ORDER_SELLERS`;
- статусы заказа, оплаты и доставки вынесены в справочники.

---

## 2. Справочники

### 2.1. `ROLES` — роли пользователей

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID роли |
| `NAME` | VARCHAR(50) | NOT NULL, UNIQUE | название роли |

Значения:

| ID | NAME |
|---|---|
| 1 | Пользователь |
| 2 | Продавец |
| 3 | Модератор |

### 2.2. `ORDER_STATUSES` — статусы заказа

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID статуса |
| `NAME` | VARCHAR(50) | NOT NULL, UNIQUE | название |

Значения:

| ID | NAME | Смысл |
|---|---|---|
| 1 | Новый | заказ создан |
| 2 | Подтверждён | оплата подтверждена продавцами |
| 3 | Собирается | зарезервирован |
| 4 | Передан в доставку | все продавцы передали товар |
| 5 | Доставлен | покупатель подтвердил получение |
| 6 | Отменён | зарезервирован |

### 2.3. `PAYMENT_METHODS` — способы оплаты

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID способа |
| `NAME` | VARCHAR(50) | NOT NULL, UNIQUE | название |

Значения:

| ID | NAME |
|---|---|
| 1 | СБП |
| 2 | При получении |

### 2.4. `PAYMENT_STATUSES` — статусы оплаты

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID статуса |
| `NAME` | VARCHAR(50) | NOT NULL, UNIQUE | название |

Значения:

| ID | NAME |
|---|---|
| 1 | Ожидает оплаты |
| 2 | Ожидает проверки |
| 3 | Оплачено |
| 4 | Отклонено |

### 2.5. `DELIVERY_STATUSES` — статусы доставки

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID статуса |
| `NAME` | VARCHAR(50) | NOT NULL, UNIQUE | название |

Значения:

| ID | NAME |
|---|---|
| 1 | Не отправлен |
| 2 | В пути |
| 3 | Доставлен |
| 4 | Отменён |

---

## 3. Основные таблицы

### 3.1. `USERS` — пользователи

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID пользователя |
| `LOGIN` | VARCHAR(50) | NOT NULL, UNIQUE | логин |
| `EMAIL` | VARCHAR(100) | NOT NULL, UNIQUE | почта |
| `PASSWORD` | VARCHAR(255) | NOT NULL | пароль (в открытом виде) |
| `FIRST_NAME` | VARCHAR(50) | NOT NULL | имя |
| `LAST_NAME` | VARCHAR(50) | NOT NULL | фамилия |
| `ROLE_ID` | INTEGER | NOT NULL, FK → `ROLES.ID` | роль |

Индексы/ограничения:

- `PK_USERS`;
- `UQ_USERS_LOGIN`;
- `UQ_USERS_EMAIL`;
- `FK_USERS_ROLE`.

Особенность: `LOGIN` и `EMAIL` уникальны независимо. При регистрации проверяется, что ни логин, ни почта не заняты.

### 3.2. `CATEGORIES` — категории товаров

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID категории |
| `NAME` | VARCHAR(100) | NOT NULL, UNIQUE | название |
| `DESCRIPTION` | BLOB SUB_TYPE TEXT | NULL | описание |

Категории может создавать только модератор. Удаление категории с товарами блокируется внешним ключом.

### 3.3. `WAREHOUSES` — склады

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID склада |
| `NAME` | VARCHAR(100) | NOT NULL | название |
| `ADDRESS` | VARCHAR(255) | NOT NULL | адрес |

Склады создаёт модератор. Остатки товаров привязаны к складам.

### 3.4. `PRODUCTS` — карточки товаров

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID товара |
| `CATEGORY_ID` | INTEGER | NOT NULL, FK → `CATEGORIES.ID` | категория |
| `NAME` | VARCHAR(150) | NOT NULL | название |
| `DESCRIPTION` | BLOB SUB_TYPE TEXT | NULL | описание |
| `IMAGE_URL` | VARCHAR(255) | NULL | путь к изображению |
| `PRICE` | DECIMAL(12,2) | NULL | цена |

Особенности:

- цена хранится с двумя знаками после запятой;
- `IMAGE_URL` хранит путь вида `/static/images/<uuid>.jpg`;
- физический файл лежит в `static/images/`;
- при удалении товара изображение удаляется из файловой системы (если это локальный файл).

### 3.5. `SELLER_PRODUCTS` — предложения продавцов

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID предложения |
| `SELLER_ID` | INTEGER | NOT NULL, FK → `USERS.ID` | продавец |
| `PRODUCT_ID` | INTEGER | NOT NULL, FK → `PRODUCTS.ID` | товар |

Ограничения:

- `UQ_SELLER_PRODUCTS (SELLER_ID, PRODUCT_ID)` — один продавец не может дважды добавить один товар.

Зачем нужна эта таблица:

- отделяет карточку товара от конкретного продавца;
- позволяет нескольким продавцам продавать один товар;
- является родителем для остатков и позиций заказа.

### 3.6. `WAREHOUSE_PRODUCTS` — остатки на складах

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID записи |
| `WAREHOUSE_ID` | INTEGER | NOT NULL, FK → `WAREHOUSES.ID` | склад |
| `SELLER_PRODUCT_ID` | INTEGER | NOT NULL, FK → `SELLER_PRODUCTS.ID` | предложение продавца |
| `QUANTITY` | INTEGER | NOT NULL, CHECK (`QUANTITY >= 0`) | количество |

Ограничения:

- `UQ_WAREHOUSE_SELLER_PRODUCT (WAREHOUSE_ID, SELLER_PRODUCT_ID)` — одна запись на пару «склад + предложение».

Суммарный остаток товара продавца:

```sql
SELECT COALESCE(SUM(QUANTITY), 0)
FROM WAREHOUSE_PRODUCTS
WHERE SELLER_PRODUCT_ID = ?;
```

### 3.7. `FAVORITES` — избранное

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID записи |
| `USER_ID` | INTEGER | NOT NULL, FK → `USERS.ID` | пользователь |
| `PRODUCT_ID` | INTEGER | NOT NULL, FK → `PRODUCTS.ID` | товар |

Ограничение:

- `UQ_FAVORITES_USER_PRODUCT (USER_ID, PRODUCT_ID)` — нельзя добавить один товар дважды.

### 3.8. `CART_ITEMS` — корзина

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID позиции |
| `USER_ID` | INTEGER | NOT NULL, FK → `USERS.ID` | пользователь |
| `QUANTITY` | INTEGER | NOT NULL, CHECK (`QUANTITY > 0`) | количество |
| `SELLER_PRODUCT_ID` | INTEGER | NOT NULL, FK → `SELLER_PRODUCTS.ID` | предложение |

Ограничение:

- `UQ_CART_USER_PRODUCT (USER_ID, SELLER_PRODUCT_ID)` — одна позиция на пару «пользователь + предложение».

### 3.9. `ORDERS` — заказы

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID заказа |
| `USER_ID` | INTEGER | NOT NULL, FK → `USERS.ID` | покупатель |
| `TOTAL_PRICE` | DECIMAL(10,2) | NOT NULL, CHECK (`TOTAL_PRICE >= 0`) | сумма |
| `STATUS_ID` | INTEGER | NOT NULL, FK → `ORDER_STATUSES.ID` | статус заказа |
| `DELIVERY_ADDRESS` | VARCHAR(255) | NOT NULL | адрес |
| `CREATED_AT` | TIMESTAMP | NOT NULL | дата создания |
| `PAYMENT_METHOD_ID` | INTEGER | FK → `PAYMENT_METHODS.ID` | способ оплаты |
| `PAYMENT_STATUS_ID` | INTEGER | FK → `PAYMENT_STATUSES.ID` | статус оплаты |
| `DELIVERY_STATUS_ID` | INTEGER | FK → `DELIVERY_STATUSES.ID` | статус доставки |

Обратите внимание: три поля `*_ID`, связанные со статусами, допускают `NULL` на уровне схемы, хотя приложение всегда их заполняет.

### 3.10. `ORDER_ITEMS` — позиции заказа

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID позиции |
| `ORDER_ID` | INTEGER | NOT NULL, FK → `ORDERS.ID` | заказ |
| `QUANTITY` | INTEGER | NOT NULL, CHECK (`QUANTITY > 0`) | количество |
| `PRICE` | DECIMAL(10,2) | NOT NULL, CHECK (`PRICE >= 0`) | цена на момент заказа |
| `SELLER_PRODUCT_ID` | INTEGER | NOT NULL, FK → `SELLER_PRODUCTS.ID` | предложение |

Важно: цена фиксируется в момент оформления заказа. Если продавец потом изменит цену товара, история заказа не изменится.

### 3.11. `ORDER_SELLERS` — продавцы в заказе

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `ID` | INTEGER | PK, NOT NULL | ID записи |
| `ORDER_ID` | INTEGER | NOT NULL, FK → `ORDERS.ID` | заказ |
| `SELLER_ID` | INTEGER | NOT NULL, FK → `USERS.ID` | продавец |
| `PAYMENT_CONFIRMED` | SMALLINT | NOT NULL, DEFAULT 0 | продавец подтвердил оплату |
| `HANDED_TO_DELIVERY` | SMALLINT | NOT NULL, DEFAULT 0 | продавец передал товар |

Ограничение:

- `UQ_ORDER_SELLERS (ORDER_ID, SELLER_ID)` — один продавец один раз в заказе.

Это ключевая таблица для мультипродавцовых заказов. Именно по ней определяется:

- какие продавцы участвуют в заказе;
- кто уже подтвердил оплату;
- кто уже передал товар;
- когда можно менять общий статус заказа.

---

## 4. Генераторы и триггеры

В Firebird нет `AUTO_INCREMENT`. Вместо этого используются генераторы (sequences) и `BEFORE INSERT`-триггеры.

### 4.1. Генераторы в чистой схеме

| Генератор | Таблица |
|---|---|
| `GEN_USERS_ID` | `USERS` |
| `GEN_CATEGORIES_ID` | `CATEGORIES` |
| `GEN_WAREHOUSES_ID` | `WAREHOUSES` |
| `GEN_PRODUCTS_ID` | `PRODUCTS` |
| `GEN_SELLER_PRODUCTS_ID` | `SELLER_PRODUCTS` |
| `GEN_WAREHOUSE_PRODUCTS_ID` | `WAREHOUSE_PRODUCTS` |
| `GEN_FAVORITES_ID` | `FAVORITES` |
| `GEN_CART_ITEMS_ID` | `CART_ITEMS` |
| `GEN_ORDERS_ID` | `ORDERS` |
| `GEN_ORDER_ITEMS_ID` | `ORDER_ITEMS` |
| `GEN_ORDER_SELLERS_ID` | `ORDER_SELLERS` |

### 4.2. Триггер

Пример:

```sql
CREATE TRIGGER BI_USERS_ID FOR USERS
ACTIVE BEFORE INSERT POSITION 0
AS
BEGIN
    IF (NEW.ID IS NULL) THEN
        NEW.ID = GEN_ID(GEN_USERS_ID, 1);
END
```

Логика:

- если `ID` не передан — взять следующее значение генератора;
- если `ID` передан явно (например, при заливке тестовых данных) — оставить его.

### 4.3. Особенность текущей базы

В текущей базе у `FAVORITES` два триггера:

- `BI_FAVORITES_ID` — использует `GEN_FAVORITES_ID`;
- `TRIGGER_BI_FAVORITES_ID` — использует `SEQ_FOR_FAVORITES_ID`.

Оба срабатывают до вставки и перезаписывают `NEW.ID`. В итоге ID всё равно уникален, но один генератор расходуется впустую. В чистом скрипте `sql/01_schema.sql` оставлен только один триггер.

---

## 5. Ограничения целостности

### 5.1. Первичные ключи

У всех таблиц есть первичный ключ `ID`.

### 5.2. Уникальность

| Ограничение | Таблица | Поля |
|---|---|---|
| `UQ_USERS_LOGIN` | `USERS` | `LOGIN` |
| `UQ_USERS_EMAIL` | `USERS` | `EMAIL` |
| `UQ_ROLES_NAME` | `ROLES` | `NAME` |
| `UQ_CATEGORIES_NAME` | `CATEGORIES` | `NAME` |
| `UQ_ORDER_STATUSES_NAME` | `ORDER_STATUSES` | `NAME` |
| `UQ_PAYMENT_METHODS_NAME` | `PAYMENT_METHODS` | `NAME` |
| `UQ_PAYMENT_STATUSES_NAME` | `PAYMENT_STATUSES` | `NAME` |
| `UQ_DELIVERY_STATUSES_NAME` | `DELIVERY_STATUSES` | `NAME` |
| `UQ_SELLER_PRODUCTS` | `SELLER_PRODUCTS` | `(SELLER_ID, PRODUCT_ID)` |
| `UQ_WAREHOUSE_SELLER_PRODUCT` | `WAREHOUSE_PRODUCTS` | `(WAREHOUSE_ID, SELLER_PRODUCT_ID)` |
| `UQ_FAVORITES_USER_PRODUCT` | `FAVORITES` | `(USER_ID, PRODUCT_ID)` |
| `UQ_CART_USER_PRODUCT` | `CART_ITEMS` | `(USER_ID, SELLER_PRODUCT_ID)` |
| `UQ_ORDER_SELLERS` | `ORDER_SELLERS` | `(ORDER_ID, SELLER_ID)` |

### 5.3. CHECK-ограничения

| Ограничение | Таблица | Условие |
|---|---|---|
| `CHK_CART_QUANTITY` | `CART_ITEMS` | `QUANTITY > 0` |
| `CHK_ORDERS_TOTAL_PRICE` | `ORDERS` | `TOTAL_PRICE >= 0` |
| `CHK_ORDER_ITEMS_PRICE` | `ORDER_ITEMS` | `PRICE >= 0` |
| `CHK_ORDER_ITEMS_QUANTITY` | `ORDER_ITEMS` | `QUANTITY > 0` |
| `CHK_WAREHOUSE_QUANTITY` | `WAREHOUSE_PRODUCTS` | `QUANTITY >= 0` |

### 5.4. Внешние ключи

| Таблица | Поле | Ссылается на |
|---|---|---|
| `USERS` | `ROLE_ID` | `ROLES.ID` |
| `PRODUCTS` | `CATEGORY_ID` | `CATEGORIES.ID` |
| `SELLER_PRODUCTS` | `SELLER_ID` | `USERS.ID` |
| `SELLER_PRODUCTS` | `PRODUCT_ID` | `PRODUCTS.ID` |
| `WAREHOUSE_PRODUCTS` | `WAREHOUSE_ID` | `WAREHOUSES.ID` |
| `WAREHOUSE_PRODUCTS` | `SELLER_PRODUCT_ID` | `SELLER_PRODUCTS.ID` |
| `FAVORITES` | `USER_ID` | `USERS.ID` |
| `FAVORITES` | `PRODUCT_ID` | `PRODUCTS.ID` |
| `CART_ITEMS` | `USER_ID` | `USERS.ID` |
| `CART_ITEMS` | `SELLER_PRODUCT_ID` | `SELLER_PRODUCTS.ID` |
| `ORDERS` | `USER_ID` | `USERS.ID` |
| `ORDERS` | `STATUS_ID` | `ORDER_STATUSES.ID` |
| `ORDERS` | `PAYMENT_METHOD_ID` | `PAYMENT_METHODS.ID` |
| `ORDERS` | `PAYMENT_STATUS_ID` | `PAYMENT_STATUSES.ID` |
| `ORDERS` | `DELIVERY_STATUS_ID` | `DELIVERY_STATUSES.ID` |
| `ORDER_ITEMS` | `ORDER_ID` | `ORDERS.ID` |
| `ORDER_ITEMS` | `SELLER_PRODUCT_ID` | `SELLER_PRODUCTS.ID` |
| `ORDER_SELLERS` | `ORDER_ID` | `ORDERS.ID` |
| `ORDER_SELLERS` | `SELLER_ID` | `USERS.ID` |

Внешние ключи не имеют `ON DELETE CASCADE`. Поэтому удаление связано с проверками в коде:

- нельзя удалить категорию, если в ней есть товары;
- нельзя удалить склад, если к нему привязаны остатки;
- нельзя удалить товар, если он используется в заказах.

---

## 6. Индексы

В текущей базе явных индексов, кроме создаваемых под PK/UNIQUE, нет. В чистом скрипте `sql/01_schema.sql` добавлены индексы на внешние ключи, которые не покрываются уникальными ограничениями:

- `IDX_USERS_ROLE`;
- `IDX_PRODUCTS_CATEGORY`;
- `IDX_SELLER_PRODUCTS_PRODUCT`;
- `IDX_WAREHOUSE_PRODUCTS_SELLER_PRODUCT`;
- `IDX_FAVORITES_PRODUCT`;
- `IDX_CART_ITEMS_SELLER_PRODUCT`;
- `IDX_ORDERS_USER`, `IDX_ORDERS_STATUS`, `IDX_ORDERS_PAYMENT_STATUS`, `IDX_ORDERS_DELIVERY_STATUS`;
- `IDX_ORDER_ITEMS_ORDER`, `IDX_ORDER_ITEMS_SELLER_PRODUCT`;
- `IDX_ORDER_SELLERS_SELLER`.

Это ускоряет типовые выборки: заказы пользователя, товары продавца, остатки, избранное.

---

## 7. Типовые запросы

### 7.1. Каталог с фильтрами

```sql
SELECT p.ID, p.NAME, p.IMAGE_URL, p.PRICE
FROM PRODUCTS p
JOIN SELLER_PRODUCTS sp ON sp.PRODUCT_ID = p.ID
WHERE p.CATEGORY_ID = ?
  AND p.NAME CONTAINING ?
  AND p.PRICE >= ?
  AND p.PRICE <= ?
ORDER BY p.PRICE ASC;
```

### 7.2. Карточка товара с остатком

```sql
SELECT
    p.ID,
    p.NAME,
    p.DESCRIPTION,
    p.IMAGE_URL,
    c.NAME AS CATEGORY,
    p.PRICE,
    COALESCE(SUM(wp.QUANTITY), 0) AS QUANTITY
FROM PRODUCTS p
JOIN CATEGORIES c ON c.ID = p.CATEGORY_ID
JOIN SELLER_PRODUCTS sp ON sp.PRODUCT_ID = p.ID
LEFT JOIN WAREHOUSE_PRODUCTS wp ON wp.SELLER_PRODUCT_ID = sp.ID
WHERE p.ID = ?
GROUP BY p.ID, p.NAME, p.DESCRIPTION, p.IMAGE_URL, c.NAME, p.PRICE;
```

### 7.3. Товары продавца

```sql
SELECT p.ID, p.NAME, p.IMAGE_URL, p.PRICE
FROM PRODUCTS p
JOIN SELLER_PRODUCTS sp ON sp.PRODUCT_ID = p.ID
WHERE sp.SELLER_ID = ?
ORDER BY p.NAME;
```

### 7.4. Заказы продавца

```sql
SELECT
    o.ID,
    o.CREATED_AT,
    os.NAME AS ORDER_STATUS,
    pm.NAME AS PAYMENT_METHOD,
    ps.NAME AS PAYMENT_STATUS,
    ds.NAME AS DELIVERY_STATUS,
    o.DELIVERY_ADDRESS,
    u.LOGIN AS BUYER,
    ords.PAYMENT_CONFIRMED,
    ords.HANDED_TO_DELIVERY,
    p.NAME AS PRODUCT_NAME,
    oi.QUANTITY,
    oi.PRICE
FROM ORDER_SELLERS ords
JOIN ORDERS o ON o.ID = ords.ORDER_ID
JOIN ORDER_STATUSES os ON os.ID = o.STATUS_ID
JOIN PAYMENT_METHODS pm ON pm.ID = o.PAYMENT_METHOD_ID
JOIN PAYMENT_STATUSES ps ON ps.ID = o.PAYMENT_STATUS_ID
JOIN DELIVERY_STATUSES ds ON ds.ID = o.DELIVERY_STATUS_ID
JOIN USERS u ON u.ID = o.USER_ID
JOIN ORDER_ITEMS oi ON oi.ORDER_ID = o.ID
JOIN SELLER_PRODUCTS sp
    ON sp.ID = oi.SELLER_PRODUCT_ID
   AND sp.SELLER_ID = ords.SELLER_ID
JOIN PRODUCTS p ON p.ID = sp.PRODUCT_ID
WHERE ords.SELLER_ID = ?
ORDER BY o.CREATED_AT DESC, o.ID DESC, p.NAME;
```

### 7.5. Заказы покупателя

```sql
SELECT
    o.ID,
    o.CREATED_AT,
    o.TOTAL_PRICE,
    os.NAME,
    pm.NAME,
    ps.NAME,
    ds.NAME,
    o.STATUS_ID,
    o.DELIVERY_STATUS_ID
FROM ORDERS o
JOIN ORDER_STATUSES os ON os.ID = o.STATUS_ID
JOIN PAYMENT_METHODS pm ON pm.ID = o.PAYMENT_METHOD_ID
JOIN PAYMENT_STATUSES ps ON ps.ID = o.PAYMENT_STATUS_ID
JOIN DELIVERY_STATUSES ds ON ds.ID = o.DELIVERY_STATUS_ID
WHERE o.USER_ID = ?
ORDER BY o.CREATED_AT DESC;
```

### 7.6. Избранное пользователя

```sql
SELECT p.ID, p.NAME, p.IMAGE_URL, p.PRICE
FROM PRODUCTS p
JOIN FAVORITES f ON f.PRODUCT_ID = p.ID
WHERE f.USER_ID = ?;
```

### 7.7. Проверка остатка перед добавлением в корзину

```sql
SELECT COALESCE(SUM(QUANTITY), 0)
FROM WAREHOUSE_PRODUCTS
WHERE SELLER_PRODUCT_ID = ?;
```

### 7.8. Количество неподтверждённых продавцов

```sql
SELECT COUNT(*)
FROM ORDER_SELLERS
WHERE ORDER_ID = ?
  AND PAYMENT_CONFIRMED = 0;
```

Если результат `0` — все продавцы подтвердили оплату, можно переводить заказ в статус «Подтверждён».

---

## 8. Развёртывание базы с нуля

### 8.1. Автоматически

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh /db/wb_vasa.fdb
```

Скрипт:

1. проверяет наличие `isql-fb`;
2. создаёт базу;
3. применяет `sql/01_schema.sql`;
4. загружает `sql/02_seed.sql`;
5. выводит итоговую статистику.

### 8.2. Вручную

```bash
# создание базы
isql-fb -q -u SYSDBA -p masterkey -i sql/00_create_database.sql

# схема
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/01_schema.sql

# тестовые данные
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/02_seed.sql
```

### 8.3. Проверка

```bash
isql-fb -u SYSDBA -p masterkey /db/wb_vasa.fdb
```

В интерактивной консоли:

```sql
SELECT COUNT(*) FROM USERS;
SELECT COUNT(*) FROM PRODUCTS;
SELECT COUNT(*) FROM ORDERS;
SELECT * FROM ORDER_STATUSES;
```

### 8.4. Резервная копия и восстановление

Резервная копия:

```bash
gbak -b -v -user SYSDBA -password masterkey /db/wb_vasa.fdb /tmp/wb_vasa.fbk
```

Восстановление:

```bash
gbak -c -v -user SYSDBA -password masterkey /tmp/wb_vasa.fbk /db/wb_vasa_new.fdb
```

---

## 9. Тестовые данные

Скрипт `sql/02_seed.sql` загружает:

- 3 роли;
- 6 статусов заказа;
- 2 способа оплаты;
- 4 статуса оплаты;
- 4 статуса доставки;
- 13 категорий;
- 3 склада;
- 6 пользователей;
- 16 товаров;
- 16 предложений продавцов;
- 25 записей остатков на складах;
- 7 записей избранного;
- 4 позиции корзины;
- 6 заказов в разных статусах;
- 9 позиций заказов;
- 7 записей `ORDER_SELLERS`.

Тестовые заказы покрывают сценарии:

| Заказ | Покупатель | Статус | Что показывает |
|---|---|---|---|
| 1 | `testuser` | Новый, оплата ожидает проверки | продавец должен подтвердить оплату |
| 2 | `buyer2` | Подтверждён, оплачен | продавец может передать товар |
| 3 | `testuser` | Новый, мультипродавцовый | частичное подтверждение оплаты |
| 4 | `buyer2` | Передан в доставку | покупатель может подтвердить получение |
| 5 | `testuser` | Доставлен | завершённый заказ |
| 6 | `testuser` | Отменён | отменённый заказ |

---

## 10. Особенности Firebird, которые важно знать

1. **Нет `AUTO_INCREMENT`.** Используются генераторы + триггеры.
2. **Идентификаторы без кавычек приводятся к верхнему регистру.** `users` и `USERS` — одно и то же.
3. **Параметры запроса — `?`.** Драйвер подставляет значения безопасно.
4. **`CONTAINING`** ищет подстроку с учётом collateral-набора символов.
5. **`BLOB SUB_TYPE TEXT`** используется для длинных описаний.
6. **`DECIMAL`** возвращается драйвером как `decimal.Decimal`, а не `float`.
7. **Даты и время** — `TIMESTAMP`, в Python приходят как `datetime.datetime`.
8. **Кодировка.** Для кириллицы нужен `UTF8` и на уровне базы, и на уровне клиента (`-ch UTF8` в isql, `charset` в драйвере).
9. **Транзакции.** По умолчанию драйвер открывает транзакцию; после изменений нужен `commit()`, при ошибке — `rollback()`.
10. **Один файл — одна база.** Firebird хранит всю базу в одном `.fdb`-файле.

---

## 11. Полезные запросы для проверки

```sql
-- Пользователи и роли
SELECT u.ID, u.LOGIN, u.EMAIL, r.NAME
FROM USERS u
JOIN ROLES r ON r.ID = u.ROLE_ID
ORDER BY u.ID;

-- Товары и их продавцы
SELECT p.ID, p.NAME, p.PRICE, u.LOGIN AS SELLER
FROM PRODUCTS p
JOIN SELLER_PRODUCTS sp ON sp.PRODUCT_ID = p.ID
JOIN USERS u ON u.ID = sp.SELLER_ID
ORDER BY p.ID;

-- Остатки по товарам
SELECT p.NAME, w.NAME AS WAREHOUSE, wp.QUANTITY
FROM WAREHOUSE_PRODUCTS wp
JOIN SELLER_PRODUCTS sp ON sp.ID = wp.SELLER_PRODUCT_ID
JOIN PRODUCTS p ON p.ID = sp.PRODUCT_ID
JOIN WAREHOUSES w ON w.ID = wp.WAREHOUSE_ID
ORDER BY p.NAME, w.NAME;

-- Заказы со статусами
SELECT o.ID, u.LOGIN, o.TOTAL_PRICE,
       os.NAME AS ORDER_STATUS,
       ps.NAME AS PAYMENT_STATUS,
       ds.NAME AS DELIVERY_STATUS
FROM ORDERS o
JOIN USERS u ON u.ID = o.USER_ID
JOIN ORDER_STATUSES os ON os.ID = o.STATUS_ID
JOIN PAYMENT_STATUSES ps ON ps.ID = o.PAYMENT_STATUS_ID
JOIN DELIVERY_STATUSES ds ON ds.ID = o.DELIVERY_STATUS_ID
ORDER BY o.ID;
```
