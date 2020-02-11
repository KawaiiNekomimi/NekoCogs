try:
    import pymongo
    from pymongo import MongoClient
except:
    raise RuntimeError("Can't load pymongo. Use 'pip3 install pymongo'!")

try:
    client = MongoClient()
    db = client['pressure']
except:
    print("Can't load database. Follow instructions on Git/online to install MongoDB.")

def userdata(user):
    return {
        "_id": user.id,
        "username": user.name,
        "pressure": 0,
        "last_msg_id": 0,
        "last_sent_at": 0,
        "last_msg_content": "",
        # For future use
        "has_joinrole": True
    }

def guilddata(guild):
    return {
        "_id": guild.id,
        "guildname": guild.name,
        "system_active": 0,
        "max_pressure": 60,
        "base_pressure": 10,
        "embed_pressure": 8.3,
        "length_pressure": 0.00625,
        "line_pressure": 0.714,
        "ping_pressure": 2.5,
        "repeat_pressure": 10,
        "alert_channel": 0,
        "log_channel": 0,
        "mod_role": "",
        # For future use 
        "users_joined": [],
        "raid_size": 4,
        "raid_time": 240,
        "lockdown_duration": 120
        "pressure_decay": 4,
        "sec_decay": 2,
    }
    
