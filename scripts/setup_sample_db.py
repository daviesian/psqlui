"""Utility that launches a sample PostgreSQL Docker container for psqlui."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from psqlui.config import CONFIG_FILE, AppConfig, ConnectionProfileConfig, load_config, save_config

DEFAULT_CONTAINER = "psqlui-sample-db"
DEFAULT_PORT = 5543
DEFAULT_PASSWORD = "psqlui"
DEFAULT_DB = "psqlui_demo"
DEFAULT_USER = "psqlui"
DOCKER_IMAGE = "postgres:16-alpine"


def run(cmd: list[str], *, check: bool = True, **kwargs) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, **kwargs)


def container_exists(name: str) -> bool:
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.ID}}"],
        text=True,
        capture_output=True,
    )
    return bool(result.stdout.strip())


def start_container(name: str, port: int, password: str, database: str, user: str) -> None:
    if container_exists(name):
        print(f"Container '{name}' already exists. Reusing it.")
        run(["docker", "start", name], check=False)
    else:
        run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-e",
                f"POSTGRES_PASSWORD={password}",
                "-e",
                f"POSTGRES_DB={database}",
                "-e",
                f"POSTGRES_USER={user}",
                "-p",
                f"{port}:5432",
                DOCKER_IMAGE,
            ]
        )
    wait_for_start(name)


def wait_for_start(name: str, retries: int = 15, delay: float = 1.0) -> None:
    for attempt in range(retries):
        result = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "pg_isready",
                "-U",
                DEFAULT_USER,
            ],
            text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(delay)
    print("Warning: database did not report ready state; continuing anyway.")


def seed_data(name: str, database: str, user: str) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS accounts (
        id SERIAL PRIMARY KEY,
        email TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        account_id INTEGER REFERENCES accounts(id),
        total NUMERIC(10,2) NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
    );
    INSERT INTO accounts (email) VALUES
        ('anna@example.com'),
        ('ben@example.com'),
        ('cara@example.com')
    ON CONFLICT DO NOTHING;
    INSERT INTO orders (account_id, total, status)
    SELECT id, (random()*100)::numeric(10,2), 'complete'
    FROM accounts
    ON CONFLICT DO NOTHING;
    """.strip()

    run(
        [
            "docker",
            "exec",
            "-i",
            name,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql,
    )


def update_config(port: int, user: str, database: str, password: str) -> None:
    try:
        config = load_config()
    except Exception:
        config = AppConfig()
    profiles = list(config.profiles)
    target = next((p for p in profiles if p.name == "Docker Sample"), None)
    if target is None:
        profiles.append(
            ConnectionProfileConfig(
                name="Docker Sample",
                host="localhost",
                port=port,
                database=database,
                user=user,
                metadata_key="demo",
                dsn=f"postgresql://{user}:{password}@localhost:{port}/{database}",
            )
        )
        config = config.model_copy(update={"profiles": profiles})
        save_config(config)
        print(f"Added 'Docker Sample' profile to {CONFIG_FILE}.")
    else:
        print("Profile 'Docker Sample' already present in config; leaving as-is.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default=DEFAULT_CONTAINER, help="Docker container name")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Host port to expose Postgres on")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Postgres password")
    parser.add_argument("--database", default=DEFAULT_DB, help="Database name to create")
    parser.add_argument("--user", default=DEFAULT_USER, help="Database user")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        start_container(args.container, args.port, args.password, args.database, args.user)
        seed_data(args.container, args.database, args.user)
    except FileNotFoundError:
        print("Docker is not installed or not on PATH.")
        return 1
    update_config(args.port, args.user, args.database, args.password)
    print(
        "Sample database is ready. Connect using the 'Docker Sample' profile or DSN "
        f"postgresql://{args.user}:{args.password}@localhost:{args.port}/{args.database}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
