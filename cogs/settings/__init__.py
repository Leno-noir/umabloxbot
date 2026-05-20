from .cog import Settings

async def setup(bot):
    await bot.add_cog(Settings(bot))