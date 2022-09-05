from __future__ import annotations

import base64
from asyncio import Queue

from aiohttp import web
from aiohttp.web_request import Request

from protos import GetRaidDetailsOutProto, GymGetInfoOutProto, METHOD_GET_RAID_DETAILS, METHOD_GYM_GET_INFO
from .log import log
from .config import config


MESSAGES = {
    METHOD_GET_RAID_DETAILS: GetRaidDetailsOutProto,
    METHOD_GYM_GET_INFO: GymGetInfoOutProto
}


class RawInput:
    def __init__(self, process_queue: Queue):
        self.app = web.Application(logger=log)
        self.queue: Queue = process_queue

        routes = [web.post("/raw", self.accept_protos)]
        self.app.add_routes(routes)

    async def accept_protos(self, request: Request):
        log.debug(f"Received message from {request.remote}")

        if not request.can_read_body:
            log.warning(f"Couldn't read body of incoming request")
            return web.Response(status=400)

        data = await request.json()

        for raw_proto in data.get("contents", []):
            method_id: int = raw_proto.get("type", 0)

            message = MESSAGES.get(method_id)
            if message is None:
                continue

            payload = raw_proto.get("payload")

            if not payload:
                log.warning(f"Empty paylod in {raw_proto}")
                continue

            try:
                decoded = base64.b64decode(payload)
            except Exception as e:
                log.warning(f"Couldn't decode {payload} in {raw_proto}")
                continue

            try:
                proto = message().parse(decoded)
                self.queue.put_nowait(proto)
            except Exception as e:
                log.exception(f"Unknown error while parsing proto {raw_proto}", e)
                continue

        return web.Response()
