-- Database DDL generation (extracted from amazon-redshift-utils v_generate_database_ddl)
-- Placeholders: {database_filter}
SELECT
  datname as datname,
  'CREATE DATABASE ' + QUOTE_IDENT(datname) + ' WITH CONNECTION LIMIT ' + datconnlimit + ';' AS ddl
FROM pg_catalog.pg_database_info
WHERE datdba >= 100
{database_filter}
ORDER BY datname
