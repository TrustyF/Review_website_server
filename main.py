from flask import Flask, Request, request, Response
from flask_cors import CORS

import storage

app = Flask(__name__)
CORS(app)


# routes
@app.route('/get_media/', methods=["GET"])
def get_media():
    return storage.movies.get_all_media()


@app.route('/set_settings/', methods=["POST"])
def set_settings():
    storage.movies.set_settings(request.json)
    return Response(status=200)


@app.route('/set_filters/', methods=["POST"])
def set_filters():
    storage.movies.set_filters(request.json)
    return Response(status=200)


@app.route('/load_more/', methods=["POST"])
def load_more():
    return storage.movies.load_more()


# @app.route('/get_recent_movie_ratings/', methods=["GET", "POST"])
# def get_recent_movie_ratings():
#     return functions.get_recent_movie_ratings(request.json)
#
#
# @app.route('/edit_movie/', methods=["POST"])
# def edit_movie():
#     functions.edit_movie(request.json)
#     return Response(status=200)
#
#
# @app.route('/add_movie/', methods=["POST"])
# def add_movie():
#     functions.add_movie(request.json)
#     return Response(status=200)
#
#
# @app.route('/del_movie/', methods=["POST"])
# def del_movie():
#     functions.del_movie(request.json)
#     return Response(status=200)
#
#
# @app.route('/get_presets/', methods=["GET"])
# def get_presets():
#     return functions.get_all_presets()
#
#
# @app.route('/add_preset/', methods=["POST"])
# def add_preset():
#     functions.add_preset(request.json)
#     return Response(status=200)
#
#
# @app.route('/del_preset/', methods=["POST"])
# def del_preset():
#     functions.del_preset(request.json)
#     return Response(status=200)
#
#
# @app.route('/check_dupe/', methods=["POST"])
# def check_dupe():
#     state = functions.check_dupe(request.json)
#     return Response(status=200), state


if __name__ == '__main__':
    app.run(debug=True)
