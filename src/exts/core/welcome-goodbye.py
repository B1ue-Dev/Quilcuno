"""
Welcome and goodbye messages for servers.

(C) 2026 - B1ue-Dev
"""

import logging
import random
import datetime

import interactions


REQUIRED_PERMS = (
    interactions.Permissions.VIEW_CHANNEL
    | interactions.Permissions.SEND_MESSAGES
    | interactions.Permissions.EMBED_LINKS
)


class WelcomeGoodbye(interactions.Extension):
    """Extension for welcome and goodbye messages."""

    def __init__(self, client: interactions.Client) -> None:
        self.client: interactions.Client = client
        self._cached: dict[int, list[interactions.GuildText]] = {}

    async def _get_config_channels(
        self, guild: interactions.Guild
    ) -> list[interactions.GuildText]:

        if guild.id not in self._cached:
            channels = await self.client.http.get_guild_channels(guild.id)
            matches: list[dict] = []
            for data in channels:
                if data.get("type") != interactions.ChannelType.GUILD_TEXT:
                    continue

                topic = data.get("topic") or ""
                if topic.partition("\n")[0].strip() == "$quilcuno welcomegoodbye setup":
                    matches.append(data)

            self._cached[guild.id] = [
                interactions.GuildText.from_dict(data, self.client)
                for data in matches
            ]

        return self._cached[guild.id]

    async def _get_channel(
        self, guild: interactions.Guild
    ) -> interactions.GuildText | None:

        channels = await self._get_config_channels(guild)
        if len(channels) != 1 or guild.me is None:
            return None

        channel = channels[0]

        permissions = channel.permissions_for(guild.me)
        if permissions & REQUIRED_PERMS != REQUIRED_PERMS:
            return None

        return channel

    @interactions.listen(interactions.events.MemberAdd)
    async def on_member_add(
        self, event: interactions.events.MemberAdd
    ) -> None:
        """Send welcome message when a member joins."""

        guild = self.client.get_guild(event.guild_id)
        if guild is None:
            return

        channel = await self._get_channel(guild)
        if channel is None:
            return

        welcome_text = (
            "It's good to have you here!",
            "We hope you have a great time here!",
            "Glad to see you!",
            "We hope you enjoy your stay!",
        )
        time_utc = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%d/%m/%Y %H:%M:%S UTC"
        )

        embed = interactions.Embed(
            title=f"Welcome! {random.choice(['🎉', '👋', '🥳'])}",
            description=(
                f"Welcome to **{guild.name}**, {event.member.user.username}! {random.choice(welcome_text)}"
            ),
            color=0x7CB7D3,
            footer=interactions.EmbedFooter(text=f"ID: {event.member.id} • {time_utc}"),
        )
        if event.member.avatar:
            embed.set_thumbnail(url=event.member.avatar.url)
        await channel.send(embeds=embed)

    @interactions.listen(interactions.events.MemberRemove)
    async def on_member_remove(
        self, event: interactions.events.MemberRemove
    ) -> None:
        """Send goodbye message when a member leaves."""
        guild = self.client.get_guild(event.guild_id)
        if guild is None:
            return

        channel = await self._get_channel(guild)
        if channel is None:
            return

        user = (
            event.member.user
            if isinstance(event.member, interactions.Member)
            else event.member
        )
        time_utc = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%d/%m/%Y %H:%M:%S UTC"
        )

        embed = interactions.Embed(
            title="Goodbye! 😢",
            description=f"Goodbye, **{user.username}**! Thanks for being part of {guild.name}.",
            color=0x7CB7D3,
            footer=interactions.EmbedFooter(text=f"ID: {user.id} • {time_utc}"),
        )
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        await channel.send(embeds=embed)

    @interactions.listen(interactions.events.ChannelCreate)
    async def on_channel_create(
        self, event: interactions.events.ChannelCreate
    ) -> None:
        self._cached.clear()

    @interactions.listen(interactions.events.ChannelUpdate)
    async def on_channel_update(
        self, event: interactions.events.ChannelUpdate
    ) -> None:
        self._cached.clear()

    @interactions.listen(interactions.events.ChannelDelete)
    async def on_channel_delete(
        self, event: interactions.events.ChannelDelete
    ) -> None:
        self._cached.clear()

    @interactions.listen(interactions.events.GuildLeft)
    async def on_guild_left(
        self, event: interactions.events.GuildLeft
    ) -> None:
        self._cached.pop(event.guild_id, None)

    @interactions.slash_command(
        name="welcomegoodbye_check",
        description="Check the welcome/goodbye message channel in this server (Need Manage Server permission).",
        contexts=[0],
    )
    async def welcomegoodbye_check(self, ctx: interactions.SlashContext) -> None:
        """Check the welcome/goodbye message channel in this server."""

        await ctx.defer(ephemeral=True)

        if ctx.guild is None:
            await ctx.send(
                "This command only works in a server.", ephemeral=True
            )
            return

        manage_permission = (
            interactions.Permissions.MANAGE_GUILD
            | interactions.Permissions.ADMINISTRATOR
        )
        if not ctx.author.guild_permissions & manage_permission:
            await ctx.send(
                "You need Manage Server permission to check this.",
                ephemeral=True,
            )
            return

        channels = await self._get_config_channels(ctx.guild)
        if not channels:
            await ctx.send(
                "No welcome/goodbye channel is available. "
                "You can set one up by creating a text channel, "
                "setting its topic to include `$quilcuno welcomegoodbye setup` at the top, "
                "and ensuring I have permission to send messages in that channel.",
                ephemeral=True,
            )
            return

        if len(channels) > 1:
            shown_channels = channels[:20]
            channel_mentions = ", ".join(
                f"<#{channel.id}>" for channel in shown_channels
            )
            extra_count = len(channels) - len(shown_channels)
            if extra_count:
                channel_mentions += f", and {extra_count} more"
            await ctx.send(
                f"Multiple welcome/goodbye channels found: {channel_mentions}. "
                "Keep only one channel configured.",
                ephemeral=True,
            )
            return

        channel = await self._get_channel(ctx.guild)
        if channel is None:
            await ctx.send(
                f"I don't have permission to send welcome/goodbye messages in <#{channels[0].id}>.",
                ephemeral=True,
            )
            return

        await ctx.send(
            f"Welcome/goodbye messages: <#{channel.id}>.",
            ephemeral=True,
        )


def setup(client) -> None:
    """Setup the extension."""
    WelcomeGoodbye(client)
    logging.info("Loaded WelcomeGoodbye extension.")
