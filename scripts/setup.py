#!/usr/bin/env python3
"""Interactive setup wizard for the Redshift skill."""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add parent to path for lib imports
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.client import CONFIG_DIR, CONFIG_FILE, save_config


def run_cmd(cmd):
    """Run a command and return (success, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def check_prerequisites():
    """Check that Python 3 and AWS CLI are available."""
    print("\nChecking prerequisites...")

    # Python version
    v = sys.version.split()[0]
    print(f"  \u2713 Python {v}")

    # AWS CLI
    ok, out, err = run_cmd(["aws", "--version"])
    if ok:
        print(f"  \u2713 {out.split()[0]}")
    else:
        print("  \u2717 AWS CLI not found")
        print("    Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html")
        sys.exit(1)

    print()


def list_aws_profiles():
    """List available AWS profiles from ~/.aws/."""
    profiles = []
    for config_file in [Path.home() / ".aws" / "credentials", Path.home() / ".aws" / "config"]:
        if config_file.exists():
            with open(config_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]"):
                        name = line[1:-1].replace("profile ", "")
                        if name not in profiles:
                            profiles.append(name)
    return profiles


def prompt(message, default=None):
    """Prompt user for input with optional default."""
    if default:
        user_input = input(f"  {message} [{default}]: ").strip()
        return user_input or default
    else:
        user_input = input(f"  {message}: ").strip()
        return user_input


def main():
    print("=" * 40)
    print("  Redshift Skill Setup")
    print("=" * 40)

    check_prerequisites()

    config = {}

    # Step 1: AWS Profile
    print("Step 1: AWS Profile")
    profiles = list_aws_profiles()
    if profiles:
        print(f"  Available profiles: {', '.join(profiles)}")
    profile = prompt("Enter profile name", profiles[0] if profiles else "default")
    config["profile"] = profile

    # Verify identity
    ok, out, err = run_cmd(["aws", "sts", "get-caller-identity", "--profile", profile, "--output", "json"])
    if ok:
        identity = json.loads(out)
        arn = identity.get("Arn", "unknown")
        account = identity.get("Account", "unknown")
        # Extract a friendly name from the ARN
        name = arn.split("/")[-1] if "/" in arn else arn
        print(f"  \u2713 Authenticated as {name} (account {account})")
    else:
        print(f"  \u2717 Authentication failed: {err}")
        print("  Check your AWS profile configuration and try again.")
        sys.exit(1)
    print()

    # Step 2: Redshift Cluster
    print("Step 2: Redshift Cluster")
    print("  Discovering clusters...")
    ok, out, err = run_cmd([
        "aws", "redshift", "describe-clusters",
        "--profile", profile, "--output", "json"
    ])

    if ok:
        clusters_data = json.loads(out)
        clusters = clusters_data.get("Clusters", [])
        if not clusters:
            print("  No clusters found. You may need a different profile or region.")
            cluster_id = prompt("Enter cluster identifier manually")
            region = prompt("AWS region", "us-east-1")
            config["region"] = region
        else:
            print("  Found:")
            for i, c in enumerate(clusters, 1):
                cid = c["ClusterIdentifier"]
                status = c["ClusterStatus"]
                endpoint = c.get("Endpoint", {})
                region = endpoint.get("Address", "").split(".")[2] if endpoint.get("Address") else "unknown"
                print(f"    {i}. {cid} ({status}, {region})")

            if len(clusters) == 1:
                choice = prompt("Select cluster (number or name)", "1")
            else:
                choice = prompt("Select cluster (number or name)")

            # Accept both number and cluster name
            cluster = None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(clusters):
                    cluster = clusters[idx]
            if not cluster:
                # Try matching by name
                for c in clusters:
                    if c["ClusterIdentifier"] == choice:
                        cluster = c
                        break
            if not cluster:
                print(f"  \u2717 Cluster '{choice}' not found")
                cluster_id = prompt("Enter cluster identifier manually")
            else:
                cluster_id = cluster["ClusterIdentifier"]
                endpoint_addr = cluster.get("Endpoint", {}).get("Address", "")
                if endpoint_addr:
                    region = endpoint_addr.split(".")[2]
                    config["region"] = region
            print(f"  \u2713 Selected: {cluster_id}")
    else:
        print(f"  Warning: Could not list clusters: {err}")
        cluster_id = prompt("Enter cluster identifier manually")

    config["cluster"] = cluster_id
    print()

    # Step 3: Database
    print("Step 3: Database")
    database = prompt("Database name", "dev")
    db_user = prompt("Database user", "admin")
    config["database"] = database
    config["db_user"] = db_user
    print()

    # Step 4: Test connection
    print("Step 4: Testing connection...")
    test_sql = "SELECT current_user AS connected_as, current_database() AS database_name"
    aws_args = [
        "aws", "redshift-data", "execute-statement",
        "--cluster-identifier", config["cluster"],
        "--database", config["database"],
        "--db-user", config["db_user"],
        "--sql", test_sql,
        "--profile", config["profile"],
        "--output", "json",
    ]
    if config.get("region"):
        aws_args += ["--region", config["region"]]

    ok, out, err = run_cmd(aws_args)
    if not ok:
        print(f"  \u2717 Failed to submit test query: {err}")
        print("  Check your cluster, database, and user settings.")
        sys.exit(1)

    stmt_id = json.loads(out).get("Id")

    # Poll for completion
    import time
    for _ in range(30):
        time.sleep(1)
        describe_args = [
            "aws", "redshift-data", "describe-statement",
            "--id", stmt_id,
            "--profile", config["profile"],
            "--output", "json",
        ]
        if config.get("region"):
            describe_args += ["--region", config["region"]]

        ok, out, err = run_cmd(describe_args)
        if ok:
            status_data = json.loads(out)
            status = status_data.get("Status")
            if status == "FINISHED":
                print(f"  \u2713 Connected as {config['db_user']} to {config['database']}")
                break
            elif status in ("FAILED", "ABORTED"):
                print(f"  \u2717 Test query {status}: {status_data.get('Error', 'unknown')}")
                sys.exit(1)
    else:
        print("  \u2717 Test query timed out")
        sys.exit(1)

    print()

    # Save config
    # Save the Python executable path so other tools know which to use
    config["python"] = sys.executable
    save_config(config)
    print(f"Saved to {CONFIG_FILE}")

    # Show a friendly command using python3/python rather than the full system path
    py_cmd = "python3" if "python3" in sys.executable or sys.platform == "darwin" else "python"
    scripts_dir = Path(__file__).resolve().parent
    print()
    print("Setup complete! Try:")
    print(f"  {py_cmd} {scripts_dir / 'query.py'} \"SELECT 1\"")
    print()


if __name__ == "__main__":
    main()
