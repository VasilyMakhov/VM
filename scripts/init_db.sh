#!/usr/bin/env bash
# ============================================================
# VM² — создание и наполнение базы данных Firebird
# ============================================================
# Использование:
#   ./scripts/init_db.sh [путь-к-базе]
#
# Пример:
#   ./scripts/init_db.sh /db/wb_vasa.fdb
#
# Переменные окружения:
#   ISC_USER      — пользователь Firebird (по умолчанию SYSDBA)
#   ISC_PASSWORD  — пароль Firebird (по умолчанию masterkey)
#   ISQL          — путь к isql (по умолчанию isql-fb)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

DB_PATH="${1:-/db/wb_vasa.fdb}"
DB_USER="${ISC_USER:-SYSDBA}"
DB_PASSWORD="${ISC_PASSWORD:-masterkey}"
ISQL_BIN="${ISQL:-isql-fb}"

if ! command -v "${ISQL_BIN}" >/dev/null 2>&1; then
    echo "Ошибка: не найден ${ISQL_BIN}." >&2
    echo "Установите клиент Firebird (пакет firebird-utils / firebird-devel)." >&2
    exit 1
fi

DB_DIR="$(dirname "${DB_PATH}")"

if [ ! -d "${DB_DIR}" ]; then
    echo "Ошибка: каталог ${DB_DIR} не существует." >&2
    exit 1
fi

if [ -e "${DB_PATH}" ]; then
    echo "База данных уже существует: ${DB_PATH}"
    echo "Перед пересозданием остановите приложение (python app.py)."
    read -r -p "Удалить её и создать заново? [y/N] " answer
    case "${answer}" in
        y|Y|yes|YES)
            rm -f "${DB_PATH}"
            ;;
        *)
            echo "Отменено."
            exit 1
            ;;
    esac
fi

TMP_CREATE="$(mktemp)"
trap 'rm -f "${TMP_CREATE}"' EXIT

cat > "${TMP_CREATE}" <<SQL
SET SQL DIALECT 3;
SET NAMES UTF8;

CREATE DATABASE '${DB_PATH}'
    USER '${DB_USER}'
    PASSWORD '${DB_PASSWORD}'
    PAGE_SIZE 8192
    DEFAULT CHARACTER SET UTF8;

COMMIT;
SQL

echo "==> Создание базы: ${DB_PATH}"
"${ISQL_BIN}" -q -u "${DB_USER}" -p "${DB_PASSWORD}" -i "${TMP_CREATE}"

echo "==> Применение схемы: sql/01_schema.sql"
"${ISQL_BIN}" -q -ch UTF8 -u "${DB_USER}" -p "${DB_PASSWORD}" \
    "${DB_PATH}" -i "${PROJECT_DIR}/sql/01_schema.sql"

echo "==> Загрузка тестовых данных: sql/02_seed.sql"
"${ISQL_BIN}" -q -ch UTF8 -u "${DB_USER}" -p "${DB_PASSWORD}" \
    "${DB_PATH}" -i "${PROJECT_DIR}/sql/02_seed.sql"

echo "==> Проверка:"
"${ISQL_BIN}" -q -ch UTF8 -u "${DB_USER}" -p "${DB_PASSWORD}" "${DB_PATH}" <<'SQL'
SELECT 'USERS' AS TABLE_NAME, COUNT(*) AS ROWS_COUNT FROM USERS;
SELECT 'PRODUCTS' AS TABLE_NAME, COUNT(*) AS ROWS_COUNT FROM PRODUCTS;
SELECT 'ORDERS' AS TABLE_NAME, COUNT(*) AS ROWS_COUNT FROM ORDERS;
SQL

echo ""
echo "Готово. База ${DB_PATH} создана и заполнена."
echo "Не забудьте проверить путь и пароль в db.py."
