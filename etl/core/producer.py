from psycopg import OperationalError
from core.utils import backoff

class PostgresProducer:
    def __init__(self, pg_conn, state, table, batch_size=100):
        self.pg_conn = pg_conn
        self.state = state
        self.table = table
        self.batch_size = batch_size

    @backoff(exceptions=(OperationalError,), service_name="PostgreSQL")
    def extract(self):
        last_updated = self.state.get_state('last_updated_at', '1970-01-01T00:00:00+00:00')
        last_id = self.state.get_state('last_id', '00000000-0000-0000-0000-000000000000')
        
        query = f"""
            SELECT id, updated_at
            FROM {self.table}
            WHERE (updated_at, id) > (%s, %s)
            ORDER BY updated_at, id
            LIMIT %s;
        """
        with self.pg_conn.cursor() as cur:
            cur.execute(query, (last_updated, last_id, self.batch_size))
            rows = cur.fetchall()
        return rows

    @backoff(exceptions=(OperationalError,), service_name="PostgreSQL")
    def extract_docs(self, columns: list[str]):
        """
        Аналог extract(), но возвращает список dict с указанными колонками (для genres/person).
        Обязательно включает 'id' и 'updated_at', чтобы можно было обновить state по последней записи.
        """
        last_updated = self.state.get_state('last_updated_at', '1970-01-01T00:00:00+00:00')
        last_id = self.state.get_state('last_id', '00000000-0000-0000-0000-000000000000')

        cols_sql = ", ".join(columns)
        query = f"""
            SELECT {cols_sql}
            FROM {self.table}
            WHERE (updated_at, id) > (%s, %s)
            ORDER BY updated_at, id
            LIMIT %s;
        """

        with self.pg_conn.cursor() as cur:
            cur.execute(query, (last_updated, last_id, self.batch_size))
            rows = cur.fetchall()
            colnames = [desc.name for desc in cur.description]

        docs: list[dict] = []
        for row in rows:
            doc = {colnames[i]: row[i] for i in range(len(colnames))}
            # нормализуем id (uuid -> str)
            if 'id' in doc:
                doc['id'] = str(doc['id'])
            docs.append(doc)

        return docs
