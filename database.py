import sqlite3


"""В этом файле осуществляется взаимодейстие с базой данной. Отправка данных, получение данных, удаление данных"""


class database:
    def __init__(self, conn, cur):
        self.conn = conn
        self.cur = cur

    def add_new_items(self, items: set, colums: str, table: str):
        length = len(items)
        self.cur.execute(f'INSERT INTO {table}({colums}) VALUES({", ".join(["?" for _ in range(length)])});', items)
        self.conn.commit()

    def get_column(self, condition: str, table: str):
        self.cur.execute(f'SELECT {condition} FROM {table};')
        result = self.cur.fetchall()
        return [res[0] for res in result]

    def get_all(self, table: str) -> list:
        self.cur.execute(f'SELECT * FROM {table};')
        result = self.cur.fetchall()
        return result

    def delete_id(self, id: int, table: str):
        self.cur.execute(f'DELETE FROM {table} WHERE id = ?', (str(id), ))
        self.conn.commit()

    def delete_nickname(self, nickname: str, table: str):
        self.cur.execute(f'DELETE FROM {table} WHERE nickname = ?', (nickname, ))
        self.conn.commit()

    def delete_all(self, table: str):
        self.cur.execute(f'DELETE FROM {table};')
        self.conn.commit()

    def get_certain(self, condition: str, table: str):
        self.cur.execute(f'SELECT * FROM {table} WHERE {condition};')
        result = self.cur.fetchall()
        if not result:
            return []
        return [res for res in result]

    def get_one_val(self, column, id_answer, table: str) -> str:
        self.cur.execute(f'SELECT {column} FROM {table} WHERE id= {id_answer};')
        result = self.cur.fetchone()
        return result[0]

    def check_value(self, condition, table):
        try:
            result = self.get_certain(condition, table)
        except Exception as err:
            print(err)
            return False

        return bool(result)

    def update_value(self, update_column:str, new_value:str, search_column:str, search_value:str, table:str):
        self.cur.execute(f"UPDATE {table} SET {update_column} = ? WHERE {search_column} = ?", (new_value, search_value))



def connection_table(name_db: str):
    conn = sqlite3.connect(name_db, check_same_thread=False)
    cur = conn.cursor()
    return database(conn, cur)