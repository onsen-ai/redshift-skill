-- Group DDL generation (extracted from amazon-redshift-utils v_generate_group_ddl)
-- Placeholders: {group_filter}
SELECT groname AS groupname, 'CREATE GROUP ' + QUOTE_IDENT(groname) + ';' AS ddl
FROM pg_catalog.pg_group
{group_filter}
ORDER BY groname
