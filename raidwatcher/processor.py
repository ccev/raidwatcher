from __future__ import annotations

import asyncio
from dataclasses import dataclass

import aiohttp
import discord
from betterproto import serialized_on_wire
from cachetools import TTLCache
from datetime import datetime

from protos import GymGetInfoOutProto, GetRaidDetailsOutProto, PokemonProto, HoloPokemonId
from .config import config
from .log import log
from .uicons import UIconManager
from .uicons import uicons


class RaidEmbed(discord.Embed):
    def __init__(self, raid_details: GetRaidDetailsOutProto, gym: Gym | None = None):
        super().__init__()

        self.title = f"Ends {self._get_formatted_time(raid_details.raid_info.raid_end_ms)}"
        self.set_thumbnail(url=uicons.pokemon(raid_details.raid_info.raid_pokemon))
        self.update(raid_details, gym)

    @staticmethod
    def _get_formatted_time(ms: int | None = None):
        dt = discord.utils.utcnow() if ms is None else datetime.fromtimestamp(ms / 1000)
        return discord.utils.format_dt(dt, style="T")

    def update(self, raid_details: GetRaidDetailsOutProto | None = None, gym: Gym | None = None):
        if gym:
            self.set_author(name=gym.name, icon_url=gym.url)

        if raid_details:
            prefix = "" if self.description is None else self.description
            extra_s = "" if raid_details.num_players_in_lobby == 1 else "s"
            self.description = prefix + (
                f"\n{self._get_formatted_time()} | " f"{raid_details.num_players_in_lobby} player{extra_s}"
            )


@dataclass
class CacheEntry:
    embed: RaidEmbed
    messages: list[discord.WebhookMessage]
    player_count: int

    async def edit(self):
        for message in self.messages:
            await message.edit(embed=self.embed)


@dataclass
class Gym:
    name: str
    url: str


class RaidProcessor:
    _session: aiohttp.ClientSession

    def __init__(self, queue: asyncio.Queue):
        self._input_queue: "asyncio.Queue[GymGetInfoOutProto | GetRaidDetailsOutProto]" = queue
        self._webhook_cache: TTLCache[int, CacheEntry] = TTLCache(maxsize=10000, ttl=120)
        self._gym_cache: TTLCache[int, Gym] = TTLCache(maxsize=1000000, ttl=60 * 60)
        self._uicons = UIconManager()

        asyncio.create_task(self._process_queue())

    async def _send_webhook(self, embed: RaidEmbed, pokemon: PokemonProto) -> list[discord.WebhookMessage]:
        icon = uicons.pokemon(pokemon)
        try:
            enum_name = HoloPokemonId(pokemon.pokemon_id).name
        except (KeyError, IndexError):
            enum_name = "Unknown"
        name = "Active " + enum_name.replace("_", " ").title() + " Raid"

        messages = []
        for url in config.discord_webhooks:
            webhook = discord.Webhook.from_url(url=url, session=self._session)
            message = await webhook.send(embed=embed, wait=True, username=name, avatar_url=icon)
            messages.append(message)
        return messages

    async def _process_queue(self):
        self._session = aiohttp.ClientSession()

        while True:
            proto = await self._input_queue.get()

            if isinstance(proto, GetRaidDetailsOutProto):
                entry = self._webhook_cache.get(proto.raid_info.raid_seed)

                if entry is not None and entry.player_count != proto.num_players_in_lobby:
                    log.info(
                        f"Editing Raid {proto.raid_info.raid_seed} with updated players "
                        f"{entry.player_count} -> {proto.num_players_in_lobby}"
                    )
                    gym = self._gym_cache.get(proto.raid_info.raid_seed)
                    entry.embed.update(proto, gym)
                    await entry.edit()

                elif entry is None and proto.num_players_in_lobby > 0:
                    log.info(f"Sending new Raid {proto.raid_info.raid_seed}")
                    gym = self._gym_cache.get(proto.raid_info.raid_seed)
                    embed = RaidEmbed(proto, gym)
                    messages = await self._send_webhook(embed, proto.raid_info.raid_pokemon)
                    entry = CacheEntry(embed=embed, messages=messages, player_count=proto.num_players_in_lobby)
                    self._webhook_cache[proto.raid_info.raid_seed] = entry

            elif isinstance(proto, GymGetInfoOutProto):
                fort = proto.gym_status_and_defenders.pokemon_fort_proto
                if not serialized_on_wire(fort.raid_info):
                    continue
                if not serialized_on_wire(fort.raid_info.raid_pokemon):
                    continue

                raid_seed = fort.raid_info.raid_seed
                if raid_seed in self._gym_cache:
                    continue

                gym = Gym(name=proto.name, url=proto.url)
                self._gym_cache[raid_seed] = gym

                entry = self._webhook_cache.get(raid_seed)
                if entry is not None:
                    log.info(f"Updating existing Raid messages for new Gym <{gym.name}>")
                    entry.embed.update(gym=gym)
                    await entry.edit()
