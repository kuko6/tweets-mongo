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