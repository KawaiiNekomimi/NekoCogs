from .pressure import Pressure

def setup(bot):
    bot.add_cog(Pressure(bot))
