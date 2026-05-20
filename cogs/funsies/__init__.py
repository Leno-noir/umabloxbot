from .cog import Funsies


async def setup(bot):
    await bot.add_cog(Funsies(bot))
