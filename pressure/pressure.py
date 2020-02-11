import asyncio
import discord
import random
import calendar
import tempfile
import functools
import time

from typing import Any, Union
from discord.utils import get
from datetime import datetime
from discord.ext import commands
from discord.ext.commands import check, MissingRole, CommandError, TextChannelConverter
from .db import db, userdata, guilddata

from redbot.core import checks, commands

from redbot.core.bot import Red


Cog: Any = getattr(commands, "Cog", object)

listener = getattr(commands.Cog, "listener", None)
if listener is None:

    def listener(name=None):
        return lambda x: x

class Pressure(Cog):
    """
    Anti-Spam system by Fear#3939
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        system_active = await self.db_get_guildinfo(message, "system_active")
        log_channel = await self.db_get_guildinfo(ctx.message, "log_channel")
        if system_active == 0:
            return
        try:
            silence_role = discord.utils.get(ctx.guild.roles, name="Silenced")
            await channel.set_permissions(silence_role, send_messages=False)
        except discord.errors.Forbidden:
            if log_channel > 0:
                log_channel = ctx.guild.get_channel(log_channel)
                await log_channel.send(f"```Failed to deny the Silenced role permissions to speak in #{channel.name}: Missing Permissions```")
        except:
            if log_channel > 0:
                log_channel = ctx.guild.get_channel(log_channel)
                await log_channel.send(f"```Failed to deny the Silenced role permissions to speak in #{channel.name}```")


    async def on_message(self, message):
        system_active = await self.db_get_guildinfo(message, "system_active")
        role_name = await self.db_get_guildinfo(message, "mod_role")
        mod_role = discord.utils.get(message.guild.roles, name=f"{role_name}")
        if message.author.bot: #Ignores all bots
            return
        if mod_role in message.author.roles:
            return
        if system_active == 0:
            return
        last_msg_id = await self.db_get_userinfo(message, "last_msg_id")
        pressure = await self.db_get_userinfo(message, "pressure")
        if last_msg_id == 0:
            await self.first_msg_pressure(message)
            await self.db_update_user(message, "last_msg_id", message.id)
            return
        else:
            time_passed = await self.get_msg_time(message, last_msg_id)
            pressure = await self.remove_pressure(message, time_passed, pressure)
            before_pressure = pressure
            reason = await self.add_pressure(message)
            await self.check_pressure(message, reason, before_pressure)
    
    # TO DO:
    # Add try/except statements to check for various errors and send info to the log channel
    # Add a raid detection system

    # I love Ahri... LoL is life, and Ahri is the best champion 

    @commands.command()
    @commands.guild_only()
    async def silence(self, ctx: commands.Context, target: discord.Member, reason: str = '[Unknown]'):
        """Silence a user"""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        alert_channel = await self.db_get_guildinfo(ctx.message, "alert_channel")
        log_channel = await self.db_get_guildinfo(ctx.message, "log_channel")
        try:
            silence_role = discord.utils.get(ctx.guild.roles, name="Silenced")
            await target.add_roles(silence_role, reason=f"Manual request by {ctx.author.name}#{ctx.author.discriminator} with reason {reason}")
        except discord.errors.Forbidden:
            await ctx.send("Failed to silence that user: Missing Permissions")
            return
        except:
            await ctx.send("Failed to silence that user.")
            return
        await ctx.send("User has been silenced")
        if log_channel > 0:
            log_channel = ctx.guild.get_channel(log_channel)
            await log_channel.send(f"```Manual Silence: {ctx.target.name}#{ctx.target.discriminator} was silenced for {reason} by {ctx.author.name}#{ctx.author.discriminator}.```")

    @commands.command()
    @commands.guild_only()
    async def unsilence(self, ctx: commands.Context, target: discord.Member, reason: str = '[Unknown]'):
        """Unsilence a user"""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        alert_channel = await self.db_get_guildinfo(ctx.message, "alert_channel")
        log_channel = await self.db_get_guildinfo(ctx.message, "log_channel")
        try:
            silence_role = discord.utils.get(ctx.guild.roles, name="Silenced")
            await target.remove_roles(silence_role, reason=f"Pressure System: Manual request by {ctx.author.name}#{ctx.author.discriminator} with reason {reason}")
        except discord.errors.Forbidden:
            await ctx.send("Failed to unsilence that user: Missing Permissions")
            return
        except:
            await ctx.send("Failed to unsilence that user.")
            return
        await ctx.send("User has been unsilenced")
        if log_channel > 0:
            log_channel = ctx.guild.get_channel(log_channel)
            await log_channel.send(f"```Manual Unsilence: {ctx.target.name}#{ctx.target.discriminator} was unsilenced for {reason} by {ctx.author.name}#{ctx.author.discriminator}.```")

    @commands.command()
    @commands.guild_only()
    async def getconfig(self, ctx, value: str = None):
        """View the pressure system config values"""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if not value:
            await ctx.send("Valid fields: `Spam`")
            return
        #if value.lower() == "raid":
        #    await ctx.send("This function isn't finished yet!")
        if value.lower() == "spam":
            max_pressure = await self.db_get_guildinfo(ctx.message, "max_pressure")
            base_pressure = await self.db_get_guildinfo(ctx.message, "base_pressure")
            embed_pressure = await self.db_get_guildinfo(ctx.message, "embed_pressure")
            length_pressure = await self.db_get_guildinfo(ctx.message, "length_pressure")
            line_pressure = await self.db_get_guildinfo(ctx.message, "line_pressure")
            ping_pressure = await self.db_get_guildinfo(ctx.message, "ping_pressure")
            repeat_pressure = await self.db_get_guildinfo(ctx.message, "repeat_pressure")
            await ctx.send(
                f"```ImagePressure: {embed_pressure}\n"
                f"PingPressure: {ping_pressure}\n"
                f"LengthPressure: {length_pressure}\n"
                f"RepeatPressure: {repeat_pressure}\n"
                f"LinePressure: {line_pressure}\n"
                f"BasePressure: {base_pressure}\n"
                f"MaxPressure: {max_pressure}```"
            )

    @commands.group(autohelp=True)
    @commands.guild_only()
    async def setconfig(self, ctx):
        """Manage pressure settings"""
        pass

    @setconfig.command(name="togglepressure")
    async def setconfig_filter(self, ctx: commands.Context):
        """Toggles the anti-spam system on/off."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        system_active = await self.db_get_guildinfo(ctx.message, "system_active")
        if system_active == 0:
            await self.db_update_guild(ctx.message, "system_active", 1)
            await ctx.send("System toggled on")
        else:
            await self.db_update_guild(ctx.message, "system_active", 0)
            await ctx.send("System toggled off")

    @setconfig.command(name="imagepressure")
    async def setconfig_imagepressure(self, ctx: commands.Context, image_pressure: float):
        """Additional pressure generated by each image, link or attachment in a message. 
        Defaults to (MaxPressure - BasePressure) / 6 = 8.3, 
        instantly silencing anyone posting 6 or more links at once."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if image_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "embed_pressure", image_pressure)
        await ctx.send(f"Set the image pressure to {image_pressure} per attachment.")

    @setconfig.command(name="pingpressure")
    async def setconfig_pingpressure(self, ctx: commands.Context, ping_pressure: float):
        """Additional pressure generated by each unique ping in a message. 
        Defaults to (MaxPressure - BasePressure) / 20 = 2.5, instantly silencing 
        anyone pinging 20 or more people at once."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if ping_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "ping_pressure", ping_pressure)
        await ctx.send(f"Set the image pressure to {ping_pressure} per mention.")

    @setconfig.command(name="lengthpressure")
    async def setconfig_lengthpressure(self, ctx: commands.Context, len_pressure: float):
        """Additional pressure generated by each individual character in the message. 
        Discord allows messages up to 2000 characters in length. 
        Defaults to (MaxPressure - BasePressure) / 8000 = 0.00625, silencing 
        anyone posting 3 huge messages at the same time."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if len_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "length_pressure", len_pressure)
        await ctx.send(f"Set the length pressure to {len_pressure} per character.")

    @setconfig.command(name="repeatpressure")
    async def setconfig_repeatpressure(self, ctx: commands.Context, repeat_pressure: float):
        """Additional pressure generated by a message that is identical to the previous message sent (ignores case). 
        Defaults to BasePressure, effectively doubling the pressure penalty for repeated messages."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if repeat_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "repeat_pressure", repeat_pressure)
        await ctx.send(f"Set the repeat pressure to {repeat_pressure} per repeated message.")

    @setconfig.command(name="linepressure")
    async def setconfig_linepressure(self, ctx: commands.Context, line_pressure: float):
        """Additional pressure generated by each newline in the message. 
        Defaults to (MaxPressure - BasePressure) / 70 = 0.714, silencing 
        anyone posting more than 70 newlines in a single message"""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if line_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "line_pressure", line_pressure)
        await ctx.send(f"Set the repeat pressure to {line_pressure} per new line")

    @setconfig.command(name="basepressure")
    async def setconfig_basepressure(self, ctx: commands.Context, base_pressure: float):
        """The base pressure generated by sending a message, regardless of length or content. Defaults to 10"""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if base_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        await self.db_update_guild(ctx.message, "base_pressure", base_pressure)
        await ctx.send(f"Set the base pressure to {base_pressure} for every message sent")

    @setconfig.command(name="maxpressure")
    async def setconfig_maxpressure(self, ctx: commands.Context, max_pressure: float):
        """The maximum pressure allowed. If a user's pressure exceeds this amount, they will be silenced. 
        Defaults to 60, which is intended to silence after a maximum of 6 short messages sent in rapid succession."""
        role_name = await self.db_get_guildinfo(ctx.message, "mod_role")
        if role_name == "":
            await ctx.send(f"The server owner must run `{ctx.clean_prefix}setup` before using this command!")
            return
        mod_role = discord.utils.get(ctx.guild.roles, name=f"{role_name}")
        if mod_role not in ctx.author.roles:
            await ctx.send("You lack the permissions to use this command!")
            return
        # ------------------------------------------------------------------------------------------------------
        if max_pressure <= 0:
            await ctx.send("Invalid Value. Value must be greater than 0.")
            return
        if max_pressure < await self.db_get_guildinfo(ctx.message, "base_pressure"):
            await ctx.send("Warning: This will silence anyone who speaks! It is recommended that you increase this value to a larger number than the base pressure.")
        await self.db_update_guild(ctx.message, "max_pressure", max_pressure)
        await ctx.send(f"Set the maximum pressure before silencing a user to {max_pressure}.")


    @commands.command()
    @checks.guildowner()
    @checks.bot_has_permissions(manage_roles=True, manage_guild=True)
    @commands.guild_only()
    async def setup(self, ctx: commands.Context, mod_role: discord.Role, alert_channel: discord.TextChannel, log_channel: discord.TextChannel):
        silence_role = discord.utils.get(ctx.guild.roles, name="Silenced")
        if silence_role == None:
            await ctx.guild.create_role(name="Silenced", color=discord.Color(0xb3b3b3))
        silence_role = discord.utils.get(ctx.guild.roles, name="Silenced")
        await ctx.send("Denying the Silenced role permissions to speak in channels...\n*This may take a while for servers with a large number of channels, please do not create any channels during this time.*")
        for channel in ctx.guild.channels:
            await channel.set_permissions(silence_role, send_messages=False)
        await self.db_update_guild(ctx.message, "mod_role", str(mod_role.name))
        await self.db_update_guild(ctx.message, "alert_channel", int(alert_channel.id))
        await self.db_update_guild(ctx.message, "log_channel", int(log_channel.id))
        await ctx.send(
            f"```Server Configured!\nModerator Role: {mod_role.name}\nMod Channel: #{alert_channel.name}\nLog Channel #{log_channel.name}\n\nNote: You need to move too much the Silenced role above all other member roles!\n{log_channel_msg}```"
            )


    async def check_pressure(self, message, reason, before_pressure):
        # Handles pressure exceeding the max pressure cap
        max_pressure = await self.db_get_guildinfo(message, "max_pressure")
        alert_channel = await self.db_get_guildinfo(message, "alert_channel")
        log_channel = await self.db_get_guildinfo(message, "log_channel")
        if alert_channel == 0:
            return
        pressure = await self.db_get_userinfo(message, "pressure")
        if pressure < max_pressure:
            return
        alert_channel = message.guild.get_channel(alert_channel)
        try:
            silence_role = discord.utils.get(message.guild.roles, name="Silenced")
            await message.author.add_roles(silence_role, reason=f"Pressure System: Exceeded max pressure by {reason}")
            role_error = ""
        except:
            role_error = "\n:warning: Failed to add the Silenced role to this user!"
        await alert_channel.send(f"Alert: {message.author.mention} was silenced for {reason}. Please investigate.{role_error}")
        if log_channel > 0:
            log_channel = message.guild.get_channel(log_channel)
            await log_channel.send(f"```Silencing spammer {message.author.display_name} (pressure: {before_pressure} -> {pressure}). Last message sent on #{message.channel.name} in {message.guild.name}:\n{message.content}```")
        return

    async def get_msg_time(self, message, last_msg_id):
        # Checks for time passed to remove pressure with the decay
        try:
            last_msg_time = int(await self.db_get_userinfo(message, "last_sent_at"))
        except:
            last_msg_time = calendar.timegm(await self.db_get_userinfo(message, "last_sent_at"))
        current_msg_time = calendar.timegm(message.created_at.utctimetuple())
        time_passed = current_msg_time - last_msg_time
        await self.db_update_user(message, "last_msg_id", message.id)
        await self.db_update_user(message, "last_sent_at", calendar.timegm(message.created_at.utctimetuple()))
        return time_passed

    async def remove_pressure(self, message, time_passed, pressure):
        # Remove from pressure decay
        negative_pressure = int((time_passed / 2) * 4)
        new_pressure = pressure - negative_pressure
        if new_pressure < 0:
            new_pressure = 0
        await self.db_update_user(message, "pressure", new_pressure)
        return new_pressure

    async def add_pressure(self, message):
        # Add pressure for every message and return a reason for silencing
        # Need to find better way to handle reasons
        reason = "`Error - You shouln't see this!`"
        max_pressure = await self.db_get_guildinfo(message, "max_pressure")
        base_pressure = await self.db_get_guildinfo(message, "base_pressure")
        embed_pressure = await self.db_get_guildinfo(message, "embed_pressure")
        length_pressure = await self.db_get_guildinfo(message, "length_pressure")
        line_pressure = await self.db_get_guildinfo(message, "line_pressure")
        ping_pressure = await self.db_get_guildinfo(message, "ping_pressure")
        repeat_pressure = await self.db_get_guildinfo(message, "repeat_pressure")
        pressure = await self.db_get_userinfo(message, "pressure")
        last_msg_content = await self.db_get_userinfo(message, "last_msg_content")
        # --------------------------------------------------------------------
        embeds = 0
        await self.db_update_user(message, "last_msg_id", message.id)
        new_pressure = pressure + base_pressure
        if new_pressure > max_pressure:
            reason = "sending too many messages"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        if message.attachments:
            for attachments in message.attachments:
                embeds = embeds + 1
            new_pressure = new_pressure + (embed_pressure * embeds)
        if new_pressure > max_pressure:
            reason = "attaching too many files"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        msg_length = len(message.content)
        new_pressure = new_pressure + (msg_length * length_pressure)
        if new_pressure > max_pressure:
            reason = "using too many characters"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        new_lines = message.content.count("\n")
        new_pressure = new_pressure + (new_lines + line_pressure)
        if new_pressure > max_pressure:
            reason = "sending too many newlines"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        message_pings = len(message.mentions)
        new_pressure = new_pressure + (message_pings * ping_pressure)
        if new_pressure > max_pressure:
            reason = "using too many mentions"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        if str(message.content.lower()) == str(last_msg_content.lower()):
            new_pressure = new_pressure + repeat_pressure
        if new_pressure > max_pressure:
            reason = "copy+pasting a message"
            await self.db_update_user(message, "pressure", new_pressure)
            return reason
        await self.db_update_user(message, "pressure", new_pressure)
        await self.db_update_user(message, "last_msg_content", str(message.content))
        return

    async def first_msg_pressure(self, message):
        # Probably need to make this work better... 
        # Determines the pressure to be added for the first logged message by a user
        base_pressure = await self.db_get_guildinfo(message, "base_pressure")
        embed_pressure = await self.db_get_guildinfo(message, "embed_pressure")
        length_pressure = await self.db_get_guildinfo(message, "length_pressure")
        line_pressure = await self.db_get_guildinfo(message, "line_pressure")
        ping_pressure = await self.db_get_guildinfo(message, "ping_pressure")
        pressure = await self.db_get_userinfo(message, "pressure")
        await self.db_update_user(message, "last_sent_at", calendar.timegm(message.created_at.utctimetuple()))
        embeds = 0
        await self.db_update_user(message, "last_msg_id", message.id)
        new_pressure = pressure + base_pressure
        if message.attachments:
            for attachments in message.attachments:
                embeds = embeds + 1
            new_pressure = new_pressure + (embed_pressure * embeds)
        msg_length = len(message.content)
        new_pressure = new_pressure + (msg_length * length_pressure)
        new_lines = message.content.count("\n")
        new_pressure = new_pressure + (new_lines + line_pressure)
        message_pings = len(message.mentions)
        new_pressure = new_pressure + (message_pings * ping_pressure)
        return new_pressure

    async def db_get_userinfo(self, message, entry_name):
        user = message.author
        userinfo = db.users.find_one({"_id": user.id})
        if not userinfo:
            data = userdata(user)
            db.users.insert_one(data)
            userinfo = db.users.find_one({"_id": user.id})
        entry_value = userinfo[f"{entry_name}"]
        return entry_value

    async def db_get_guildinfo(self, message, entry_name):
        guild = message.guild
        guildinfo = db.guilds.find_one({"_id": guild.id})
        if not guildinfo:
            data = guilddata(guild)
            db.guilds.insert_one(data)
            guildinfo = db.guilds.find_one({"_id": guild.id})
        try:
            entry_value = guildinfo[f"{entry_name}"]
        except:
            await self.fix_get_guildinfo(message, entry_name)
            entry_value = guildinfo[f"{entry_name}"]
        return entry_value

    async def db_update_user(self, message, entry_name, entry_value):
        user = message.author
        userinfo = db.users.find_one({"_id": user.id})
        if not userinfo:
            data = userdata(user)
            db.users.insert_one(data)
            userinfo = db.users.find_one({"_id": user.id})
        userinfo["{entry_name}".format(entry_name=entry_name)] = entry_value
        db.users.replace_one({"_id": user.id}, userinfo, upsert=True)
        return

    async def db_update_guild(self, message, entry_name, entry_value):
        guild = message.guild
        guildinfo = db.guilds.find_one({"_id": guild.id})
        if not guildinfo:
            data = guilddata(guild)
            db.guilds.insert_one(data)
            guildinfo = db.guilds.find_one({"_id": guild.id})
        try:
            guildinfo[f"{entry_name}"] = entry_value
        except:
            await self.fix_guild_db(message, entry_name, entry_value)
            guildinfo[f"{entry_name}"] = entry_value
        db.guilds.replace_one({"_id": guild.id}, guildinfo, upsert=True)
        return
