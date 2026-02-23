from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pymysql
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
CONFIG_PATH = Path("db_config.json")
DEFAULT_CONFIG = {
    "host": "notasegura-cluster.cluster-cyswk2h7td5h.us-east-1.rds.amazonaws.com",
    "port": 53861,
    "database": "notasegura",
    "user": "",
    "password": "",
}


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_connection(config: dict[str, Any]):
    return pymysql.connect(
        host=config["host"],
        port=int(config["port"]),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=8,
        read_timeout=8,
        write_timeout=8,
    )


@app.route("/")
def home():
    return redirect(url_for("connect"))


@app.route("/connect", methods=["GET", "POST"])
def connect():
    message = ""
    ok = False
    config = load_config()

    if request.method == "POST":
        config = {
            "host": request.form.get("host", "").strip(),
            "port": int(request.form.get("port", "53861")),
            "database": request.form.get("database", "").strip(),
            "user": request.form.get("user", "").strip(),
            "password": request.form.get("password", ""),
        }

        action = request.form.get("action")
        try:
            conn = get_connection(config)
            conn.close()
            ok = True
            message = "Conexão realizada com sucesso."
            if action == "save":
                save_config(config)
                message = "Conexão OK e credenciais salvas."
        except Exception as exc:  # noqa: BLE001
            message = f"Falha na conexão: {exc}"

    return render_template("connect.html", config=config, message=message, ok=ok)


@app.route("/cleanup", methods=["GET", "POST"])
def cleanup():
    config = load_config()
    message = ""
    ok = False
    tables: list[str] = []
    selected_table = ""
    cnpj = ""
    user_id = ""
    single_delete = ""
    generated_sql = ""

    try:
        with get_connection(config) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                rows = cursor.fetchall()
                if rows:
                    key = list(rows[0].keys())[0]
                    tables = [row[key] for row in rows]
    except Exception as exc:  # noqa: BLE001
        message = f"Não foi possível carregar tabelas: {exc}"

    if request.method == "POST":
        cnpj = request.form.get("cnpj", "").strip()
        selected_table = request.form.get("table_name", "").strip()

        if not cnpj:
            message = "Informe um CNPJ."
        elif not selected_table:
            message = "Selecione uma tabela."
        else:
            try:
                with get_connection(config) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT id FROM users WHERE users.cnpj = %s", (cnpj,))
                        user_row = cursor.fetchone()
                        if not user_row:
                            message = "Nenhum usuário encontrado para o CNPJ informado."
                        else:
                            user_id = str(user_row["id"])
                            single_delete = f"DELETE FROM {selected_table} WHERE user_id = {user_id};"

                            cursor.execute(
                                """
                                SELECT CONCAT('DELETE FROM ', TABLE_NAME, ' WHERE user_id = ', %s, ';') AS sql_delete
                                FROM information_schema.KEY_COLUMN_USAGE
                                WHERE REFERENCED_TABLE_NAME = 'users'
                                  AND REFERENCED_COLUMN_NAME = 'id'
                                  AND TABLE_SCHEMA = %s
                                """,
                                (user_id, config["database"]),
                            )
                            sql_rows = cursor.fetchall()
                            generated_sql = "\n".join(row["sql_delete"] for row in sql_rows)
                            ok = True
                            message = "Consulta executada com sucesso."
            except Exception as exc:  # noqa: BLE001
                message = f"Erro ao executar consulta: {exc}"

    return render_template(
        "cleanup.html",
        message=message,
        ok=ok,
        tables=tables,
        selected_table=selected_table,
        cnpj=cnpj,
        user_id=user_id,
        single_delete=single_delete,
        generated_sql=generated_sql,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
