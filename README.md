# pokemon-tcg-database

A small full-stack web app for browsing, searching, and cataloging Pokémon
Trading Card Game cards. Built with **Next.js (App Router) + TypeScript**, a
**SQLite** database (via `better-sqlite3`), and **Tailwind CSS**.

## Features

- Browse a seeded catalog of Pokémon TCG cards
- Search by card name or set
- Filter by energy type
- Add new cards through a form (with server-side validation)
- JSON API under `/api/cards`

## Tech stack

| Layer      | Choice                                   |
| ---------- | ---------------------------------------- |
| Framework  | Next.js 15 (App Router)                  |
| Language   | TypeScript                               |
| Database   | SQLite (`better-sqlite3`)                |
| Styling    | Tailwind CSS                             |
| Tests      | Vitest                                   |
| Lint       | ESLint (`eslint-config-next`)            |

## Getting started

Requires Node.js 22+ and pnpm.

```bash
pnpm install        # install dependencies
pnpm dev            # start the dev server at http://localhost:3000
```

The SQLite database is created automatically at `data/pokemon.db` on first
run and seeded with a starter set of cards.

## Scripts

| Command       | Description                              |
| ------------- | ---------------------------------------- |
| `pnpm dev`    | Start the development server (port 3000) |
| `pnpm build`  | Production build                         |
| `pnpm start`  | Run the production build                 |
| `pnpm lint`   | Run ESLint                               |
| `pnpm test`   | Run the Vitest test suite                |

## API

| Method | Route             | Description                             |
| ------ | ----------------- | --------------------------------------- |
| GET    | `/api/cards`      | List cards (`?search=` and `?type=`)    |
| POST   | `/api/cards`      | Create a card                           |
| GET    | `/api/cards/:id`  | Fetch a single card                     |
