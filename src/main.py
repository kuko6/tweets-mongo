import pymongo
from pymongo import MongoClient
import psycopg
from psycopg.rows import dict_row
import time


def fetch_postgres(conn: psycopg.Connection) -> psycopg.ServerCursor:
    """ Create cursor and execute the query """

    cur = conn.cursor(name='tweets')
    cur.execute("""
    SELECT 
        c.id::text as _id, c.author_id::text, c."content", c.possibly_sensitive, c."language", c."source", c.retweet_count, c.reply_count, c.like_count, c.quote_count, c.created_at,
        json_build_object(
            '_id', a.id::text, 'name', a."name", 'username', a.username, 
            'description', a.description, 'followers_count', a.followers_count, 
            'following_count', a.following_count, 'tweet_count', a.tweet_count, 'listed_count', a.listed_count
        ) author,
        COALESCE(ca.jsons, '[]') context_annotations,
        COALESCE(ch.jsons, '[]') conversation_hashtags,
        COALESCE(an.jsons, '[]') annotations,
        COALESCE(l.jsons, '[]') links,
        COALESCE(cr.jsons, '[]') conversation_references
    FROM conversations c
    JOIN authors a ON c.author_id = a.id
    LEFT JOIN (
        SELECT ca.conversation_id, 
            json_agg(json_build_object(
                'entity', json_build_object('name', ce."name", 'description', ce.description), 
                'domain', json_build_object('name', cd."name", 'description', cd.description))
            ) jsons
        FROM context_annotations ca
        JOIN context_entities ce ON ca.context_entity_id = ce.id
        JOIN context_domains cd ON ca.context_domain_id = cd.id 
        GROUP BY ca.conversation_id
    ) ca ON ca.conversation_id = c.id
    LEFT JOIN (
        SELECT ch.conversation_id, json_agg(h.tag) jsons 
        FROM conversation_hashtags ch
        JOIN hashtags h ON ch.hashtag_id = h.id
        GROUP BY ch.conversation_id
    ) ch ON ch.conversation_id = c.id
    LEFT JOIN (
        SELECT an.conversation_id, json_agg(json_build_object('value', an."value", 'probability', an.probability, 'type', an."type")) jsons 
        FROM annotations an
        GROUP BY an.conversation_id
    ) an ON an.conversation_id = c.id
    LEFT JOIN (
        SELECT l.conversation_id, json_agg(json_build_object('url', l.url, 'title', l.title, 'description', l.description)) jsons 
        FROM links l
        GROUP BY l.conversation_id
    ) l ON l.conversation_id = c.id
    LEFT JOIN (
        SELECT 
            cr.conversation_id,
            json_agg(json_build_object('type', cr."type", 'id', p.id::text)) jsons
        FROM conversation_references cr
        JOIN conversations p ON cr.parent_id = p.id
        WHERE timezone('UTC', p.created_at)::date = '2022-02-24'
        GROUP BY cr.conversation_id
    ) cr ON cr.conversation_id = c.id
    WHERE timezone('UTC', c.created_at)::date = '2022-02-24';
    """)

    return cur


def main():
    mongo = MongoClient('localhost', port=27017)
    mongo_db = mongo.get_database('pdt')
    tweets = mongo_db['tweets']
    authors = mongo_db['authors']

    conn = psycopg.connect(host='127.0.0.1', dbname='pdt', user='mac', password='', row_factory=dict_row)
    cur = fetch_postgres(conn)
    
    start_time = time.time()
    processed_rows = 0
    
    authors_data = []
    inserted_authors = set()
    tweets_data = []
    while True:
        rows = cur.fetchmany(10000)
        if len(rows) == 0: break

        for row in rows:
            author = row.pop('author')
            tweet = row

            # To avoid errors for inserting duplicate documents (authors)
            if not author['_id'] in inserted_authors:
                inserted_authors.add(author['_id'])
                authors_data.append(author)

            tweets_data.append(tweet)
            processed_rows += 1

        tweets.insert_many(tweets_data)
        authors.insert_many(authors_data)
        
        print(f'Execution after {processed_rows} rows: {round(time.time() - start_time, 3)}s')

        authors_data.clear()
        tweets_data.clear()

    cur.close()
    conn.close()
    mongo.close()


if __name__ == '__main__':
    main()