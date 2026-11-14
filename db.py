import os

from firebird.driver import connect


def get_connection():
    database = os.environ.get("VM2_DB_PATH", "/db/wb_vasa.fdb")
    host = os.environ.get("VM2_DB_HOST", "").strip()

    # Если хост задан, подключаемся через сервер Firebird.
    # Это нужно для RPM-установки: приложение работает под своим
    # пользователем и не имеет доступа к файлу базы напрямую.
    if host and not database.startswith(f"{host}:"):
        database = f"{host}:{database}"

    return connect(
        database=database,
        user=os.environ.get("VM2_DB_USER", "SYSDBA"),
        password=os.environ.get("VM2_DB_PASSWORD", "masterkey")
    )
