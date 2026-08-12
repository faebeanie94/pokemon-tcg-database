#!/bin/sh
# Build the database on first boot, then hand over to the API server. Later
# refreshes are handled by the service itself on the POKEDB_REFRESH_HOURS timer.
set -e

if [ ! -f "$POKEDB_DB" ]; then
    echo "No database at $POKEDB_DB - building it now (a few minutes on first run)..."
    python -m pokedb update
fi

exec "$@"
