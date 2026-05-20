from .cog import Feedback


async def setup(bot):
    await bot.add_cog(Feedback(bot))
