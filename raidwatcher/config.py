from __future__ import annotations

import sys
import os
from typing import Optional

import rtoml
from pydantic import BaseModel, ValidationError

from .log import log
from .geofence import Geofence


class Area(BaseModel):
    name: str
    webhooks: list[str]
    geofence: Geofence | None = None

    class Config:
        arbitrary_types_allowed = True


class Config(BaseModel):
    host: str
    port: int
    geofence_path: str
    uicon_url: str
    area: list[Area]


with open("config.toml", mode="r") as _config_file:
    _raw_config = rtoml.load(_config_file)

try:
    _config = Config(**_raw_config)
except ValidationError as e:
    log.error(f"Config validation error!\n{e}")
    sys.exit(1)


_geofences: dict[str, Geofence] = {}
for file in os.listdir(_config.geofence_path):
    if not file.endswith(".txt"):
        continue

    with open(os.path.join(_config.geofence_path, file), mode="r") as fence_file:
        _raw_fence = fence_file.read()

    if _raw_fence.startswith("[") and "]" in _raw_fence:
        _fence_name = _raw_fence.split("[", 1)[1].split("]")[0]
    else:
        _fence_name = file[:-4]

    _geofences[_fence_name] = Geofence.from_raw(_raw_fence)

for _area in _config.area:
    _area.geofence = _geofences.get(_area.name)


config = _config
