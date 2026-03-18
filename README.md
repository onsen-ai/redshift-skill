# Redshift Skill for Claude Code

A Claude Code skill for exploring AWS Redshift clusters — run queries, browse schemas, generate DDL, check disk usage, and more.

**Cross-platform** (Mac + Windows) | **Read-only** (hard guardrails) | **Zero pip install** (Python stdlib only)

## Prerequisites

- **Python 3.8+** — no pip packages needed, stdlib only
- **AWS CLI v2** — configured with a profile that has [Redshift Data API](https://docs.aws.amazon.com/redshift/latest/mgmt/data-api.html) access

## Installation

### Using the Skills CLI (recommended)

```bash
# Install to your project
npx skills add onsen-ai/redshift-skill

# Or install globally (available across all projects)
npx skills add onsen-ai/redshift-skill -g
```

See [vercel-labs/skills](https://github.com/vercel-labs/skills) for more install options.

### Manual installation

```bash
# Clone and symlink into your project
git clone https://github.com/onsen-ai/redshift-skill.git
ln -s /path/to/redshift-skill /your/project/.claude/skills/redshift
```

### First-time setup

Run the interactive setup wizard to configure your connection:

```bash
python3 scripts/setup.py    # macOS / Linux
python scripts/setup.py     # Windows
```

The wizard will:
1. Check prerequisites (Python, AWS CLI)
2. List your available AWS profiles
3. Discover Redshift clusters
4. Test connectivity with a real query
5. Save config to `~/.redshift-skill/config.json`

You can re-run setup anytime to change your connection settings.

## Usage

Once set up, all scripts work without connection args:

```bash
# Run any SQL query
python scripts/query.py "SELECT count(1) FROM my_schema.my_table"

# Explore the database
python scripts/schemas.py
python scripts/tables.py --schema=public
python scripts/columns.py --schema=public --table=users

# Generate DDL
python scripts/ddl.py --schema=public --name=users
python scripts/ddl.py --type=view --schema=public --name=v_active_users
python scripts/ddl.py --type=schema --name=public
python scripts/ddl.py --type=database
python scripts/ddl.py --type=udf --schema=public
python scripts/ddl.py --type=external --schema=spectrum
python scripts/ddl.py --type=group

# Search for objects
python scripts/search.py --pattern=order
python scripts/search.py --pattern=price --type=column

# Sample data
python scripts/sample.py --schema=public --table=users --limit=5

# Check disk usage
python scripts/space.py --top=20
python scripts/space.py --schema=public

# Extended table metadata
python scripts/table_info.py --schema=public --table=users
```

### Output formats

All scripts support `--format=txt|csv|json` (default: txt):

```bash
python scripts/tables.py --schema=public --format=csv
python scripts/tables.py --schema=public --format=json
```

Save directly to a file with `--save`:

```bash
python scripts/query.py --format=csv --save=results.csv "SELECT * FROM public.users"
```

Results exceeding 50 rows auto-save to `~/redshift-exports/` and show the first 20 rows inline.

### Override connection settings

Any script accepts connection overrides:

```bash
python scripts/query.py --profile=prod --cluster=my-cluster --database=analytics "SELECT 1"
```

## Rich metadata out of the box

The skill bundles SQL from [amazon-redshift-utils](https://github.com/awslabs/amazon-redshift-utils) and runs it directly against system catalogs. No admin views or special setup needed on your cluster — full DDL generation (with distkeys, sortkeys, encoding, constraints), extended table metadata, and disk usage analysis work everywhere.

### DDL types

| Type | Description | Example |
|------|-------------|---------|
| `table` | Full table DDL with distkey, sortkey, constraints, encoding | `ddl.py --schema=s --name=t` |
| `view` | View definition | `ddl.py --type=view --schema=s --name=v` |
| `schema` | Schema creation with authorization | `ddl.py --type=schema` |
| `database` | Database creation with connection limits | `ddl.py --type=database` |
| `udf` | User-defined function (SQL + Python) | `ddl.py --type=udf --schema=s` |
| `external` | Spectrum/external table DDL | `ddl.py --type=external` |
| `group` | User group DDL | `ddl.py --type=group` |

## Read-only safety

All queries are validated before execution — both by Claude and by the script itself. Only these statement types are allowed:

`SELECT` · `WITH` · `SHOW` · `DESCRIBE` · `EXPLAIN` · `SET`

DDL, DML, and DCL statements are blocked at the script level. Multi-statement queries are also rejected.

## Configuration

Config is stored at `~/.redshift-skill/config.json`:

```json
{
  "profile": "my-profile",
  "cluster": "my-cluster",
  "database": "my-database",
  "db_user": "admin",
  "region": "us-east-1"
}
```

Edit this file directly or re-run `python scripts/setup.py`.

## License

SQL queries in `scripts/sql/` are derived from [amazon-redshift-utils](https://github.com/awslabs/amazon-redshift-utils) (Apache 2.0).
