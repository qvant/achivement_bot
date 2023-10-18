global queries
global query_texts

GET_NEXT_UPDATE_DATE = "get_next_update_date"
MARK_UPDATE_DONE = "mark_update_done"

queries = {GET_NEXT_UPDATE_DATE: r"db\queries\get_next_update_date.sql",
           MARK_UPDATE_DONE: r"db\queries\mark_update_done.sql"
           }
query_texts = {}


def read_query(name: str) -> str:
    return open(queries[name], "r").read()


def get_query(name: str ) -> str:
    global query_texts
    if name not in query_texts:
        query_texts[name] = read_query(name)
    return query_texts[name]
