import os
from unittest.mock import Mock, patch

import pandas as pd
import pytest
import sqlalchemy as sa
from streamlit.testing.v1 import AppTest
from test_editor import APP

from editor import ExecutionResult
from languages.sql.executor import (
    EXERCISE_DIR,
    execute_query,
    get_engine,
    list_table_names,
    load_table,
)


@pytest.mark.parametrize(
    "secrets",
    [
        {
            "connections": {"sql": {"url": "postgresql://new"}},
            "DATABASE_URL": "postgresql://old",
        },
        {"DATABASE_URL": "postgresql://old"},
    ],
)
def test_connection_configuration_and_legacy_fallback(secrets):
    engine = Mock()
    engine.dialect.name = "postgresql"
    with (
        patch("languages.sql.executor.read_secrets", return_value=secrets),
        patch("streamlit.connection", return_value=Mock(engine=engine)) as connection,
    ):
        assert get_engine() is engine
        kwargs = connection.call_args.kwargs
        if "connections" in secrets:
            assert "url" not in kwargs
        else:
            assert kwargs["url"] == secrets["DATABASE_URL"]


def test_sql_without_configuration_is_local_error():
    with (
        patch("auth.read_secrets", return_value={}),
        patch("languages.sql.executor.read_secrets", return_value={}),
        patch("editor.code_editor", return_value={}),
    ):
        app = AppTest.from_file(str(APP)).run()
        app.switch_page("app_pages/sql.py").run()
        assert not app.exception
        assert app.error[0].title == "SQL connection unavailable"
        app.switch_page("app_pages/python.py").run()
        assert not app.exception


def test_tab_switch_fetches_only_active_table_without_reexecuting_sql():
    event = {"type": "submit", "id": "one", "text": "SELECT 1"}
    with (
        patch("auth.read_secrets", return_value={}),
        patch("editor.code_editor", return_value=event),
        patch("languages.sql.executor.get_engine", return_value=Mock()),
        patch(
            "languages.sql.executor.execute_query",
            return_value=ExecutionResult(success="Done"),
        ) as execute,
        patch("languages.sql.executor.list_table_names", return_value=["a", "b"]),
        patch(
            "languages.sql.executor.load_table", return_value=pd.DataFrame({"x": [1]})
        ) as load,
    ):
        app = AppTest.from_file(str(APP)).run()
        app.switch_page("app_pages/sql.py").run()
        assert not app.exception
        assert execute.call_count == 1
        assert load.call_count == 1
        assert load.call_args.args[1] == "a"
        app.session_state["sql_tables"] = "b"
        app.run()
        assert not app.exception
        assert load.call_count == 2
        assert load.call_args.args[1] == "b"
        assert execute.call_count == 1
        assert app.success[0].value == "Done"


@pytest.fixture(params=["psycopg2", "psycopg"])
def postgres_engine(request):
    url = os.environ.get("KODERPAD_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set KODERPAD_TEST_DATABASE_URL to a disposable PostgreSQL database"
        )
    parsed = sa.make_url(url)
    if not (parsed.database or "").startswith("koderpad_test"):
        pytest.fail(
            "Destructive tests require a database name starting with koderpad_test"
        )
    engine = sa.create_engine(parsed.set(drivername=f"postgresql+{request.param}"))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.postgres
def test_multi_statement_reset_results_and_identifier_quoting(postgres_engine):
    result = execute_query(
        postgres_engine,
        """CREATE TABLE "Order Details" (value text);
        INSERT INTO "Order Details" VALUES ('50% :literal');
        CREATE TABLE "quote""name" (value int);
        CREATE TABLE ":bind" (value int);
        CREATE VIEW exercise_view AS SELECT * FROM "Order Details";
        SELECT * FROM "Order Details";""",
    )
    assert result.error is None
    assert result.dataframe is not None
    assert result.dataframe.iloc[0, 0] == "50% :literal"
    assert list_table_names(postgres_engine) == [
        ":bind",
        "Order Details",
        "exercise_view",
        'quote"name',
    ]
    assert load_table(postgres_engine, "Order Details").iloc[0, 0] == "50% :literal"
    assert load_table(postgres_engine, 'quote"name').empty
    assert load_table(postgres_engine, ":bind").empty
    assert load_table(postgres_engine, "exercise_view").iloc[0, 0] == "50% :literal"
    result = execute_query(postgres_engine, "SELECT 42 AS answer")
    assert result.error is None
    assert result.dataframe is not None
    assert result.dataframe.iloc[0, 0] == 42
    assert list_table_names(postgres_engine) == []


@pytest.mark.postgres
def test_failed_query_rolls_back_schema_reset(postgres_engine):
    assert execute_query(postgres_engine, "CREATE TABLE preserved (id int)").success
    result = execute_query(
        postgres_engine, "CREATE TABLE discarded (id int); SELECT * FROM missing"
    )
    assert result.error
    assert list_table_names(postgres_engine) == ["preserved"]


@pytest.mark.postgres
@pytest.mark.parametrize(
    "exercise", sorted(EXERCISE_DIR.glob("*.sql")), ids=lambda path: path.name
)
def test_bundled_sql_exercises(postgres_engine, exercise):
    result = execute_query(postgres_engine, exercise.read_text(encoding="utf-8"))
    assert result.error is None
