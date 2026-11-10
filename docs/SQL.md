# SQL-скрипты развёртывания VM²

В каталоге `sql/` лежат скрипты, которые позволяют развернуть базу данных Firebird с нуля и заполнить её тестовыми данными.

---

## 1. Состав

| Файл | Назначение |
|---|---|
| `sql/00_create_database.sql` | создание пустой базы |
| `sql/01_schema.sql` | таблицы, первичные и внешние ключи, CHECK-ограничения, индексы, генераторы, триггеры |
| `sql/02_seed.sql` | справочники и тестовые данные |
| `sql/99_reset.sql` | удаление всех данных без удаления схемы |
| `scripts/init_db.sh` | автоматическое выполнение всех шагов |

---

## 2. Быстрый запуск

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh /db/wb_vasa.fdb
```

Скрипт:

1. проверяет наличие `isql-fb`;
2. проверяет, существует ли файл базы;
3. если существует — спрашивает подтверждение на удаление;
4. создаёт базу с кодировкой `UTF8`;
5. применяет схему;
6. загружает тестовые данные;
7. выводит количество пользователей, товаров и заказов.

### Параметры

```bash
./scripts/init_db.sh /путь/к/базе.fdb
```

Переменные окружения:

```bash
ISC_USER=SYSDBA ISC_PASSWORD=masterkey ISQL=isql-fb ./scripts/init_db.sh /db/wb_vasa.fdb
```

---

## 3. Ручной запуск

### 3.1. Создание базы

```bash
isql-fb -q -u SYSDBA -p masterkey -i sql/00_create_database.sql
```

Путь к файлу задаётся внутри скрипта:

```sql
CREATE DATABASE '/db/wb_vasa.fdb'
    USER 'SYSDBA'
    PASSWORD 'masterkey'
    PAGE_SIZE 8192
    DEFAULT CHARACTER SET UTF8;
```

Если нужен другой путь — отредактируйте строку `CREATE DATABASE`.

### 3.2. Схема

```bash
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/01_schema.sql
```

`-ch UTF8` важен для корректного чтения кириллицы из SQL-файла.

### 3.3. Тестовые данные

```bash
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/02_seed.sql
```

### 3.4. Проверка

```bash
isql-fb -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb
```

```sql
SELECT COUNT(*) FROM USERS;
SELECT COUNT(*) FROM PRODUCTS;
SELECT COUNT(*) FROM ORDERS;
SELECT * FROM ORDER_STATUSES;
```

---

## 4. Что создаёт схема

### 4.1. Таблицы

- `ROLES`;
- `USERS`;
- `CATEGORIES`;
- `WAREHOUSES`;
- `PRODUCTS`;
- `SELLER_PRODUCTS`;
- `WAREHOUSE_PRODUCTS`;
- `FAVORITES`;
- `CART_ITEMS`;
- `ORDER_STATUSES`;
- `PAYMENT_METHODS`;
- `PAYMENT_STATUSES`;
- `DELIVERY_STATUSES`;
- `ORDERS`;
- `ORDER_ITEMS`;
- `ORDER_SELLERS`.

### 4.2. Генераторы

`GEN_USERS_ID`, `GEN_CATEGORIES_ID`, `GEN_WAREHOUSES_ID`, `GEN_PRODUCTS_ID`, `GEN_SELLER_PRODUCTS_ID`, `GEN_WAREHOUSE_PRODUCTS_ID`, `GEN_FAVORITES_ID`, `GEN_CART_ITEMS_ID`, `GEN_ORDERS_ID`, `GEN_ORDER_ITEMS_ID`, `GEN_ORDER_SELLERS_ID`.

### 4.3. Триггеры

По одному `BEFORE INSERT`-триггеру на каждую таблицу, где нужен автогенерируемый `ID`.

### 4.4. Индексы

Добавлены индексы на внешние ключи, которые не покрываются `UNIQUE`-ограничениями. Это ускоряет выборки заказов, товаров, остатков и избранного.

---

## 5. Тестовые данные

`sql/02_seed.sql` создаёт:

- 6 пользователей;
- 13 категорий;
- 3 склада;
- 16 товаров;
- 16 предложений продавцов;
- 25 записей остатков;
- 7 записей избранного;
- 4 позиции корзины;
- 6 заказов;
- 9 позиций заказов;
- 7 записей `ORDER_SELLERS`.

### 5.1. Пользователи

| ID | Логин | Пароль | Роль |
|---|---|---|---|
| 1 | `testuser` | `123456` | покупатель |
| 2 | `seller1` | `123456` | продавец |
| 3 | `moderator` | `123456` | модератор |
| 4 | `$eller` | `qqqwww123` | продавец |
| 5 | `prodavan228` | `123456` | продавец |
| 6 | `buyer2` | `123456` | покупатель |

### 5.2. Заказы

| ID | Покупатель | Статус | Оплата | Доставка | Сценарий |
|---|---|---|---|---|---|
| 1 | `testuser` | 1 Новый | 2 Ожидает проверки | 1 Не отправлен | продавец подтверждает оплату |
| 2 | `buyer2` | 2 Подтверждён | 3 Оплачено | 1 Не отправлен | продавец передаёт товар |
| 3 | `testuser` | 1 Новый | 2 Ожидает проверки | 1 Не отправлен | мультипродавцовый заказ |
| 4 | `buyer2` | 4 Передан в доставку | 3 Оплачено | 2 В пути | покупатель подтверждает получение |
| 5 | `testuser` | 5 Доставлен | 3 Оплачено | 3 Доставлен | завершённый заказ |
| 6 | `testuser` | 6 Отменён | 4 Отклонено | 4 Отменён | отменённый заказ |

> Seed-скрипт ссылается на изображения, которые уже лежат в `static/images/` и отслеживаются git. Если удалить эти файлы, карточки товаров останутся без картинок.

---

## 6. Очистка данных

```bash
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/99_reset.sql
```

Скрипт удаляет все строки из всех таблиц и сбрасывает генераторы в 0. Схема остаётся.

После очистки можно снова выполнить:

```bash
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/02_seed.sql
```

> **Осторожно:** `99_reset.sql` удаляет все данные без подтверждения. Не запускайте его на рабочей базе.

---

## 7. Резервное копирование

### 7.1. Создание резервной копии

```bash
gbak -b -v -user SYSDBA -password masterkey /db/wb_vasa.fdb /tmp/wb_vasa.fbk
```

### 7.2. Восстановление

```bash
gbak -c -v -user SYSDBA -password masterkey /tmp/wb_vasa.fbk /db/wb_vasa_restored.fdb
```

### 7.3. Восстановление с заменой

```bash
gbak -c -r -v -user SYSDBA -password masterkey /tmp/wb_vasa.fbk /db/wb_vasa.fdb
```

`-r` означает `replace`.

---

## 8. Возможные проблемы

### 8.1. `isql-fb: command not found`

Установите клиент Firebird:

```bash
# Debian/Ubuntu
sudo apt install firebird-utils

# Fedora/RHEL
sudo dnf install firebird-utils
```

### 8.2. `I/O error ... permission denied`

Пользователь, под которым работает Firebird, не может создать файл в каталоге. Проверьте права на каталог:

```bash
ls -ld /db
```

Каталог должен быть доступен на запись пользователю Firebird (обычно `firebird` или `reddatabase`).

### 8.3. `Database already opened with engine instance`

База уже открыта другим процессом или другой версией клиента. Закройте приложение и повторите.

### 8.4. Кириллица превращается в «кракозябры»

Проверьте:

- база создана с `DEFAULT CHARACTER SET UTF8`;
- isql запускается с `-ch UTF8`;
- SQL-файл сохранён в UTF-8.

### 8.5. `CREATE DATABASE` не выполняется

Убедитесь, что:

- путь к файлу существует и доступен;
- в каталоге нет файла с таким именем;
- у пользователя Firebird есть права на создание файла;
- `isql-fb` подключён к нужному серверу.

### 8.6. После seed не работает вход

Проверьте, что `db.py` указывает на ту базу, которую вы создали:

```python
database="/db/wb_vasa.fdb"
```

И что seed действительно выполнился:

```sql
SELECT COUNT(*) FROM USERS;
```

Должно быть 6.

---

## 9. Отличия чистого скрипта от текущей базы

`sql/01_schema.sql` — это **исправленная и упорядоченная** версия схемы. Отличия от текущей `/db/wb_vasa.fdb`:

| Что | Текущая база | Чистый скрипт |
|---|---|---|
| Кодировка | `NONE` | `UTF8` |
| Триггеры `FAVORITES` | два триггера | один |
| Имена генераторов | смесь `GEN_*` и `SEQ_FOR_*` | единые `GEN_*` |
| Индексы на FK | нет | есть |
| Имена триггеров | разные | единые `BI_*` |
| Категории/склады | генераторы `SEQ_FOR_*` | `GEN_CATEGORIES_ID`, `GEN_WAREHOUSES_ID` |

Это не меняет логику приложения: все имена таблиц, колонок и ограничений совместимы с кодом.

---

## 10. Как адаптировать скрипт под другую базу

1. Измените путь в `sql/00_create_database.sql`.
2. Измените путь и пароль в `db.py`.
3. При необходимости измените логин/пароль в командах `isql-fb`.
4. Если база уже существует — используйте только `sql/01_schema.sql` и `sql/02_seed.sql` на пустой базе, либо `sql/99_reset.sql` + `sql/02_seed.sql` для перезаливки данных.

---

## 11. Почему данные вставляются с явными ID

В seed-скрипте у всех строк указаны явные `ID`. Это сделано для того, чтобы:

- ссылки между таблицами были предсказуемыми;
- можно было легко понять, какой товар какому продавцу принадлежит;
- тестовые заказы ссылались на конкретные `SELLER_PRODUCT_ID`;
- скрипт можно было читать и проверять вручную.

После вставки генераторы синхронизируются:

```sql
SET GENERATOR GEN_USERS_ID TO 6;
```

Поэтому новые записи, созданные через приложение, получат ID начиная с 7 и не конфликтуют с тестовыми.

---

## 12. Проверка после развёртывания

```sql
-- пользователи
SELECT ID, LOGIN, ROLE_ID FROM USERS ORDER BY ID;

-- товары и продавцы
SELECT p.ID, p.NAME, u.LOGIN AS SELLER
FROM PRODUCTS p
JOIN SELLER_PRODUCTS sp ON sp.PRODUCT_ID = p.ID
JOIN USERS u ON u.ID = sp.SELLER_ID
ORDER BY p.ID;

-- заказы
SELECT o.ID, o.STATUS_ID, o.PAYMENT_STATUS_ID, o.DELIVERY_STATUS_ID
FROM ORDERS o
ORDER BY o.ID;

-- продавцы в заказах
SELECT ORDER_ID, SELLER_ID, PAYMENT_CONFIRMED, HANDED_TO_DELIVERY
FROM ORDER_SELLERS
ORDER BY ORDER_ID, SELLER_ID;
```
