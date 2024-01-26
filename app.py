import os

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from constants import MAIN_DIR
from db_loader import db
import logging

# check if using locally
dev_mode = os.path.exists(os.path.join(MAIN_DIR, 'devmode.txt'))

load_dotenv(os.path.join(MAIN_DIR, '.env'))

app = Flask(__name__)

db_username = os.getenv('MYSQL_DATABASE_USERNAME')
db_password = os.getenv('MYSQL_DATABASE_PASSWORD')
db_name = 'TrustyFox$review_site'

database_uri = f'mysql+pymysql://{db_username}:{db_password}@TrustyFox.mysql.pythonanywhere-services.com:3306/{db_name}'
local_database_uri = f'mysql+pymysql://root:{db_password}@127.0.0.1:3306/{db_name}'

if dev_mode:
    print('using local')
    app.config["SQLALCHEMY_DATABASE_URI"] = local_database_uri
else:
    print('using cloud')
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

CORS(app)


@app.route("/test")
def test():
    return "test", 200


with app.app_context():
    db.init_app(app)

    logging.disable(logging.WARNING)

    # from sql_models.media_model import *
    # db.create_all()

    from flask_blueprints import media_blueprint, tag_blueprint, tier_list_blueprint

    app.register_blueprint(media_blueprint.bp, url_prefix='/media')
    app.register_blueprint(tag_blueprint.bp, url_prefix='/tag')
    app.register_blueprint(tier_list_blueprint.bp, url_prefix='/tier_list')
