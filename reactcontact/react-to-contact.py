import asyncio
import re
import datetime
import discord
from discord.ext import commands

from core import checks
from core.models import PermissionLevel


class ReactToContact(commands.Cog):
    """
    Make users start modmail thread by clicking an emoji
    """

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.plugin_db.get_partition(self)
        self.reaction = None
        self.channel = None
        self.message = None
        # asyncio.create_task(self._set_db())

    # async def _set_db(self):
    #     config = await self.db.find_one({"_id": "config"})

    #     if config is None:
    #         return
    #     else:
    #         self.channel = config.get("channel", None)
    #         self.reaction = config.get("reaction", None)
    #         self.message = config.get("message", None)

    @commands.command(aliases=["sr"])
    @commands.guild_only()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def setreaction(self, ctx: commands.Context, link: str):
        """
        Set the message on which the bot will look reactions on.
        Creates an __interactive session__ to use emoji **(Supports Unicode Emoji Too)**
        Before using this command, make sure there is a reaction on the message you want the plugin to look at.

        **Usage:**
        {prefix}setreaction <message_url>
        """

        def check(reaction, user):
            return user == ctx.message.author

        regex = r"discordapp\.com"

        if bool(re.search(regex, link)) is True:
            sl = link.split("/")
            msg = sl[-1]
            channel = sl[-2]

            # TODO: Better English
            await ctx.send(
                "Réagissez au message avec l'émoji"
                " `(Cette reaction doit être mise sur ce message sinon ça ne marchera pas.)`"
            )
            reaction, user = await self.bot.wait_for("reaction_add", check=check)

            await self.db.find_one_and_update(
                {"_id": "config"},
                {
                    "$set": {
                        "channel": channel,
                        "message": msg,
                        "reaction": f"{reaction.emoji.name if isinstance(reaction.emoji, discord.Emoji) else reaction.emoji}",
                    }
                },
                upsert=True,
            )
            await ctx.send("C'est bon !")

        else:
            await ctx.send("Donnez moi un lien valid s'il vous plait.")
            return

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        config = await self.db.find_one({"_id": "config"})

        if config is None:
          #  print("No Config")
            return

        if config["reaction"] is None or (payload.emoji.name != config["reaction"]):
          #  print("No Reaction")
            return

        if config["channel"] is None or (payload.channel_id != int(config["channel"])):
          #  print("No Channel")
            return

        if config["message"] is None or (payload.message_id != int(config["message"])):
          #  print("No Message")
            return

        guild: discord.Guild = discord.utils.find(
            lambda g: g.id == payload.guild_id, self.bot.guilds
        )

        member: discord.Member = guild.get_member(payload.user_id)

        channel = guild.get_channel(int(config["channel"]))

        msg: discord.Message = await channel.fetch_message(int(config["message"]))

        await msg.remove_reaction(payload.emoji, member)
        embed = discord.Embed(
            description="Bonjour, comment puis-je vous aider ?",
            color=self.bot.main_color
        )
        embed.set_footer(text="Attention répondre à ce message ouvrira un ticket.")
        try:
            await member.send(embed=embed)
        except (discord.HTTPException, discord.Forbidden):
            ch = self.bot.get_channel(int(self.bot.config.get("support-logs")))

            await ch.send(
                embed=discord.Embed(
                    title="Je n'ai pas pue contacter l'utilisateur",
                    description=f"J'ai essayé de contacter **{member.name}#{member.discriminator}** mais je réussis (mp fermé ou bot blocké)",
                    color=self.bot.main_color,
                    timestamp=datetime.datetime.utcnow(),
                )
            )


def setup(bot):
    bot.add_cog(ReactToContact(bot))
