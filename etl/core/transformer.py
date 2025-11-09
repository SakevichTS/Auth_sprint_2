from core.enricher import PostgresEnricher
from typing import List, Dict, Optional

class PostgresTransformer:
    def __init__(self, pg_enricher: PostgresEnricher):
        self.pg_enricher = pg_enricher

    def transform_movies(self, rows):
        if not rows:
            return []
            
        movies_data = {}
        for row in rows:
            fw_id = str(row['fw_id'])
            if fw_id not in movies_data:
                movies_data[fw_id] = {
                    'id': fw_id,
                    'title': row['title'],
                    'description': row['description'],
                    'imdb_rating': row['rating'],
                    '_genre': set(),
                    '_actors': set(),
                    '_writers': set(),
                    '_directors': set(),
                }
        
            if row.get('genre_id') and row.get('genre_name'):
                genre_tuple = (str(row['genre_id']), row['genre_name'])
                movies_data[fw_id]['_genre'].add(genre_tuple)

            if row['person_id']:
                person_tuple = (str(row['person_id']), row['full_name'])
                role = row['role']
                if role == 'actor':
                    movies_data[fw_id]['_actors'].add(person_tuple)
                elif role == 'writer':
                    movies_data[fw_id]['_writers'].add(person_tuple)
                elif role == 'director':
                    movies_data[fw_id]['_directors'].add(person_tuple)

        final_list = []
        for movie in movies_data.values():
            movie['genre'] = [{'id': gid, 'name': gname} for gid, gname in movie['_genre']]
            movie['actors'] = [{'id': pid, 'name': pname} for pid, pname in movie['_actors']]
            movie['writers'] = [{'id': pid, 'name': pname} for pid, pname in movie['_writers']]
            movie['directors'] = [{'id': pid, 'name': pname} for pid, pname in movie['_directors']]
            movie['actors_names'] = [pname for _, pname in movie['_actors']]
            movie['writers_names'] = [pname for _, pname in movie['_writers']]
            movie['directors_names'] = [pname for _, pname in movie['_directors']]

            del movie['_genre']
            del movie['_actors']
            del movie['_writers']
            del movie['_directors']
            
            final_list.append(movie)

        return final_list

    def transform_genres(self, docs):
            """
            docs — список dict из Producer.extract_docs(...) по content.genre.
            Возвращает документы под индекс 'genres'.
            """
            if not docs:
                return []
            out = []
            for d in docs:
                out.append({
                    'id': str(d['id']),
                    'name': d.get('name') or '',
                    'description': d.get('description') or '',
                })
            return out

    def transform_person(self, docs: List[dict], links: Optional[List[dict]] = None) -> List[dict]:
            """
            Возвращает документы под индекс 'persons':
            {
            'id': str,
            'full_name': str,
            'films': [{'id': str, 'roles': [str, ...]}, ...]
            }
            """
            if not docs:
                return []

            # 1) Сгруппировать роли по фильмам для каждой персоны
            #    person_id -> { film_id -> set(roles) }
            roles_by_person: Dict[str, Dict[str, set]] = {}
            if links:
                for row in links:
                    pid = str(row.get('person_id') or '')
                    fid = str(row.get('film_id') or '')
                    role = row.get('role')
                    if not pid or not fid or not role:
                        continue

                    if pid not in roles_by_person:
                        roles_by_person[pid] = {}
                    if fid not in roles_by_person[pid]:
                        roles_by_person[pid][fid] = set()
                    roles_by_person[pid][fid].add(role)

            # 2) Собрать итоговые документы
            result: List[dict] = []
            for p in docs:
                pid = str(p['id'])
                films = []
                for fid, roles in roles_by_person.get(pid, {}).items():
                    films.append({"id": fid, "roles": sorted(roles)})
                result.append({
                    "id": pid,
                    "full_name": p.get("full_name") or "",
                    "films": films,
                })

            return result