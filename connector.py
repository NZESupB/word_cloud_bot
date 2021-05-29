import redis

pool = redis.ConnectionPool(host='127.0.0.1', port=6380, encoding='utf8', decode_responses=True)


def get_connection():
    return redis.StrictRedis(connection_pool=pool)
