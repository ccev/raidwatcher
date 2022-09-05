import asyncio
from asyncio import Queue

from aiohttp import web

from raidwatcher.raw_input import RawInput
from raidwatcher.processor import RaidProcessor
from raidwatcher.uicons import uicons
from raidwatcher.config import config


async def main():
    processing_queue = Queue()
    await uicons.iconset.reload()

    accepter = RawInput(process_queue=processing_queue)
    asyncio.create_task(
        web._run_app(
            app=accepter.app,
            host=config.host,
            port=config.port,
            access_log=None
        )
    )
    RaidProcessor(processing_queue)

    await asyncio.Event().wait()


asyncio.run(main())
