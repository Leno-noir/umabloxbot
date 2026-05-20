from .cog import Promotion


async def setup(bot):
    await bot.add_cog(Promotion(bot))
