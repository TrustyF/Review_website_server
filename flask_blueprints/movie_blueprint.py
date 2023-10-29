import io
import json
import os.path
from pprint import pprint
import requests

from flask import Blueprint, request, Response, jsonify, send_file

from constants import MAIN_DIR
from data_mapper.media_mapper import map_media
from db_loader import db
from sql_models.media_model import Media

bp = Blueprint('movie', __name__)


@bp.route("/get")
def get():
    # parameters
    limit = request.args.get('limit')
    page = request.args.get('page')
    order = request.args.get('order')

    print(f'{limit =}', f'{order =}', f'{page =}')

    # setup query
    query = (
        db.session.query(Media)
        .filter_by(media_type='movie')
    )

    # order result
    match order:
        case 'release_date':
            query = query.order_by(Media.created_at)
        case 'name':
            query = query.order_by(Media.name)

        #     query = query.join(Card).order_by(Card.card_price.desc())
        #     query = query.join(CardTemplate).order_by(UserCard.storage_id, CARD_TYPE_PRIORITY, CardTemplate.name)

    # order direction
    # match direction:
    #     case 'asc':
    #         query = query.asc()
    #     case 'desc':
    #         query = query.desc()
    #     case _:
    #         pass

    # limiting
    if limit is not None:
        # query = query.offset(int(card_limit) * int(card_page))
        query = query.limit(int(limit))

    # get query and map
    media = query.all()
    mapped_media = [map_media(mov) for mov in media]

    return mapped_media

# @bp.route("/get_image")
# def get_image():
#     card_id = request.args.get('id')
#     file_path = os.path.join(MAIN_DIR, "assets", "card_images_cached", f"{card_id}.jpg")
#
#     if not os.path.exists(file_path):
#         response = requests.get(f'https://images.ygoprodeck.com/images/cards_small/{card_id}.jpg')
#
#         with open(file_path, 'wb') as outfile:
#             outfile.write(response.content)
#
#     return send_file(file_path, mimetype='image/jpg')
#
#
# @bp.route("/add_by_name")
# def add_by_name():
#     card_name = request.args.get('name')
#     print(f'searching for {card_name}')
#
#     found_cards = search_card_by_name(card_name)
#
#     new_card = UserCard(card_template_id=found_cards[0].id)
#
#     db.session.add(new_card)
#     db.session.commit()
#     db.session.close()
#
#     return []
#
#
# @bp.route("/delete")
# def delete():
#     card_id = request.args.get('id')
#     print(f'deleting {card_id}')
#
#     # db.session.update(UserCard).where(id=card_id).values(is_deleted=1)
#     db.session.query(UserCard).filter_by(id=card_id).delete()
#     db.session.commit()
#     db.session.close()
#
#     return []
#
#
# @bp.route("/set_card_attrib")
# def set_card_attrib():
#     user_card_id = request.args.get('user_card_id')
#     attr_name = request.args.get('attr_name')
#     attribute = request.args.get('attribute')
#
#     print(f'updating card {attr_name} of card {user_card_id} to {attribute}')
#
#     if attribute == 'null':
#         print('is null')
#         db.session.query(UserCard).filter_by(id=user_card_id).update({str(attr_name): None})
#     else:
#         db.session.query(UserCard).filter_by(id=user_card_id).update({str(attr_name): attribute})
#
#     db.session.commit()
#     db.session.close()
#
#     return []
#
#
# @bp.route("/search_by_name")
# def search_by_name():
#     card_name = request.args.get('name')
#
#     if card_name == '':
#         return []
#
#     print(f'searching for {card_name}')
#
#     found_cards = search_card_by_name(card_name)
#     found_cards_ids = [x.id for x in found_cards]
#
#     query = (
#         db.session
#         .query(UserCard)
#         .join(CardTemplate)
#         .filter(UserCard.card_template_id.in_(found_cards_ids))
#         # .filter(UserCard.storage_id.notin_([11]))
#         .order_by(UserCard.storage_id, CARD_TYPE_PRIORITY, CardTemplate.name)
#     )
#
#     cards_in_user = query.all()
#
#     mapped_cards = [map_card(uc) for uc in cards_in_user]
#
#     return mapped_cards
