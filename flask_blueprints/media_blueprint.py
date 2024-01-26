import io
import json
import os.path
from pprint import pprint

import dateutil.parser
import requests

from flask import Blueprint, request, Response, jsonify, send_file
from sqlalchemy import not_, and_, or_
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql.expression import func
from datetime import datetime, timedelta
from math import ceil, floor

from youtubesearchpython import VideosSearch

from constants import MAIN_DIR, TMDB_ACCESS_TOKEN, TMDB_API_KEY, IGDB_CLIENT_ID, IGDB_CLIENT_SECRET
from data_mapper.media_mapper import map_from_tmdb, map_from_mangadex, map_from_igdb, map_from_youtube
from db_loader import db
from sql_models.media_model import Media, Genre, Theme, Tag, media_genre_association, media_tag_association, TierList, \
    ContentRating
from data_mapper.serializer import serialize_media, deserialize_media

bp = Blueprint('media', __name__)


def get_search_category_from_type(f_media_type):
    if f_media_type in ['movie']:
        return 'movie'
    if f_media_type in ['tv', 'anime']:
        return 'tv'


def handle_igdb_access_token(f_source):
    def request_access_token():
        # get token
        token_request = f'https://id.twitch.tv/oauth2/token'
        token_params = {
            'client_id': IGDB_CLIENT_ID,
            'client_secret': IGDB_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        }
        token_response = requests.post(token_request, params=token_params).json()
        token_response['date_added'] = datetime.now().isoformat()
        print('requesting new token')

        return token_response

    def make_new_token():
        print('making new token')
        f_token = request_access_token()

        with open(file_path, 'w') as outfile:
            json.dump(f_token, outfile, indent=1)

        return f_token

    token_path = os.path.join(MAIN_DIR, 'tokens')
    file_path = os.path.join(token_path, (f_source + '.json'))

    # no file
    if not os.path.isfile(file_path):
        return make_new_token()

    # get old token
    with open(file_path, 'r') as infile:
        old_token = json.load(infile)

    # check if outdated
    token_date_added = datetime.fromisoformat(old_token['date_added'])
    token_time_diff = abs((token_date_added - datetime.now()))

    if token_time_diff.total_seconds() > old_token['expires_in']:
        # refresh token
        return make_new_token()
    else:
        # return current token
        print('token time left',
              timedelta(seconds=old_token['expires_in'] - token_time_diff.total_seconds()))
        return old_token


@bp.route("/get", methods=['POST'])
def get():
    # parameters
    data = request.get_json()
    print(data)

    limit = data.get('limit')
    page = data.get('page')
    order = data.get('order')
    media_type = data.get('type')
    session_seed = data.get('session_seed')

    genres = data.get('genres')
    themes = data.get('themes')
    tags = data.get('tags')
    tier_lists = data.get('tier_lists')

    ratings = data.get('ratings')
    public_ratings = data.get('public_ratings')
    release_dates = data.get('release_dates')
    runtimes = data.get('runtimes')
    content_ratings = data.get('content_ratings')

    search = data.get('search')

    user_rating_sort_override = data.get('user_rating_sort_override')
    random_sort_override = data.get('random_sort_override')

    # setup query
    query = (db.session.query(Media).filter(
        or_(Media.is_deleted == 0, Media.is_deleted == None)))  # noqa

    def apply_filters(q):
        if media_type:
            q = q.filter_by(media_type=media_type)
        if search:
            if len(q.filter(Media.name.ilike(f'{search}')).all()) > 0:
                q = q.filter(Media.name.ilike(f'{search}'))

            elif len(q.filter(Media.name.ilike(f'%{search}%')).all()) > 0:
                q = q.filter(Media.name.ilike(f'%{search}%'))

            elif len(q.join(Media.genres).filter(Genre.name.ilike(f'%{search}%')).all()) > 0:
                q = q.join(Media.genres).filter(Genre.name.ilike(f'%{search}%'))

            elif len(q.join(Media.tags).filter(Tag.name.ilike(f'%{search}%')).all()) > 0:
                q = q.join(Media.tags).filter(Tag.name.ilike(f'%{search}%'))

            elif len(q.filter(Media.studio.ilike(f'%{search}%')).all()) > 0:
                q = q.filter(Media.studio.ilike(f'%{search}%'))

            elif len(q.filter(Media.author.ilike(f'%{search}%')).all()) > 0:
                q = q.filter(Media.author.ilike(f'%{search}%'))

            else:
                q = q.filter(Media.overview.ilike(f'%{search}%'))

        if tier_lists:
            q = (q.join(Media.tier_lists).filter(TierList.name.in_(tier_lists))
                 .group_by(Media.id).having(func.count(Media.id) == len(tier_lists)))
        if genres:
            q = (q.join(Media.genres).filter(Genre.id.in_(genres))
                 .group_by(Media.id).having(func.count(Media.id) == len(genres)))
        if themes:
            q = (q.join(Media.themes).filter(Theme.id.in_(themes))
                 .group_by(Media.id).having(func.count(Media.id) == len(themes)))
        if tags:
            q = (q.join(Media.tags).filter(Tag.id.in_(tags))
                 .group_by(Media.id).having(func.count(Media.id) == len(tags)))
        if content_ratings:
            q = q.filter(or_(
                Media.content_rating_id.in_(content_ratings),
                Media.content_rating_id.is_(None),
            ))

        if ratings:
            q = q.filter(Media.user_rating >= ratings[0],
                         Media.user_rating <= ratings[1])
        if public_ratings:
            q = q.filter(
                or_(
                    and_(Media.public_rating >= public_ratings[0],
                         Media.public_rating <= public_ratings[1]),
                    Media.public_rating.is_(None)
                )
            )

        if release_dates:
            q = q.filter(Media.release_date >= datetime(day=1, month=1, year=int(release_dates[0])),
                         Media.release_date <= datetime(day=1, month=1, year=int(release_dates[1])))
        if runtimes:
            q = q.filter(Media.runtime >= int(runtimes[0]), Media.runtime <= int(runtimes[1]))

        return q

    def order_results(q):
        # order result
        selected_ordering = None
        rating_ordering = Media.user_rating.desc() if not user_rating_sort_override else None
        rand_ordering = func.rand(session_seed) if not random_sort_override else None

        if order:
            match order:
                case 'release_date':
                    selected_ordering = Media.release_date.desc()
                case 'name':
                    selected_ordering = Media.name
                case 'public_rating':
                    selected_ordering = Media.public_rating.desc()
                case 'runtime':
                    selected_ordering = Media.runtime.desc()
                case 'date_added':
                    selected_ordering = Media.created_at.desc()

        q = q.order_by(rating_ordering, selected_ordering, rand_ordering, Media.id)

        return q

    query = apply_filters(query)
    query = order_results(query)

    # limiting
    if limit is not None:
        query = query.limit(limit).offset(page * limit)

    # get query and map
    media = query.all()
    serialized_media = [serialize_media(x) for x in media]

    return serialized_media, 200


@bp.route("/find", methods=['GET'])
def find():
    media_name = request.args.get('name')
    media_type = request.args.get('type')
    media_id = request.args.get('id')
    media_page = request.args.get('page', type=int)

    print(f'searching {media_name=} {media_type=} {media_id=}')

    def request_tmdb():
        all_found = []
        id_request = requests.get(
            f'https://api.themoviedb.org/3/search/{media_type}?query={media_name}&page=1', headers={
                "accept": "application/json",
                "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"}).json()

        found_ids = [x['id'] for x in id_request['results'][media_page * 5:(media_page * 5) + 5]]
        print(found_ids)

        for media_id in found_ids:
            full_info = requests.get(
                f'https://api.themoviedb.org/3/{media_type}/{media_id}?api_key={TMDB_API_KEY}'
                f'&language=en-US&append_to_response=releases,content_ratings,credits,external_ids').json()

            all_found.append(full_info)

        return all_found

    def request_mangadex():

        def find_in_relationships(data, key, value):
            for my_dict in data:
                if my_dict.get(key) == value:
                    return my_dict

        media_request = requests.get(f"https://api.mangadex.org/manga?title={media_name}"
                                     f"&limit=5&offset={media_page * 5}&includes[]=cover_art&includes"
                                     f"[]=chapter&includes[]=author"
                                     f"&order[followedCount]=desc&order[relevance]=desc&order[rating]=desc").json()

        all_found = media_request['data']

        for media in all_found:

            rel_found = find_in_relationships(media.get('relationships'), 'type', 'cover_art')
            if rel_found is None:
                continue

            path = (f"https://uploads.mangadex.org/covers/{media['id']}"
                    f"/{rel_found['attributes']['fileName']}"
                    f".512.jpg")
            statistics = requests.get(f'https://api.mangadex.org/statistics/manga/{media["id"]}').json()

            media['poster_path'] = path
            media['vote_average'] = statistics['statistics'][media['id']]['rating']['bayesian']

        # pprint(all_found)
        return all_found

    def request_igdb():  # noqa

        token = handle_igdb_access_token('igdb_token')

        title_request = f'https://api.igdb.com/v4/games'
        title_data = f'search "{media_name}"; limit 5;' \
                     f' fields name,release_dates.y,genres.name,themes.name,total_rating' \
                     f',category,url,summary,cover.url,involved_companies.developer,involved_companies.company.name' \
                     f',age_ratings.rating,age_ratings.category;'
        title_headers = {
            'Client-ID': IGDB_CLIENT_ID,
            'Authorization': f"{token['token_type']} {token['access_token']}",
        }
        title_response = requests.post(title_request, data=title_data, headers=title_headers).json()

        return title_response

    def request_youtube():
        search = VideosSearch(media_name, limit=5).result()
        result = search.get('result')

        for video in result[:2]:
            print(video['id'])
            votes = requests.get(f'https://returnyoutubedislikeapi.com/votes?videoId={video["id"]}').json()
            vote_rating = votes['likes'] / (votes['likes'] + votes['dislikes']) * 10

            video['public_rating'] = vote_rating

        return result

    mapped_media = []

    if media_type in ['movie', 'tv']:
        full_medias = request_tmdb()

        if len(full_medias) > 0:
            mapped_media = map_from_tmdb(full_medias, media_type)

    elif media_type in ['manga']:
        full_medias = request_mangadex()

        if len(full_medias) > 0:
            mapped_media = map_from_mangadex(full_medias, media_type)

    elif media_type in ['game']:
        full_medias = request_igdb()

        if len(full_medias) > 0:
            mapped_media = map_from_igdb(full_medias, media_type)

    elif media_type in ['youtube']:
        full_medias = request_youtube()

        if len(full_medias) > 0:
            mapped_media = map_from_youtube(full_medias, media_type)

    serialized_media = [serialize_media(x) for x in mapped_media]

    if len(serialized_media) > 0:
        # print(serialized_media)
        return serialized_media, 200
    else:
        return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}


@bp.route("/add", methods=['POST'])
def add():
    data = request.get_json()
    print('add', data['name'])

    pprint(data)

    exist_check = db.session.query(Media).filter(Media.external_id == data['external_id']).one_or_none()

    # cancel if already present
    if exist_check is not None:
        return json.dumps({'ok': False}), 404, {'ContentType': 'application/json'}

    media_obj = Media(**deserialize_media(data))

    # associations
    media_obj.genres = [db.session.query(Genre).filter_by(id=x['id']).one() for x in data.get('genres', [])]
    media_obj.themes = [db.session.query(Theme).filter_by(id=x['id']).one() for x in data.get('themes', [])]
    media_obj.tags = [db.session.query(Tag).filter_by(id=x['id']).one() for x in data.get('tags', [])]
    media_obj.tier_lists = [db.session.query(TierList).filter_by(id=x['id']).one() for x in data.get('tier_lists', [])]

    db.session.add(media_obj)
    db.session.commit()
    db.session.close()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/update", methods=['POST'])
def update():
    # parameters
    data = request.get_json()
    print('update', data['name'])
    # pprint(data)

    query = db.session.query(Media).filter_by(id=data['id'])

    if query.one_or_none() is None:
        return json.dumps({'ok': False}), 200, {'ContentType': 'application/json'}

    # update
    query.update(deserialize_media(data))

    # pprint(deserialize_media(data))

    # associations
    media_obj = query.one()

    media_obj.genres = [db.session.query(Genre).filter_by(id=x['id']).one() for x in data.get('genres', [])]
    media_obj.themes = [db.session.query(Theme).filter_by(id=x['id']).one() for x in data.get('themes', [])]
    media_obj.tags = [db.session.query(Tag).filter_by(id=x['id']).one() for x in data.get('tags', [])]
    media_obj.tier_lists = [db.session.query(TierList).filter_by(id=x['id']).one() for x in data.get('tier_lists', [])]
    media_obj.content_rating = db.session.query(ContentRating).filter_by(id=data.get('content_rating')['id']).one()

    db.session.commit()
    db.session.close()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/delete", methods=['GET'])
def delete():
    # parameters
    media_id = request.args.get('id')
    print('delete', media_id)

    db.session.query(Media).filter_by(id=media_id).delete()
    db.session.commit()
    db.session.close()

    return json.dumps({'ok': True}), 200, {'ContentType': 'application/json'}


@bp.route("/get_image")
def get_image():
    media_id = request.args.get('id')
    media_path = request.args.get('path')
    media_type = request.args.get('type')

    # print(f'getting image {media_id=} {media_type=} {media_path=}')

    # return not found image
    if media_path in ['null', 'undefined', 'not_found']:
        return send_file(os.path.join(MAIN_DIR, "assets", "not_found.jpg", ), mimetype='image/jpg')

    file_path = os.path.join(MAIN_DIR, "assets", "poster_images_caches", media_id + f'_{media_type}_' + '.jpg')

    # check if the requested image is part of a db entry and save if true
    if db.session.query(Media).filter(Media.external_id == media_id,
                                      Media.poster_path == media_path).one_or_none():

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        response = requests.get(media_path)

        with open(file_path, 'wb') as outfile:
            outfile.write(response.content)

    else:
        # if preview return without saving
        response = requests.get(media_path)
        return response.content

    return send_file(file_path, mimetype='image/jpg')


@bp.route("/get_extra_posters")
def search_extra_posters():
    media_name = request.args.get('name')
    media_external_id = request.args.get('external_id')
    media_type = request.args.get('type')

    # print(f'extra posters {media_name=} {media_type=} {media_external_id=}')

    search_category = get_search_category_from_type(media_type)

    def request_tmdb_posters():
        extra_request = requests.get(
            f'https://api.themoviedb.org/3/{search_category}/{media_external_id}?api_key={TMDB_API_KEY}'
            f'&language=en-US&append_to_response=credits,images&include_image_language=en,null').json()

        tmdb_link = 'https://image.tmdb.org/t/p/w500'
        concat_posters = [tmdb_link + x['file_path'] for x in extra_request['images']['posters']]

        return concat_posters

    def request_mangadex_posters():
        extra_request = requests.get(f'https://api.mangadex.org/cover?limit=100&manga%5B%5D={media_external_id}').json()
        aggregated_links = []

        if extra_request.get('data') is None:
            return []

        for entry in extra_request['data']:

            if entry['attributes']['volume'] is None:
                continue

            path = (f"https://uploads.mangadex.org/covers/{media_external_id}"
                    f"/{entry['attributes']['fileName']}"
                    f".512.jpg")
            aggregated_links.append([path, entry['attributes']['volume']])

        sorted_links = sorted(aggregated_links, key=lambda x: float(x[1]))
        clean_links = [x[0] for x in sorted_links]

        return clean_links

    def request_igdb_posters():

        token = handle_igdb_access_token('igdb_token')

        cover_request = 'https://api.igdb.com/v4/covers'
        cover_data = f'fields url;'
        cover_headers = {
            'Client-ID': IGDB_CLIENT_ID,
            'Authorization': f"{token['token_type']} {token['access_token']}",
        }
        cover_response = requests.post(cover_request, data=cover_data, headers=cover_headers).json()
        print(cover_response)
        clean_covers = [x['url'] for x in cover_response]

        return clean_covers

    def request_youtube_posters():
        base = [f'https://img.youtube.com/vi/{media_external_id}/maxresdefault.jpg']
        [base.append(f'https://img.youtube.com/vi/{media_external_id}/maxres{x}.jpg') for x in range(1, 5)]
        return base

    posters = []
    if media_type in ['movie', 'tv']:
        posters = request_tmdb_posters()

    if media_type in ['manga']:
        posters = request_mangadex_posters()

    if media_type in ['game']:
        posters = request_igdb_posters()

    if media_type in ['short']:
        posters = request_youtube_posters()

    return posters, 200


@bp.route("/get_filters", methods=['POST'])
def get_filters():
    params = request.get_json()

    media_type = params.get('type')
    media_tier_lists = params.get('tier_lists')

    print(f'getting filters for {media_type=} {media_tier_lists=}')

    genres = db.session.query(Genre)
    themes = db.session.query(Theme)
    tags = db.session.query(Tag)
    content_ratings = db.session.query(ContentRating)

    if media_type:
        genres = genres.join(Media.genres).filter(Media.media_type == media_type)
        themes = themes.join(Media.themes).filter(Media.media_type == media_type)
        tags = tags.join(Media.tags).filter(Media.media_type == media_type)
        content_ratings = content_ratings.join(Media.content_rating).filter(Media.media_type == media_type)

    if media_tier_lists:
        genres = genres.join(Media.tier_lists).filter(TierList.id.in_(media_tier_lists))
        themes = themes.join(Media.tier_lists).filter(TierList.id.in_(media_tier_lists))
        tags = tags.join(Media.tier_lists).filter(TierList.id.in_(media_tier_lists))
        content_ratings = content_ratings.join(Media.tier_lists).filter(TierList.id.in_(media_tier_lists))

    ratings = (db.session.query(func.max(Media.user_rating).label('max'),
                                func.min(Media.user_rating).label('min'))
               .filter(Media.user_rating.is_not(None)))

    public_ratings = db.session.query(func.max(Media.public_rating).label('max'),
                                      func.min(Media.public_rating).label('min')).filter(
        Media.public_rating != 0, Media.public_rating.is_not(None))

    release_dates = (db.session.query(func.max(Media.release_date).label('max'),
                                      func.min(Media.release_date).label('min'))
                     .filter(Media.release_date.is_not(None)))

    runtimes = (db.session.query(func.max(Media.runtime).label('max'),
                                 func.min(Media.runtime).label('min'))
                .filter(Media.runtime.is_not(None)))

    ratings = ratings.one()
    public_ratings = public_ratings.one()
    release_dates = release_dates.one()
    runtimes = runtimes.one()

    result = {
        'genres': genres.group_by(Genre.id).all(),
        'themes': themes.group_by(Theme.id).all(),
        'tags': tags.group_by(Tag.id).all(),
        'content_ratings': content_ratings.group_by(ContentRating.id).all(),
        'user_ratings': [ratings.min or 0, ratings.max or 0],
        'public_ratings': [floor(public_ratings.min or 0), ceil(public_ratings.max or 0)],
        'release_dates': [release_dates.min.year, release_dates.max.year]
        if release_dates.max is not None else [1900, 3000],
        'runtimes': [0, ceil(runtimes.max / 15) * 15] if runtimes.max else [0, 0],
    }

    return result, 200