from __future__ import annotations

import sys

import rtoml
from pydantic import BaseModel, ValidationError

from .log import log


class Config(BaseModel):
    host: str
    port: int
    discord_webhooks: list[str]
    uicon_url: str


with open("config.toml", mode="r") as _config_file:
    _raw_config = rtoml.load(_config_file)

try:
    _config = Config(**_raw_config)
except ValidationError as e:
    log.error(f"Config validation error!\n{e}")
    sys.exit(1)

config = _config
