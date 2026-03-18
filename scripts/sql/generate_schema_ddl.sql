-- Schema DDL generation (extracted from amazon-redshift-utils v_generate_schema_ddl)
-- Placeholders: {schema_filter}
SELECT
    nspname AS schemaname,
    'CREATE SCHEMA ' + QUOTE_IDENT(nspname) +
        CASE
        WHEN nspowner > 100
        THEN ' AUTHORIZATION ' + QUOTE_IDENT(pg_user.usename)
        ELSE ''
        END
        + ';' AS ddl
FROM pg_catalog.pg_namespace as pg_namespace
LEFT OUTER JOIN pg_catalog.pg_user pg_user
ON pg_namespace.nspowner=pg_user.usesysid
WHERE nspowner >= 100
{schema_filter}
ORDER BY nspname
