from tinydb import TinyDB, Query, where, operations
import re


def rating_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'rating' not in f_filters:
        return match_everything

    rating_filters = f_filters['rating']['filter']

    if not rating_filters:
        return match_everything

    rating_query = Query().my_rating.any(rating_filters)

    return rating_query


def length_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'length' not in f_filters:
        return match_everything

    length_filters = f_filters['length']['filter']

    if length_filters == '':
        return match_everything

    length_query = Query().title.matches('[aZ]*')

    # filter length
    for length in length_filters:
        match length:
            case "1_hour":
                length_query = (Query().runtime <= 60)
            case "1_2_hour":
                length_query = (Query().runtime <= 120)
            case "2_3_hour":
                length_query = (120 < Query().runtime < 180)
            case "3_hour":
                length_query = (Query().runtime >= 180)

    return length_query


def genre_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'genre' not in f_filters:
        return match_everything

    genre_filters = f_filters['genre']['filter']

    if not genre_filters:
        return match_everything

    genre_query = (Query().genres.all(genre_filters))

    return genre_query


# def region_filter(f_filters):
#     match_everything = Query().title.matches('[aZ]*')
#
#     if 'region' not in f_filters:
#         return match_everything
#
#     region_filters = f_filters['region']['filter']
#
#     if region_filters == '':
#         return match_everything
#
#     region_query = Query().title.matches('[aZ]*')
#
#     # filter region
#     for region in region_filters:
#         match region:
#             case "western":
#                 region_query = (~Query().region.any("asian"))
#
#             case "asian":
#                 region_query = (Query().region.any("western"))
#
#     return region_query


def format_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'format' not in f_filters:
        return match_everything

    format_filters = f_filters['format']['filter']

    if format_filters == '':
        return match_everything

    format_query = Query().title.matches('[aZ]*')

    # filter format
    for format_f in format_filters:
        match format_f:
            case "Live-action":
                format_query = (~Query().genres.any("Animation"))

            case "Animated":
                format_query = (Query().genres.any("Animation"))

    return format_query


def content_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'content' not in f_filters:
        return match_everything

    content_filters = f_filters['content']['filter']

    if not content_filters:
        return match_everything

    content_filters += ['none'] * (len(f_filters['content']['available']) - len(content_filters))

    content_query = (
            (Query().contentRating == content_filters[0]) |
            (Query().contentRating == content_filters[1]) |
            (Query().contentRating == content_filters[2]) |
            (Query().contentRating == content_filters[3])
    )

    return content_query


def searchbar_filter(f_filters):
    match_everything = Query().title.matches('[aZ]*')

    if 'search_bar' not in f_filters:
        return match_everything

    searchbar_filters = f_filters['search_bar']

    if searchbar_filters == '':
        return match_everything

    searchbar_query = Query().title.test(lambda val: re.search(searchbar_filters, val, re.IGNORECASE))

    return searchbar_query


def pick_one_each_genre(f_array):
    genres = []
    selected_movies = []

    for movie in f_array:
        try:
            if movie['genres'][0] not in genres:
                selected_movies.append(movie)
                genres.append(movie['genres'][0])
        except IndexError as error:
            print(movie['title'], error)

    # print(genres)
    return selected_movies
