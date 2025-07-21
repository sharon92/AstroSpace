import os
from flask import Flask


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    
    app.config['root_path'] = os.path.dirname(__file__)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1000 * 1000

    app.config['UPLOAD_PATH'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(app.config['UPLOAD_PATH'],exist_ok=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    with app.app_context():
        exists = db.check_images_table_exists()
        if not exists:
            print("Table does not exist. Initializing database...")
            db.init_db()

    from . import auth
    app.register_blueprint(auth.bp)

    from . import blog
    app.register_blueprint(blog.bp)
    app.add_url_rule('/', endpoint='index')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=9000)
