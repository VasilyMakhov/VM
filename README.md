# VM² — учебный маркетплейс на Flask и Firebird

**VM²** — курсовой проект: маркетплейс с тремя ролями — **покупатель**, **продавец** и **модератор**.

Стек: Python, Flask, Jinja2, Firebird, `firebird-driver`.

---

## Возможности

### Гость

- просмотр каталога, поиск и фильтрация товаров;
- сортировка по цене и названию;
- карточка товара;
- регистрация и вход.

### Покупатель

- личный кабинет и редактирование профиля;
- избранное и корзина;
- оформление заказа с выбором оплаты: СБП или при получении;
- история заказов с фильтрацией и сортировкой;
- отмена заказа до передачи в доставку;
- подтверждение получения.

### Продавец

- свои товары и остатки на складах;
- создание, редактирование и удаление товаров;
- заказы, в которых есть его товары;
- подтверждение оплаты и передача товаров в доставку.

### Модератор

- категории и склады;
- товары всех продавцов;
- редактирование и удаление товаров любого продавца.

---

## Структура проекта

```text
VM/
├── app.py                  # точка входа Flask
├── db.py                   # подключение к Firebird
├── requirements.txt
├── routes/                 # обработчики HTTP-маршрутов
├── templates/              # HTML-шаблоны Jinja2
├── static/                 # CSS и изображения
├── sql/                    # создание схемы и тестовые данные
├── scripts/init_db.sh      # создание и наполнение БД
└── packaging/              # RPM-пакет
```

---

## Быстрый старт

### Требования

- Python 3.11+;
- Firebird 4/5 или RedDatabase;
- `isql-fb` для развёртывания базы.

### Установка

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### База данных

По умолчанию используется `/db/wb_vasa.fdb`.

Создать базу, применить схему и загрузить тестовые данные:

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh /db/wb_vasa.fdb
```

Если база уже существует, скрипт спросит подтверждение перед пересозданием.

Ручной способ:

```bash
isql-fb -q -u SYSDBA -p masterkey -i sql/00_create_database.sql
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/01_schema.sql
isql-fb -q -ch UTF8 -u SYSDBA -p masterkey /db/wb_vasa.fdb -i sql/02_seed.sql
```

### Настройка подключения

Параметры читаются из переменных окружения:

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `VM2_DB_PATH` | `/db/wb_vasa.fdb` | путь к файлу базы |
| `VM2_DB_HOST` | пусто | хост Firebird; `localhost` включает подключение через сервер |
| `VM2_DB_USER` | `SYSDBA` | пользователь Firebird |
| `VM2_DB_PASSWORD` | `masterkey` | пароль Firebird |

Пример:

```bash
VM2_DB_PATH=/var/lib/vm2/vm2.fdb \
VM2_DB_HOST=localhost \
VM2_DB_USER=SYSDBA \
VM2_DB_PASSWORD=masterkey \
python app.py
```

### Запуск

```bash
python app.py
```

Приложение доступно по адресу:

```text
http://127.0.0.1:2911
```

---

## Тестовые аккаунты

После загрузки `sql/02_seed.sql`:

| Логин | Пароль | Роль |
|---|---|---|
| `testuser` | `123456` | Покупатель |
| `buyer2` | `123456` | Покупатель |
| `seller1` | `123456` | Продавец |
| `$eller` | `qqqwww123` | Продавец |
| `prodavan228` | `123456` | Продавец |
| `moderator` | `123456` | Модератор |

---

## RPM-пакет

Сборка:

```bash
rpmbuild -ba packaging/vm2.spec
```

Установка:

```bash
sudo rpm -Uvh --replacepkgs \
    ~/rpmbuild/RPMS/noarch/vm2-1.0.0-1.red80.noarch.rpm
sudo systemctl enable --now vm2
```

При установке пакет создаёт базу `/var/lib/vm2/vm2.fdb`, применяет схему и тестовые данные. Владелец файла базы определяется автоматически по пользователю сервера Firebird (`firebird` или `reddatabase`).
