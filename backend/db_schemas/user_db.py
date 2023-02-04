from backend.db_schemas.user_schema import UserSchema
import mysql.connector


def init_db():
    _execute(
        ("CREATE TABLE IF NOT EXISTS User ("
         "  first_name VARCHAR NOT NULL,"
         "  last_name VARCHAR NOT NULL,"
         "  type VARCHAR NOT NULL,"
         "  birthday DATE NOT NULL,"
         "  document_id INTEGER NOT NULL,"
         "  country VARCHAR NOT NULL,"
         "  city VARCHAR NOT NULL,"
         "  address VARCHAR,"
         "  email VARCHAR NOT NULL,"
         "  password VARCHAR NOT NULL,"
         "  phone_number INTEGER,"
         "  username VARCHAR NOTNULL,"
         "  id INT PRIMARY KEY AUTO_INCREMENT)"))


def get_all():
    return _execute("SELECT * FROM User", return_entity=False)


def get_user(id):
    return _execute("Select * FROM User WHERE id = {}".format(id), return_entity=False)


def create(user):
    username = user.get("username")
    query = r"SELECT count(*) AS count FROM User WHERE username = '{0}'".format(username)
    count = _execute(query, return_entity=False)

    if count[0]["count"] > 0:
        return

    columns = ", ".join(user.keys())
    values = ", ".join("'{}'".format(value) for value in user.values())
    _execute("INSERT INTO User ({}) VALUES({})".format(columns, values))

    return {}


def update(user, id):
    query = "SELECT count(*) AS count FROM User WHERE id = '{}'".format(id)
    count = _execute(query, return_entity=False)

    if count[0]["count"] == 0:
        return

    values = ["'{}'".format(value) for value in user.values()]
    update_values = ", ".join("{} = {}".format(key, value) for key, value in zip(user.keys(), values))
    _execute("UPDATE User SET {} WHERE id = '{}'".format(update_values, id))
    return {}


def delete(id):
    count = _execute("SELECT count(*) AS count FROM User WHERE id = '{}'".format(id),
                     return_entity=False)
    if count[0]["count"] == 0:
        return
    _execute("DELETE FROM User WHERE id = '{}'".format(id))
    return {}


def _build_list_of_dicts(cursor):
    column_names = [record[0].lower() for record in cursor.description]
    column_and_values = [dict(zip(column_names, record)) for record in cursor.fetchall()]
    return column_and_values


def _convert_to_schema(list_of_dicts):
    return UserSchema().load(list_of_dicts, many=True)


def _execute(query, return_entity=None):
    connection = mysql.connector.connect(
      host="localhost",
      port=3303,
      user="root",
      password="root",
      database="bank_db")
    cursor = connection.cursor()
    cursor.execute(query)

    query_result = None
    if cursor.rowcount == -1:
        query_result = _build_list_of_dicts(cursor)

    if query_result is not None and return_entity:
        query_result = _convert_to_schema(query_result)

    cursor.close()
    connection.close()
    return query_result


