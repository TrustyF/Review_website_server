import datetime
from dataclasses import dataclass
from db_loader import db

media_genre_association = db.Table('media_genre_assoc', db.Model.metadata,
                                   db.Column('media_id', db.Integer, db.ForeignKey('medias.id', ondelete='CASCADE')),
                                   db.Column('genre_id', db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'))
                                   )

media_theme_association = db.Table('media_theme_assoc', db.Model.metadata,
                                   db.Column('media_id', db.Integer, db.ForeignKey('medias.id', ondelete='CASCADE')),
                                   db.Column('theme_id', db.Integer, db.ForeignKey('themes.id', ondelete='CASCADE'))
                                   )

media_tag_association = db.Table('media_tag_assoc', db.Model.metadata,
                                 db.Column('media_id', db.Integer, db.ForeignKey('medias.id', ondelete='CASCADE')),
                                 db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'))
                                 )
media_tier_list_association = db.Table('media_tier_list_assoc', db.Model.metadata,
                                       db.Column('media_id', db.Integer,
                                                 db.ForeignKey('medias.id', ondelete='CASCADE')),
                                       db.Column('tier_list_id', db.Integer,
                                                 db.ForeignKey('tier_lists.id', ondelete='CASCADE'))
                                       )


@dataclass
class Genre(db.Model):
    __tablename__ = "genres"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False, unique=True)
    origin: str = db.Column(db.String(50), nullable=False)

    media = db.relationship("Media", back_populates='genres', lazy='dynamic', secondary=media_genre_association)


@dataclass
class ContentRating(db.Model):
    __tablename__ = "content_rating"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False, unique=True)
    order: int = db.Column(db.Integer)


@dataclass
class Theme(db.Model):
    __tablename__ = "themes"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False, unique=True)
    origin: str = db.Column(db.String(50), nullable=False)

    media = db.relationship("Media", back_populates='themes', lazy='dynamic', secondary=media_theme_association)


@dataclass
class Tag(db.Model):
    __tablename__ = "tags"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False, unique=True)
    overview: str = db.Column(db.String(1000))
    image_path: str = db.Column(db.String(100))
    tier: str = db.Column(db.String(100))
    origin: str = db.Column(db.String(50), nullable=False)

    media = db.relationship("Media", back_populates='tags', lazy='dynamic', secondary=media_tag_association)

    def __repr__(self):
        return f'{self.name}'


@dataclass
class TierList(db.Model):
    __tablename__ = "tier_lists"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(50), nullable=False, unique=True)

    media = db.relationship("Media", back_populates='tier_lists', lazy='dynamic', secondary=media_tier_list_association)


@dataclass
class Media(db.Model):
    __tablename__ = "medias"

    id: int = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name: str = db.Column(db.String(255), nullable=False)
    external_name: str = db.Column(db.String(255))
    release_date: datetime.date = db.Column(db.Date)
    overview: str = db.Column(db.String(1000))
    poster_path: str = db.Column(db.String(200))

    author: str = db.Column(db.String(200))
    studio: str = db.Column(db.String(200))

    media_type: str = db.Column(db.String(50), nullable=False)
    media_medium: str = db.Column(db.String(50))

    user_rating: int = db.Column(db.Integer, nullable=False)
    public_rating: float = db.Column(db.Float)

    is_dropped: bool = db.Column(db.Boolean)
    is_deleted: bool = db.Column(db.Boolean)

    created_at: datetime.datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at: datetime.datetime = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

    external_id: str = db.Column(db.String(100))
    external_link: str = db.Column(db.String(1000))

    runtime: int = db.Column(db.Integer)
    episodes: int = db.Column(db.Integer)
    seasons: int = db.Column(db.Integer)

    content_rating_id = db.Column(db.Integer, db.ForeignKey('content_rating.id'))
    content_rating = db.relationship("ContentRating")

    genres = db.relationship("Genre", secondary=media_genre_association)
    themes = db.relationship("Theme", secondary=media_theme_association)
    tags = db.relationship("Tag", secondary=media_tag_association)
    tier_lists = db.relationship("TierList", secondary=media_tier_list_association)
