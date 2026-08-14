#!/bin/sh
# Wait for a seeded SQLite database on the volume, then start Next.js.
# Catalog rebuilds are done locally; this image never runs pokedb update.
set -e

DB_PATH="${POKEDB_DB:-/data/pokemon_tcg.sqlite}"

if [ ! -f "$DB_PATH" ]; then
    echo "No card database at $DB_PATH."
    echo "Seed the Fly volume from a local build — see docs/DEPLOY_FLY.md"
    echo "Waiting for database file..."
    while [ ! -f "$DB_PATH" ]; do
        sleep 5
    done
    echo "Database found at $DB_PATH."
fi

exec "$@"
