import os
from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    # first priority 
    app.config.from_object('AstroSpace.config.Config') 

    # second priority
    # load the environment variables from the path set in environment variable
    app.config.from_envvar('ASTROSPACE_SETTINGS', silent=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)
    
    app.config['root_path'] = os.path.dirname(__file__)
    app.config['MAX_CONTENT_LENGTH'] = 2 *  (1024 ** 3) #about 2GB

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        return jsonify(error=f"Uploaded File is too large. Max size is {app.config['MAX_CONTENT_LENGTH']/(1024**3)} GB."), 413

    #app.config['UPLOAD_PATH'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(app.config['UPLOAD_PATH'],exist_ok=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    for key in ['SECRET_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT']:
        if key not in app.config:
            raise ValueError(f"{key} must be set in the configuration", app.config)

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

    from .profile import private, public
    app.register_blueprint(private.bp)
    app.register_blueprint(public.bp)

    app.add_url_rule('/', endpoint='index')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=9000)
