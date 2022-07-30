from listenbrainz.db import couchdb


def insert_fresh_releases(database: str, docs: list[dict]):
    """ Insert the given fresh releases in the couchdb database. """
    for doc in docs:
        doc["_id"] = str(doc["user_id"])
    couchdb.insert_data(database, docs)


def get_fresh_releases(user_id: int):
    """ Retrieve fresh releases for given user. """
    data = couchdb.fetch_data("fresh_releases", user_id)
    if not data:
        return None
    return {
        "user_id": user_id,
        "releases": data["releases"]
    }
