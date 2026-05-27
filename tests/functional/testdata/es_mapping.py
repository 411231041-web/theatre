# Elasticsearch mapping test data
ES_FILM_MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "title": {"type": "text"},
        "description": {"type": "text"},
        "imdb_rating": {"type": "float"},
        "genre": {"type": "keyword"},
        "director": {"type": "text"},
        "actors_names": {"type": "text"},
        "writers_names": {"type": "text"},
        "actors": {
            "type": "nested",
            "properties": {
                "id": {"type": "keyword"},
                "name": {"type": "text"},
            },
        },
        "writers": {
            "type": "nested",
            "properties": {
                "id": {"type": "keyword"},
                "name": {"type": "text"},
            },
        },
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
        "film_work_type": {"type": "keyword"},
    }
}

ES_GENRE_MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "name": {
            "type": "text",
            "fields": {
                "raw": {"type": "keyword"},
            },
        },
        "description": {"type": "text"},
        "created_at": {"type": "date"},
        "updated_at": {"type": "date"},
    }
}

ES_PERSON_MAPPING = {
    "properties": {
        "id": {"type": "keyword"},
        "full_name": {
            "type": "text",
            "fields": {
                "raw": {"type": "keyword"},
            },
        },
        "films": {
            "type": "nested",
            "properties": {
                "id": {"type": "keyword"},
                "roles": {"type": "keyword"},
            },
        },
    }
}
