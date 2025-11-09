import logging
import time
import json
from psycopg import OperationalError
from redis import Redis

from core.utils import pg_conn_context, redis_conn_context, connect_es
from core.state import State, RedisStorage
from core.producer import PostgresProducer
from core.enricher import PostgresEnricher
from core.merger import PostgresMerger
from core.transformer import PostgresTransformer
from core.loader import ElasticsearchLoader
from core.config import settings

def process_source(config: dict, producer: PostgresProducer, enricher: PostgresEnricher, merger: PostgresMerger, transformer: PostgresTransformer, redis_connection: Redis):
    logging.info("-> Запуск producer для 'genre'...")

    genre_docs = producer.extract_docs(['id', 'name', 'description', 'created_at', 'updated_at'])
    if not genre_docs:
        logging.info("Для 'genre' нет новых данных.")
        return

    logging.info(f"Producer извлёк {len(genre_docs)} жанров из 'genre'.")

    # трансформируем и отправляем в очередь жанров
    docs_for_es = transformer.transform_genres(genre_docs)
    if docs_for_es:
        q_genres = 'processed_genres_queue'
        logging.info(f"Отправка {len(docs_for_es)} жанров в очередь '{q_genres}'...")
        for doc in docs_for_es:
            redis_connection.rpush(q_genres, json.dumps(doc, default=str))

    # связанные фильмы -> через enricher -> merger -> transform_movies -> в общую очередь фильмов
    source_ids = [d['id'] for d in genre_docs]
    film_work_ids = list(dict.fromkeys(enricher.enrich(source_ids, 'genre')))
    if film_work_ids:
        logging.info(f"Подготовка к обработке данных для {len(film_work_ids)} связанных фильмов.")
        raw_data = merger.fetch_merged_data(film_work_ids)
        transformed_movies = transformer.transform_movies(raw_data)
        if transformed_movies:
            q_movies = 'processed_movies_queue'
            logging.info(f"Отправка {len(transformed_movies)} фильмов в очередь '{q_movies}'...")
            for doc in transformed_movies:
                redis_connection.rpush(q_movies, json.dumps(doc, default=str))
        else:
            logging.warning("Transformer для фильмов вернул пусто — нечего отправлять.")
    else:
        logging.info("Нет связанных фильмов для переиндексации по изменённым жанрам.")

    # обновляем state по последнему документу
    last = genre_docs[-1]
    producer.state.set_state('last_updated_at', str(last['updated_at']))
    producer.state.set_state('last_id', last['id'])
    logging.info(f"Состояние для 'genre' обновлено: modified={last['updated_at']}, id={last['id']}\n")


def load_data_to_es(es_loader: ElasticsearchLoader, redis_connection: Redis, queue_name: str):
    """
    Извлекает данные из очереди Redis и загружает их в Elasticsearch пачками.
    """

    logging.info(f"[genres] Проверка очереди '{queue_name}' на наличие данных для загрузки...")

    while redis_connection.llen(queue_name) > 0:
        records_to_load_str = redis_connection.lrange(queue_name, 0, settings.batch_size - 1)
        records_to_load = [json.loads(rec) for rec in records_to_load_str]

        logging.info(f"[genres] Извлечено {len(records_to_load)} документов из Redis для загрузки в индекс '{es_loader.index_name}'.")
        es_loader.load_to_es(records_to_load)

        redis_connection.ltrim(queue_name, len(records_to_load), -1)
        logging.info(f"[genres] Успешно обработанная пачка удалена из очереди '{queue_name}'.")

    logging.info("[genres] Очередь пуста. Загрузка в Elasticsearch завершена на данный момент.")


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    try:
        with redis_conn_context(**settings.redis.to_dict()) as redis_connection, \
             connect_es(hosts=[f"http://{settings.es.host}:{settings.es.port}"]) as es_conn:

            logging.info("[genres] Соединения с Redis и Elasticsearch установлены.")

            # Этот раннер отвечает за индекс жанров
            genres_loader = ElasticsearchLoader(es_conn, 'genres')

            while True:
                try:
                    with pg_conn_context(**settings.pg.to_dict()) as p_conn:
                        genre_cfg = next(cfg for cfg in settings.producer_configs if cfg.source_type == 'genre')
                        genre_state = State(RedisStorage(redis_connection, genre_cfg.state_key))
                        genre_producer = PostgresProducer(p_conn, genre_state, genre_cfg.table, settings.batch_size)
                        enricher = PostgresEnricher(p_conn, settings.batch_size)
                        merger = PostgresMerger(p_conn, settings.batch_size)
                        transformer = PostgresTransformer(enricher)

                        # Обработка жанров (и пуш связанных фильмов в общую очередь)
                        process_source(genre_cfg, genre_producer, enricher, merger, transformer, redis_connection)

                except OperationalError as e:
                    logging.warning(f"[genres] Не удалось подключиться к PostgreSQL в этом цикле. Повтор через 5 секунд. Ошибка: {e}")

                load_data_to_es(genres_loader, redis_connection, 'processed_genres_queue')

                logging.info(f"[genres] --- Тик завершён. Пауза {settings.sleep_time} секунд. ---\n")
                time.sleep(settings.sleep_time)

    except Exception as e:
        logging.error(f"[genres] Критическая ошибка в главном цикле ETL: {e}", exc_info=True)

if __name__ == '__main__':
    main()
