from firebird.driver import connect


def get_connection():
    return connect(
    database="/db/wb_vasa.fdb",
    user="SYSDBA",
    password="masterkey")