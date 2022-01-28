import discord
from discord.ext import commands
import rule34
import asyncio
from cogs.utils import constants as const
import logging
import random


logger = logging.getLogger(__name__)


rule34 = rule34.Rule34(asyncio.get_event_loop())


class NSFW(commands.Cog):
    """
    Commands for NSFW content
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # TODO: r34 nuke command

    @commands.command(aliases=["rule34"])
    @commands.is_nsfw()
    async def r34(self, ctx: commands.Context, *, tags: str):
        """
        Search for images on rule34.xxx
        """
        # Make sure my bot doesn't get banned from Discord
        for illegal_tag in const.ILLEGAL_TAGS:
            if illegal_tag in tags.lower():
                logger.warning("NSFW command called with inappropriate tags")
                await ctx.message.add_reaction(const.NSFW)
                return await ctx.send("Illegal tags in search query.")

        # Make sure no result's with illegal tags are retrieved
        full_tags = tags + " -" + " -".join(const.ILLEGAL_TAGS)

        # Search for images
        posts = await rule34.getImages(tags=full_tags, randomPID=True)

        if posts is None:
            return await ctx.send(f"No results found for {discord.utils.escape_markdown(tags)}")

        random_post = random.choice(posts)
        if not random_post.initialised:
            logger.warning("Rule34 returned an uninitialized post")
            await ctx.send("Rule34 returned a weird image, attempting to send")
            return await ctx.send(random_post.file_url)

        result_str = await self.get_results_str(full_tags)
        await ctx.send(f"Found {result_str} for {discord.utils.escape_markdown(tags)}, here's a random one:")
        await ctx.send(random_post.file_url)

    @r34.error
    async def r34_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.add_reaction(const.NO)
            await ctx.send(
                ("Missing tags to search for.\n"
                 f"Usage: `{ctx.prefix}r34/rule34 <tags>` or for multiple tags "
                 f"`{ctx.prefix}r34/rule34 <tag1> <tag2> ...`\n"
                 "If your tag has spaces in it use underscores (`_`) instead.")
            )

    async def get_results_str(self, tags: str) -> str:
        posts = await rule34.totalImages(tags=tags + " -" + " -".join(const.ILLEGAL_TAGS))
        # Perform advanced algorithm to fix pluralization
        if posts == 1:
            results_str = "1 result"
        else:
            results_str = f"{posts} results"

        return results_str


def setup(bot: commands.Bot):
    bot.add_cog(NSFW(bot))
