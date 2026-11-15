from contextlib import closing
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
import streamlit as st
from streamlit.connections import SQLConnection

from auth import read_secrets
from editor import ExecutionResult, render_editor, show_output

from .settings import SQL_EDITOR_SETTINGS

EXERCISE_DIR = Path(__file__).resolve().parent / "exercises"
SQL_FILE_EXT = ".sql"
DROP_SCHEMA_PUBLIC = "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"


def get_engine() -> sa.Engine:
    secrets = read_secrets()
    if "sql" in secrets.get("connections", {}):
        connection = st.connection("sql", type=SQLConnection, pool_pre_ping=True)
    elif secrets.get("DATABASE_URL"):
        connection = st.connection(
            "sql", type=SQLConnection, url=secrets["DATABASE_URL"], pool_pre_ping=True
        )
    else:
        raise ValueError(
            "Configure [connections.sql] in .streamlit/secrets.toml to use SQL."
        )
    if connection.engine.dialect.name != "postgresql":
        raise ValueError("SQL exercises require a PostgreSQL connection.")
    return connection.engine


def execute_query(engine: sa.Engine, query: str) -> ExecutionResult:
    """Reset and execute in one transaction; retain the final statement's result.

    Use the driver's unparameterized script API because playground scripts may
    contain multiple statements and literal percent signs or colon expressions.
    Psycopg 3 exposes each result separately; psycopg2 exposes only the final one.
    """
    try:
        dataframe = None
        with (
            engine.begin() as connection,
            closing(connection.connection.cursor()) as cursor,
        ):
            cursor.execute(f"{DROP_SCHEMA_PUBLIC}\n\n{query}")
            while True:
                dataframe = (
                    pd.DataFrame(
                        cursor.fetchall(),
                        columns=[column[0] for column in cursor.description],
                    )
                    if cursor.description is not None
                    else None
                )
                if engine.dialect.driver != "psycopg" or not cursor.nextset():
                    break
        return ExecutionResult(
            dataframe=dataframe,
            success="Query executed successfully!" if dataframe is None else None,
        )
    except Exception as error:  # noqa: BLE001 - support both database drivers
        return ExecutionResult(error=f"Error: {error}")


def list_table_names(engine: sa.Engine) -> list[str]:
    with engine.connect() as connection:
        inspector = sa.inspect(connection)
        return sorted(
            inspector.get_table_names(schema="public")
            + inspector.get_view_names(schema="public")
        )


def load_table(engine: sa.Engine, table_name: str) -> pd.DataFrame:
    # Quote identifiers as identifiers, including reserved words and embedded quotes.
    query = sa.select(sa.literal_column("*")).select_from(
        sa.table(table_name, schema="public")
    )
    with engine.connect() as connection:
        return pd.read_sql_query(query, con=connection)


def show_tables(engine: sa.Engine, table_names: list[str]) -> None:
    if not table_names:
        st.info("No tables in public. Run an exercise to populate them.")
        return
    # Reset a removed selection when a different exercise changes the table list.
    if st.session_state.get("sql_tables") not in table_names:
        st.session_state["sql_tables"] = table_names[0]
    tabs = st.tabs(table_names, key="sql_tables", on_change="rerun")
    for tab, name in zip(tabs, table_names):
        if tab.open:
            with tab:
                try:
                    dataframe = load_table(engine, name)
                    st.dataframe(
                        dataframe,
                        width="stretch",
                        hide_index=True,
                        height=387,
                        key=f"sql_table_{name}",
                        alt=f"Rows in public.{name}",
                    )
                except Exception as error:  # noqa: BLE001 - support both database drivers
                    st.error(f"Error fetching table {name}: {error}")


def run() -> None:
    with st.sidebar:
        st.caption(
            "Each Run drops and recreates the public schema. "
            "Run the selected exercise to populate its tables."
        )
    query_col, tables_col = st.columns(2)
    with query_col:
        workspace, query = render_editor(
            "sql", EXERCISE_DIR, SQL_FILE_EXT, SQL_EDITOR_SETTINGS
        )
        output_panel = st.container()
    with tables_col:
        tables_panel = st.container()

    try:
        engine = get_engine()
    except Exception:  # noqa: BLE001 - show a local configuration/connection error
        with tables_panel:
            st.error(
                "Check [connections.sql] in .streamlit/secrets.toml and use a PostgreSQL URL.",
                title="SQL connection unavailable",
            )
        return

    if query is not None:
        workspace.output = execute_query(engine, query)
    with output_panel:
        show_output(workspace.output)
    with tables_panel:
        try:
            show_tables(engine, list_table_names(engine))
        except Exception:  # noqa: BLE001 - show a local configuration/connection error
            st.error(
                "Check your SQL credentials and that PostgreSQL is running.",
                title="Could not load tables",
            )
