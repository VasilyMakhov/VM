from firebird.driver import connect

connection = connect(
    database="/db/wb_vasa.fdb",
    user="SYSDBA",
    password="masterkey"
)

print("great!")

connection.close()