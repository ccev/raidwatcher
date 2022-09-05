from __future__ import annotations

import itertools
import json
from enum import Enum
from typing import Any

import aiohttp

from protos import PokemonProto
from .config import config


class IconSetManager:
    index: dict[str, Any]

    def __init__(self, url: str):
        self.url = url

    async def reload(self):
        async with aiohttp.ClientSession() as session:
            result = await session.get(self.url + "index.json")
            raw_index = await result.text()
            self.index = json.loads(raw_index)


class UIconCategory(Enum):
    POKEMON = "pokemon"


class UIconManager:
    def __init__(self):
        self.iconset = IconSetManager(config.uicon_url)

    def pokemon(self, pokemon: PokemonProto) -> str:
        args = [
            ("", pokemon.pokemon_id),
            ("e", pokemon.pokemon_display.current_temp_evolution),
            ("f", pokemon.pokemon_display.form),
            ("c", pokemon.pokemon_display.costume),
        ]
        return self.get(UIconCategory.POKEMON, args)

    def get(self, category: UIconCategory, args: list[tuple[str, int]]) -> str:
        fin_args = []
        for identifier, id_ in args:
            if id_ != 0:
                fin_args.append(f"{identifier}{id_}")

        combinations = []
        for i in range(len(fin_args) + 1, 0, -1):
            for subset in itertools.combinations(fin_args, i):
                if subset[0] == fin_args[0]:
                    combinations.append(list(subset))
        combinations.append(["0"])

        name = ""
        for combination in combinations:
            possible_name = "_".join(combination) + ".png"
            if possible_name in self.iconset.index.get(category.value, []):
                name = possible_name
                break

        if not name:
            name = "0"
            category = UIconCategory.POKEMON
        return self.iconset.url + category.value + "/" + name


uicons = UIconManager()
