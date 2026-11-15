# Koderpad
An online Python and SQL database playground for testing codes

## Requirements
1. [uv](https://github.com/astral-sh/uv)
2. make
3. Docker
4. Python3.11

## Local Development
1. Setup environment variables.
    ```sh
    cp -i .streamlit/secrets.toml.example .streamlit/secrets.toml
    ```
- Note that instead of `.env`, we are using `secrets.toml` located in the `.streamlit` directory to store secrets for this project.
- Authentication is optional for local development. To enable sign-in, configure OIDC as described below. Legacy `APP_PWD` configuration must be removed.
- The default URL under `[connections.sql]` in `.streamlit/secrets.toml` should match the `make db` in `Makefile`. Update if required to point to other database url.

2. Run database and app
    ```sh
    $ make db  # run the local Postgres container in the background
    $ make dev # run the Streamlit app
    ```

   `make db` reuses the Postgres major version recorded in `db/PG_VERSION` for existing data, or defaults to Postgres 16 for a new database. Changing the image version does not upgrade existing database files; a major-version upgrade requires a separate migration.

## Sign-in
Native Streamlit OIDC sign-in is enabled when `[auth]` is present in `.streamlit/secrets.toml`. Register an OIDC application with your provider and set `redirect_uri`, `cookie_secret`, `client_id`, `client_secret`, and `server_metadata_url`. A commented example is included in `.streamlit/secrets.toml.example`.

For local development, register `http://localhost:8501/oauth2callback` as the redirect URI. Use your deployed URL when hosting the app. Every user authenticated by that provider can access all three pages; there is no email allowlist. Sign out from the sidebar.

Without `[auth]`, local development runs without sign-in. An incomplete `[auth]` section or any legacy `APP_PWD` setting blocks access and displays migration guidance. Do not commit real secrets.

## SQL configuration and execution
Configure PostgreSQL under `[connections.sql]`. Legacy top-level `DATABASE_URL` is supported only when `[connections.sql]` is absent. Python and Dockerfile pages work without database configuration.

Each fresh SQL Run drops and recreates the shared `public` schema within the same transaction as the submitted script. Errors roll back that transaction. Use a dedicated playground database: users share its tables. Browsing table tabs, changing pages, or resetting the editor does not execute submitted code. Only the active table is fetched; table reads are not cached.

Reset editor restores the selected exercise and clears its saved output. Changing exercises also clears output. Exercise selections persist across page changes; unsaved editor drafts are not persisted after leaving a page.

## Checks
```sh
make check         # lint, format check, type check, tests; does not rewrite files
make format        # apply Ruff fixes and formatting
make update-hooks  # update pre-commit hook versions explicitly
make test          # regression tests
```

PostgreSQL integration tests are skipped unless `KODERPAD_TEST_DATABASE_URL` points to a disposable database whose name starts with `koderpad_test`. They reset its public schema and run against both psycopg drivers:

```sh
KODERPAD_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:55432/koderpad_test uv run pytest -m postgres
```

## Warning
Only grant access to trusted users. Python runs inside the app process, and its import checks are not a sandbox. SQL users can execute arbitrary scripts against the configured database. OIDC identifies users; it does not isolate their execution or database tables.
