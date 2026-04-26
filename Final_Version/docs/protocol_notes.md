# Protocol Notes

## Transport

- TCP sockets
- UTF-8 JSON objects separated by newline characters
- Client and server both use the shared `shared/messages.py` encoder/decoder

## Main Message Flow

### Join

Client:

```json
{"type":"join","username":"player_one"}
```

Server:

```json
{"type":"joined","username":"player_one","profile":{...},"controls":{...}}
```

### Lobby Refresh

Client:

```json
{"type":"request_lobby"}
```

Server:

```json
{
  "type":"lobby_state",
  "users":[{"username":"player_one","status":"lobby","map":"Desert"}],
  "messages":["player_one: hello"],
  "active_matches":[{"match_id":"a_vs_b_123","players":["a","b"],"spectators":1}],
  "incoming_invites":[{"from":"rival"}]
}
```

### Invite

Client:

```json
{"type":"invite_player","target":"rival"}
```

Server:

```json
{"type":"invite_sent","target":"rival"}
```

Target receives:

```json
{"type":"invite_received","from":"player_one"}
```

### Private Lobby Chat

Client opens a private chat window:

```json
{"type":"open_private_chat","target":"rival"}
```

Server confirms the private chat can be opened:

```json
{"type":"private_chat_opened","peer":"rival"}
```

Client sends a private lobby message:

```json
{"type":"send_private_lobby_chat","target":"rival","text":"Ready after this match?"}
```

Only the sender and receiver receive the routed private message:

```json
{
  "type":"private_lobby_chat",
  "from":"player_one",
  "to":"rival",
  "text":"Ready after this match?",
  "timestamp":"14:32"
}
```

Private chat errors are sent only to the requesting client:

```json
{"type":"private_chat_error","target":"rival","message":"Player is disconnected."}
```

If a private-chat peer disconnects, the other peer receives:

```json
{"type":"private_chat_status","peer":"rival","message":"Player disconnected","online":false,"timestamp":"14:35"}
```

### Match Start

Server:

```json
{
  "type":"match_started",
  "players":["player_one","rival"],
  "snapshot":{...}
}
```

### Real-Time State

Server sends periodic snapshots:

```json
{"type":"match_state","snapshot":{...}}
```

### Input

Client:

```json
{"type":"action","action":"up"}
```

### Match End

Server:

```json
{
  "type":"match_over",
  "winner":"player_one",
  "scores":{"player_one":70,"rival":52},
  "snapshot":{...}
}
```

## Design Notes

- The server is authoritative.
- Clients never send raw positions.
- Match settings come from saved profile data and are applied when an invite becomes a match.
- Spectators receive the same `match_state` snapshots as players.
- Arena Blessings are server-spawned power-ups with shield, boost, or drain effects.
- Private lobby chat is routed only to the sender and target; it is not added to global lobby chat.
