import asyncio
import httpx
from app.http_client import send_request

async def main():
    async with httpx.AsyncClient() as client:
        result = await send_request(client, 'https://example.com', timeout=10)
        print(result)

asyncio.run(main())
