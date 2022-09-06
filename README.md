# Raid Watcher
 
⚠️ Proof of concept. This will most likely not work with your system.

![Discord notifications](readme_assets/discord.png)

Raid Watcher takes in raw protos (GetRaidDetails and GymGetInfo) and sends 
notifications to Discord if the lobby size changed. As pictured above. 
It will keep these messages updated if the player count changes.

### Setup

- Clone, `pip install -r requirements.txt`,
`cp config.example.toml config.toml` and fill out the config
- I think this requires at least Python 3.10, though 3.9 could work too
- Redirect any raw protos to `http://<host>:<port>/raw`. They must be 
POST-requests with the body looking as follows.

```js
{
    "lat": 0.0,
    "lon": 0.0,    
    "contents": [
        {
            "type": 1,      // method id
            "payload": ""   // raw message
        },
        // ...
    ]
}
```

### Shortcomings

There's no way to know how long a lobby lasts without joining it, which I don't 
think is something we want to do. Raid Watcher will cache any Raid for 120s 
and update it if the player count changes. So sometimes it will process a new 
lobby as if it were an old one.

GetRaidDetailsProtos do not contain any information about the Gym. So Raid 
Watcher has to also listen for GymGetInfoProtos. If one comes in that has an 
active Raid, it will cache Gym information based on the Raid Seed for one hour. 
This means that it's possible to get messages without any Gym info. These will be updated 
if a later GymGetInfoProto is received.
