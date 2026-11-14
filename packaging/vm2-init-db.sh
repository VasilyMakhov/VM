#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${VM2_DB_PATH:-/var/lib/vm2/vm2.fdb}"
DB_USER="${VM2_DB_USER:-SYSDBA}"
DB_PASSWORD="${VM2_DB_PASSWORD:-masterkey}"
SQL_DIR="${VM2_SQL_DIR:-/opt/vm2/sql}"
ISQL="${ISQL:-isql-fb}"
LOAD_SEED="${VM2_LOAD_SEED:-1}"
FB_USER="${VM2_FB_USER:-auto}"
FB_GROUP="${VM2_FB_GROUP:-auto}"

log() {
    echo "[vm2-init-db] $*"
}

if [ "$FB_USER" = "auto" ] || [ -z "$FB_USER" ]; then
    FB_USER="$(systemctl show firebird.service -p User --value 2>/dev/null || true)"
fi

if [ -z "$FB_USER" ] || [ "$FB_USER" = "root" ]; then
    FB_USER="$(ps -eo user=,comm= 2>/dev/null \
        | awk '$2 ~ /^(rdbserver|firebird)$/ {print $1; exit}' || true)"
fi

if [ -z "$FB_USER" ] || [ "$FB_USER" = "root" ]; then
    for user in firebird reddatabase; do
        if getent passwd "$user" >/dev/null 2>&1; then
            FB_USER="$user"
            break
        fi
    done
fi

if [ "$FB_GROUP" = "auto" ] || [ -z "$FB_GROUP" ]; then
    FB_GROUP="$(systemctl show firebird.service -p Group --value 2>/dev/null || true)"
fi

if [ -z "$FB_GROUP" ]; then
    FB_GROUP="$(id -gn "$FB_USER" 2>/dev/null || true)"
fi

if [ -z "$FB_GROUP" ]; then
    FB_GROUP="firebird"
fi

have_owner() {
    getent passwd "$FB_USER" >/dev/null 2>&1 \
        && getent group "$FB_GROUP" >/dev/null 2>&1
}

fix_owner() {
    if have_owner; then
        chown "$FB_USER:$FB_GROUP" "$1"
        chmod 0660 "$1"
    fi
}

restore_context() {
    if command -v selinuxenabled >/dev/null 2>&1 && selinuxenabled; then
        restorecon "$1" >/dev/null 2>&1 || true
    fi
}

check_server() {
    if ! systemctl is-active --quiet firebird.service 2>/dev/null \
        && ! systemctl is-active --quiet reddatabase.service 2>/dev/null; then
        return 0
    fi

    if echo "SELECT 1 FROM RDB\$DATABASE;" \
        | "$ISQL" -q "localhost:$DB_PATH" \
            -u "$DB_USER" -p "$DB_PASSWORD" >/dev/null 2>&1; then
        log "Сервер Firebird открыл базу: $DB_PATH"
    else
        echo "[vm2-init-db] ВНИМАНИЕ: сервер Firebird не смог открыть $DB_PATH" >&2
    fi
}

DB_DIR="$(dirname "$DB_PATH")"

if [ ! -d "$DB_DIR" ]; then
    log "Создание каталога: $DB_DIR"
    if have_owner; then
        install -d -m 0750 -o "$FB_USER" -g "$FB_GROUP" "$DB_DIR"
    else
        install -d -m 0750 "$DB_DIR"
    fi
elif [ "$DB_DIR" = "/var/lib/vm2" ] && have_owner; then
    chown "$FB_USER:$FB_GROUP" "$DB_DIR"
    chmod 0750 "$DB_DIR"
fi

if [ -e "$DB_PATH" ] && [ ! -s "$DB_PATH" ]; then
    log "Пустой файл базы удалён: $DB_PATH"
    rm -f "$DB_PATH"
fi

if [ -e "$DB_PATH" ]; then
    fix_owner "$DB_PATH"
    restore_context "$DB_PATH"
    check_server
    log "База уже существует: $DB_PATH"
    exit 0
fi

command -v "$ISQL" >/dev/null 2>&1 || {
    echo "Не найден $ISQL. Установите firebird-utils." >&2
    exit 1
}

[ -f "$SQL_DIR/01_schema.sql" ] || {
    echo "Не найден $SQL_DIR/01_schema.sql" >&2
    exit 1
}

if [ "$LOAD_SEED" = "1" ] && [ ! -f "$SQL_DIR/02_seed.sql" ]; then
    echo "Не найден $SQL_DIR/02_seed.sql" >&2
    exit 1
fi

escape() {
    printf '%s' "$1" | sed "s/'/''/g"
}

SAFE_PATH="$(escape "$DB_PATH")"
SAFE_USER="$(escape "$DB_USER")"
SAFE_PASSWORD="$(escape "$DB_PASSWORD")"

log "Создание базы: $DB_PATH"
"$ISQL" -q -u "$DB_USER" -p "$DB_PASSWORD" <<SQL
SET SQL DIALECT 3;
SET NAMES UTF8;

CREATE DATABASE '${SAFE_PATH}'
    USER '${SAFE_USER}'
    PASSWORD '${SAFE_PASSWORD}'
    PAGE_SIZE 8192
    DEFAULT CHARACTER SET UTF8;

COMMIT;
SQL

log "Применение схемы: $SQL_DIR/01_schema.sql"
"$ISQL" -q -ch UTF8 -u "$DB_USER" -p "$DB_PASSWORD" \
    "$DB_PATH" -i "$SQL_DIR/01_schema.sql"

if [ "$LOAD_SEED" = "1" ]; then
    log "Загрузка тестовых данных: $SQL_DIR/02_seed.sql"
    "$ISQL" -q -ch UTF8 -u "$DB_USER" -p "$DB_PASSWORD" \
        "$DB_PATH" -i "$SQL_DIR/02_seed.sql"
fi

fix_owner "$DB_PATH"
restore_context "$DB_PATH"
check_server
log "Готово: $DB_PATH"
