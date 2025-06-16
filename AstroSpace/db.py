import click
from flask import current_app, g
import psycopg2
from psycopg2.extras import RealDictCursor

def get_conn():
    if 'db' not in g:
        # Database configuration
        db_config = {
            'dbname': current_app.config['DB_NAME'],
            'user': current_app.config['DB_USER'],
            'password': current_app.config['DB_PASSWORD'],
            'host': current_app.config['DB_HOST'],
            'port': current_app.config['DB_PORT'],
            'cursor_factory': RealDictCursor
        }
        g.db = psycopg2.connect(**db_config)

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_conn()

    with current_app.open_resource('schema.sql') as f:
        sql_statements = f.read().decode('utf8')
        
        with db.cursor() as cur:
            for statement in sql_statements.split(';'):
                stmt = statement.strip()
                if stmt:
                    # print("statement",stmt)  # Debugging: print the SQL statements
                    cur.execute(stmt)
            db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')
