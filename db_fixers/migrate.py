import csv
import datetime
import pprint
from concurrent.futures import ThreadPoolExecutor

import dateutil.parser
import requests

from constants import TMDB_ACCESS_TOKEN
from data_mapper.serializer import serialize_media
from sql_models.media_model import Media, Genre, Theme, Tag, ContentRating
from db_loader import db
import json
from app import app


def insert_in_db():
    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\movie_db.json',
              'r') as infile:
        movies = json.load(infile)['_default']
        # print(f'{len(movies)} movies')

    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\tv_db.json',
              'r') as infile:
        tv = json.load(infile)['_default']
        # print(f'{len(tv)} tv')

    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\anime_db.json',
              'r') as infile:
        anime = json.load(infile)['_default']
        # print(f'{len(anime)} anime')

    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\manga_db.json',
              'r') as infile:
        manga = json.load(infile)['_default']
        # print(f'{len(manga)} manga')

    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\game_db.json',
              'r') as infile:
        game = json.load(infile)['_default']
        # print(f'{len(game)} game')

    with open(r'D:\A_Main\A_Projects\WebDev\review_site\Review_website_server_BAK\database\presets_db.json',
              'r') as infile:
        tags = json.load(infile)['_default']

    #  create genres
    for media in [movies, tv, anime, manga]:
        for entry in media:
            for genre in media[entry]['genres']:
                if not db.session.query(Genre).filter_by(name=genre).first():
                    new_genre = Genre(name=genre, origin=media[entry]['media_type'])
                    db.session.add(new_genre)

    # create themes
    for entry in game:
        for theme in game[entry]['themes']:
            # print('theme', theme)
            if not db.session.query(Theme).filter_by(name=theme).first():
                new_theme = Theme(name=theme, origin=game[entry]['media_type'])
                db.session.add(new_theme)

        for genre in game[entry]['genres']:
            # print('genre', genre)
            if not db.session.query(Genre).filter_by(name=genre).first():
                new_theme = Genre(name=genre, origin=game[entry]['media_type'])
                db.session.add(new_theme)

    #  create tags
    for media in [movies, tv, anime, manga, game]:
        for entry in media:
            for tag in media[entry]['tags'] or []:
                if not db.session.query(Tag).filter_by(name=tag['name']).first():
                    new_tag = Tag(
                        name=tag['name'],
                        overview=tag['description'],
                        image_path=tag['image'],
                        tier=tag['tier'],
                        origin=media[entry]['media_type']
                    )
                    db.session.add(new_tag)

    db.session.commit()

    # create media
    for media in [movies, tv, anime, manga, game]:
        # print(f'test {len(media)}')
        for i, entry in enumerate(media):
            mov = media[entry]
            # print(mov['title'])

            new_mov = Media(
                name=mov['title'],
                overview=mov['overview'][:1000],
                poster_path=mov['poster_path'],
                media_type=mov['media_type'],
                release_date=mov['release_date'],

                user_rating=int(mov['my_rating']),
                public_rating=mov['vote_average'] if mov['media_type'] != 'game' else mov['vote_average'] / 10,

                external_id=None if 'imdb_id' not in mov else mov['imdb_id'],
                runtime=None if 'runtime' not in mov else mov['runtime'],
                episodes=None if 'episodes' not in mov else mov['episodes'],
                seasons=None if 'seasons' not in mov else mov['seasons'],
                content_rating=None if 'contentRating' not in mov else mov['contentRating'],
            )

            genres = []
            themes = []
            tags = []

            try:
                genres = [db.session.query(Genre).filter_by(name=x).first() for x in mov['genres']]
            except:
                pass
            try:
                themes = [db.session.query(Theme).filter_by(name=x).first() for x in mov['themes']]
            except:
                pass
            try:
                tags = [db.session.query(Tag).filter_by(name=x['name']).first() for x in mov['tags']]
            except:
                pass

            new_mov.genres = genres
            new_mov.themes = themes
            new_mov.tags = tags

            db.session.add(new_mov)
            # print(f'adding {i} - {new_mov.name} - {mov["title"]}')

        db.session.commit()
    db.session.close()


def update_existing_from_tmdb():
    # print('updating')

    all_media = db.session.query(Media).filter(Media.updated_at == None).all()

    # print(len(all_media))
    for media_obj in all_media:

        if media_obj.media_type not in ['tv', 'anime']:
            continue

        main_request = requests.get(
            f'https://api.themoviedb.org/3/find/{media_obj.external_id}?external_source=imdb_id', headers={
                "accept": "application/json",
                "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"}).json()

        found_media = main_request[f'tv_results'][0] if len(
            main_request[f'tv_results']) > 0 else None

        if found_media is None:
            continue

        # print('attempting to update ', media_obj.name, ' to ', found_media.get('title') or found_media['name'])

        db.session.query(Media).filter(Media.id == media_obj.id).update({'external_id': found_media['id']})

    db.session.commit()
    db.session.close()


def update_all_records():
    def update_record(record):
        find_media = requests.get(
            f'http://127.0.0.1:5000/media/find?name={record.name}&type={record.media_type}&page=0').json()

        try:
            selected = find_media[0]
        except KeyError:
            return

        # print(record.name, record.release_date, ' vs ', selected['name'], record.release_date)
        # check if correct
        if selected['name'] != record.name or str(selected['release_date']) != str(record.release_date):
            # print("!!! ", record.name, ' vs ', selected['name'])
            return

        selected['id'] = record.id
        selected['user_rating'] = record.user_rating
        requests.post(f'http://127.0.0.1:5000/media/update', json=selected)

    all_records = (db.session.query(Media).filter(
        Media.media_type == 'game', Media.content_rating_id.is_(None)).all())
    # , Media.updated_at < dateutil.parser.parse('2024-01-25')

    # print(len(all_records))
    with ThreadPoolExecutor() as executor:
        results = [executor.submit(update_record, x) for x in all_records]


def connect_content_ratings():
    all_records = db.session.query(Media).all()

    for record in all_records:
        print(record.content_rating_old)

        if record.content_rating_old is None or record.content_rating_old == "":
            continue

        content = db.session.query(ContentRating).filter_by(name=record.content_rating_old).one()
        record.content_rating = content

    db.session.commit()


def compare_csv_to_db():
    with open(r'C:\Users\sirja\Downloads\ratings.csv') as csv_file:
        reader = csv.reader(csv_file, delimiter=',')

        for i, row in enumerate(reader):
            date = row[2]
            print(row[4][:-1])
            print(date)
            try:
                obj = db.session.query(Media).filter(Media.external_link == row[4][:-1])
                obj.update({'created_at': dateutil.parser.parse(date)})
            except Exception as e:
                print(e)
                print(row[3], ' not found')
                pass

            # if i > 3:
            #     break

        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        compare_csv_to_db()
