import redis


class RedisService:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def get(self, key):
        return self.redis_client.get(key)

    def set(self, key, value, ex=None):
        self.redis_client.set(key, value, ex=ex)

    def delete(self, key):
        self.redis_client.delete(key)
