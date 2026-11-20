import os
from dotenv import load_dotenv
import redis.asyncio as aioredis

load_dotenv()

redis = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)