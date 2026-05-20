from .cog import Networking


async def setup(bot):
    await bot.add_cog(Networking(bot))
