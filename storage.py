import os
from tinydb import TinyDB, Query, where, operations
import re
from flask import Response
import requests

import sort_funcs
import filter_funcs


class Presets:
    def __init__(self):
        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/presets_db.json')

        self.db = TinyDB(self.db_path)

    def get_all_presets(self):
        return sorted(self.db.all(), key=lambda d: d['tier'])

    def add_preset(self, data):
        self.db.insert(data)

    def del_preset(self, data):
        self.db.remove(Query().name == str(data['name']))


class StorageManager:
    def __init__(self):
        self.stores = {}
        self.curr_media = 'movie'

    def add_store(self, name, media):
        self.stores[name] = media

    def set_current_media(self, media_type):
        print('set current', media_type)
        self.curr_media = media_type

    def get_curr_media(self):
        print('returning', self.curr_media, self.stores[self.curr_media])
        return self.stores[self.curr_media]


class Media:

    def __init__(self, media_type):

        self.media_type = media_type

        self.base_path = os.path.dirname(__file__)
        self.db_path = os.path.join(self.base_path, f'database/{self.media_type}_db.json')

        self.db = TinyDB(self.db_path)

        self.filters = {}
        self.max_page_items = 50

        self.settings = {'session_seed': 0, }
        self.rank_range = (1, 10)

        self.rank_avg_range = None
        self.my_rating_range = None

        self.calc_rating_range()

    # setters
    def set_settings(self, query):
        print('set_settings')
        self.settings = query
        self.max_page_items = 50

    def set_filters(self, query):
        print('set_filters')
        self.filters = query

    # operations
    def add_media(self, data):
        self.db.insert(data)

    def update_media(self, data):
        new_data = data['newData']
        old_data = data['oldData']

        title_query = Query().title == str(new_data['title'])
        self.db.update(new_data, title_query)

    def del_media(self, data):
        title_query = Query().title == str(data['title'])
        self.db.remove(title_query)

    # post requests
    def load_more(self):
        self.max_page_items += 50

        if self.max_page_items >= len(self.db.all()):
            return Response(status=201)
        else:
            return Response(status=200)

    # getters
    def get_all_media(self):
        filtered_arr = self.filter(self.db)
        sorted_arr = self.sorting(filtered_arr)
        culled_arr = self.culling(sorted_arr)
        ranked_arr = sort_funcs.place_in_rank_category(culled_arr, self.rank_range)
        return ranked_arr

    def get_media_rating_range(self):
        return {
            'avg_range': self.rank_avg_range,
            'my_range': self.my_rating_range
        }

    # helpers
    def filter(self, f_arr):
        return f_arr.search(
            filter_funcs.rating_filter(self.filters) &
            filter_funcs.length_filter(self.filters) &
            filter_funcs.genre_filter(self.filters) &
            filter_funcs.region_filter(self.filters) &
            filter_funcs.format_filter(self.filters) &
            filter_funcs.searchbar_filter(self.filters)
        )

    def sorting(self, f_arr):
        match self.filters['sort']['filter'][0]:
            case 'popular_vote':
                sort_arr = sort_funcs.sort_by_avg_rating(f_arr)
            case 'date_rated':
                sort_arr = sort_funcs.sort_by_date_rated(f_arr)
            case 'release_date':
                sort_arr = sort_funcs.sort_by_date_released(f_arr)
            case _:
                sort_arr = sort_funcs.sort_randomize(f_arr, self.settings['session_seed'])

        sort_arr = sort_funcs.sort_by_my_rating(sort_arr)
        return sort_arr

    def culling(self, f_arr):
        return f_arr[:self.max_page_items]

    def check_dupe(self, data):
        if data == {}:
            return

        print('checking dupe ', data['title'])
        title_query = Query().title.matches(str(data['title']))
        entries = self.db.search(title_query)

        if len(entries) > 0:
            state = True
        else:
            state = False

        return state

    # calculators
    def calc_rating_range(self):
        avg_ratings = [mov['vote_average'] for mov in self.db]
        my_ratings = [mov['my_rating'] for mov in self.db]

        self.rank_avg_range = (min(avg_ratings), max(avg_ratings))
        self.my_rating_range = (min(my_ratings), max(my_ratings))

        # print(self.media_type, self.rank_avg_range, self.my_rating_range)

    # others
    def transfer_old(self):
        old_db = TinyDB(os.path.join(self.base_path, f'database/sorted_db.json'))
        self.db.insert_multiple(old_db.table('movies').search(where('media_type') == self.media_type))


class Movies(Media):
    def __init__(self):
        super().__init__(media_type='movie')

    # getters
    def get_cover(self, media_id):
        movie = self.db.search(Query().id == int(media_id))[0]
        return requests.get(f"https://image.tmdb.org/t/p/w500{movie['poster_path']}")

    # others
    def cleanup(self):
        for mov in self.db.all():

            if 'images' not in mov:
                return
            if 'posters' not in mov['images']:
                return

            mov['posters'] = []

            for file in mov['images']['posters']:
                mov['posters'].append(file['file_path'])

            del mov['images']
            # print(mov['title'])

            try:
                self.db.table('_default').remove(Query().title == str(mov['title']))
                self.db.table('_default').insert(mov)
            except:
                print('keyError', mov['title'])


class Series(Media):
    def __init__(self):
        super().__init__(media_type='tv')

    def cleanup(self):
        for mov in self.db.all():
            print(mov['title'])

            if 'images' not in mov:
                return
            if 'posters' not in mov['images']:
                return

            mov['posters'] = []

            for file in mov['images']['posters']:
                mov['posters'].append(file['file_path'])

            del mov['images']
            del mov['credits']
            del mov['backdrop_path']
            del mov['created_by']
            del mov['episode_run_time']
            del mov['first_air_date']
            del mov['homepage']
            del mov['languages']
            del mov['last_air_date']
            del mov['last_episode_to_air']
            del mov['next_episode_to_air']
            del mov['networks']
            del mov['origin_country']
            del mov['production_companies']
            del mov['production_countries']
            del mov['spoken_languages']
            del mov['status']
            del mov['tagline']
            del mov['type']

            try:
                self.db.table('_default').remove(Query().title == str(mov['title']))
                self.db.table('_default').insert(mov)
            except:
                print('keyError', mov['title'])


class Manga(Media):
    def __init__(self):
        super().__init__(media_type='manga')

    # helpers
    def filter(self, f_arr):
        return f_arr.search(
            filter_funcs.rating_filter(self.filters) &
            filter_funcs.genre_filter(self.filters) &
            filter_funcs.content_filter(self.filters) &
            filter_funcs.searchbar_filter(self.filters)
        )


tag_presets = Presets()

store = StorageManager()
store.add_store('movie', Movies())
store.add_store('tv', Series())
store.add_store('manga', Manga())