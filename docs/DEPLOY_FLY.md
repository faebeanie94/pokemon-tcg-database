# Deploying the Next.js console on Fly.io

Dark-mode operator console (`Dockerfile.web`) with the catalog SQLite file on a
volume. The app never rebuilds sources on Fly — build locally, upload the DB.

## Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) logged in
- Local catalog at `build/pokemon_tcg.sqlite` (after `pnpm refresh` or equivalent)
- Match index built: `pnpm build:index` (or let the app rebuild on first request)

## First deploy

```bash
# Create the app (skip if fly.toml app name already exists on your org)
fly apps create tfg-tcg-database

# Create the volume in the same region as primary_region in fly.toml
fly volumes create pokedb_data --region lhr --size 3 --yes

# Deploy the image (machine will wait until the DB file appears)
fly deploy

# Seed the volume (run while a machine is up; entrypoint waits for the file)
fly sftp put build/pokemon_tcg.sqlite /data/pokemon_tcg.sqlite

# SFTP uploads as root — the Next.js process runs as uid 1001 and must be
# able to write (WAL + match-index rebuild on first request).
fly ssh console -C "sh -c 'chown 1001:1001 /data/pokemon_tcg.sqlite && chmod 664 /data/pokemon_tcg.sqlite'"
fly apps restart
```

Then open `https://tfg-tcg-database.fly.dev` and try Identify with
`Charizard 4/102`.

Tip: if the live DB has an open WAL, upload a consistent copy instead:

```bash
sqlite3 build/pokemon_tcg.sqlite "VACUUM INTO '/tmp/pokemon_tcg_fly.sqlite';"
fly sftp put /tmp/pokemon_tcg_fly.sqlite /data/pokemon_tcg.sqlite
fly ssh console -C "sh -c 'chown 1001:1001 /data/pokemon_tcg.sqlite && chmod 664 /data/pokemon_tcg.sqlite'"
fly apps restart
```

## Refreshing the catalog

1. Rebuild locally (`pnpm refresh` / compose pipeline as needed).
2. `pnpm build:index`
3. Upload again: `fly sftp put build/pokemon_tcg.sqlite /data/pokemon_tcg.sqlite`
4. Restart so connections reopen the new file: `fly apps restart tfg-tcg-database`

## Sizing

| Resource | Value | Why |
|---|---|---|
| VM memory | 2GB | ~1GB SQLite + Next + better-sqlite3 |
| Volume | ≥3GB | DB + WAL + headroom for replacements |

## Python API image

`Dockerfile` + `docker-compose.yml` still serve the FastAPI lookup API locally.
That path is separate from this Fly web deploy.
