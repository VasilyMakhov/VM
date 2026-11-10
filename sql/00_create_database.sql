-- ============================================================
-- VM² — создание пустой базы данных Firebird
-- ============================================================
-- ВНИМАНИЕ: путь к файлу базы нужно при необходимости изменить.
-- Скрипт рассчитан на запуск через isql-fb:
--
--   isql-fb -q -u SYSDBA -p masterkey -i sql/00_create_database.sql
--
-- После выполнения этого скрипта выполните:
--   sql/01_schema.sql
--   sql/02_seed.sql
-- ============================================================

SET SQL DIALECT 3;
SET NAMES UTF8;

CREATE DATABASE '/db/wb_vasa.fdb'
    USER 'SYSDBA'
    PASSWORD 'masterkey'
    PAGE_SIZE 8192
    DEFAULT CHARACTER SET UTF8;

COMMIT;
