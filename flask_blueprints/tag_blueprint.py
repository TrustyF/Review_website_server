import json
import os
from dataclasses import asdict

import sqlalchemy.exc
from flask import Blueprint, request, Response, jsonify, send_file
from sqlalchemy import func, or_

from app import cache
from constants import MAIN_DIR
from db_loader import db
from flask_blueprints.login_blueprint import requires_auth
from sql_models.media_model import Tag, Media

bp = Blueprint('tag', __name__)


@bp.route("/get", methods=['GET'])
@cache.cached()
def get():
    tag_counts = (
        db.session.query(Tag, func.count(Media.id).label('count'))
        .filter(Tag.is_deleted.is_(None))
        .outerjoin(Tag.media)
        .group_by(Tag)
        .all()
    )

    serialized_tags = [{**asdict(tag), 'count': count} for tag, count in tag_counts]

    return serialized_tags, 200


@bp.route("/get_tier_images", methods=['GET'])
@cache.cached(query_string=True)
def get_tier_images():
    tier = request.args.get('tier')
    get_all = request.args.get('get_all')

    all_tags_path = os.path.join(MAIN_DIR, 'static', 'tags', 'icons', tier)
    all_images = [x for x in os.listdir(all_tags_path)]

    # return all images
    if get_all:
        formated_images = [[tier, x] for x in all_images]
        return formated_images, 200

    # return images not yet used for tags
    tags = (
        db.session.query(Tag)
        .filter(Tag.tier == tier)
        .filter(Tag.is_deleted.is_(None))
        .all()
    )

    tag_paths = [f'{tag.image_path}.webp' for tag in tags]

    exclusive_paths = [name for name in all_images if name not in tag_paths]
    images = [[tier, x] for x in exclusive_paths]

    return images, 200


@bp.route("/add", methods=['POST'])
@requires_auth
def add():
    data = request.get_json()
    # print(data)
    # del data['id']

    # print(f'adding tag {data=}')

    new_tag = Tag(**{
        'name': data['name'],
        'overview': data['overview'],
        'image_path': data['image_path'],
        'tier': data['tier'],
        'origin': data['origin'],
        'is_unique': data['is_unique'],
    })
    db.session.add(new_tag)

    db.session.commit()

    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}

    db.session.close()
    cache.clear()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/update", methods=['POST'])
@requires_auth
def update():
    data = request.get_json()
    tag_id = data['id']

    # print(f'updating tag {data=}')

    db.session.query(Tag).filter(Tag.id == tag_id).update({
        'name': data['name'],
        'overview': data['overview'],
        'image_path': data['image_path'],
        'tier': data['tier'],
        'origin': data['origin'],
        'is_unique': data['is_unique'],
    })

    db.session.commit()
    db.session.close()
    cache.clear()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/delete")
@requires_auth
def delete():
    tag_id = request.args.get('id')

    # print(f'deleting tag {tag_id=}')

    db.session.query(Tag).filter(Tag.id == tag_id).update({'is_deleted': True})

    db.session.commit()
    db.session.close()
    cache.clear()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}
