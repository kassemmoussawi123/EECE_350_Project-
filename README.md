# Πthon Arena

Πthon Arena is a polished client-server EECE 350 network programming project: a two-player online snake battle game built with Python, Pygame, sockets, threads, and a shared JSON-line protocol. The server remains authoritative for lobby state, invites, chat, spectator sessions, match timing, snakes, collisions, pies, Arena Blessings power-ups, scores, and winner determination. The client handles rendering, menus, controls, matchmaking flow, and gameplay HUD presentation.

## Features

- Centralized TCP server with authoritative game state.
- Pygame graphical client with splash, menu, connection, lobby, customization, match settings, waiting, gameplay, pause, spectator, end-game, help, credits, and settings screens.
- Lobby with online users, invite/cancel flow, lobby chat, and active match list.
- Real-time two-player snake gameplay with obstacles, pies, scores, health, timer, and winner logic.
- Spectator mode for live matches.
- In-match chat and emoji reactions.
- Creative feature: Arena Blessings power-ups (`shield`, `boost`, `drain`) for stronger demo quality and presentation.
- Uploaded images/screenshots reorganized into `assets/` and `docs/screenshots/`.

## Folder Structure

```text
Final_Version/
├── client/
│   ├── main.py
│   ├── network.py
│   ├── game.py
│   ├── renderer.py
│   ├── settings.py
│   └── ui/
│       ├── assets_loader.py
│       ├── screens.py
│       ├── theme.py
│       └── widgets.py
├── server/
│   ├── main.py
│   ├── game_state.py
│   ├── handlers.py
│   ├── lobby.py
│   ├── protocol.py
│   └── utils.py
├── shared/
│   ├── constants.py
│   ├── helpers.py
│   └── messages.py
├── assets/
│   ├── backgrounds/
│   ├── icons/
│   ├── images/
│   ├── sounds/
│   └── fonts/
├── docs/
│   ├── protocol_notes.md
│   └── screenshots/
├── README.md
├── requirements.txt
├── .gitignore
└── run_game.md
```

## Technologies Used

- Python 3.11+
- Pygame
- `socket`
- `threading`
- `json`
- Standard-library file/path management

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

## How to Run

### Start the server

```bash
python -m server.main
```

The default host/port is `0.0.0.0:5050`.

### Start a client

```bash
python -m client.main
```

Run two client instances for a local test on the same machine.

## Example Local Test Workflow

1. Open terminal A and start the server.
2. Open terminal B and launch the first client.
3. Open terminal C and launch the second client.
4. Connect both clients to `127.0.0.1` on port `5050`.
5. Set usernames, customize snakes, adjust match settings, and invite the opponent from the lobby.
6. Start the match, test movement, chat, reactions, spectating, and end-game flow.

## Controls

- Move: the keys chosen in the customization screen. Defaults are `W`, `A`, `S`, `D`.
- `Esc`: open/close the pause overlay during a match.
- `1`, `2`, `3`: send emoji reactions during a match.
- `Enter`: submit chat when the chat box is active.
- `Q` while paused: forfeit the match.
- `M` while paused: mute/unmute locally.
- `S` while paused: jump to settings.
- `Esc` in spectator mode: leave spectating.

## Protocol Overview

The game uses newline-delimited JSON messages. Every message contains a `type` field. Example groups:

- Client to server:
  - `join`
  - `save_profile`
  - `request_lobby`
  - `send_lobby_chat`
  - `invite_player`
  - `cancel_invite`
  - `respond_invite`
  - `spectate_match`
  - `leave_spectate`
  - `action`
  - `send_match_chat`
  - `emoji_reaction`
  - `forfeit_match`
- Server to client:
  - `joined`
  - `lobby_state`
  - `lobby_chat`
  - `invite_sent`
  - `invite_received`
  - `invite_cancelled`
  - `invite_response`
  - `match_started`
  - `spectate_started`
  - `match_state`
  - `match_chat`
  - `reaction`
  - `match_over`
  - `error`

More detailed notes are in [docs/protocol_notes.md](docs/protocol_notes.md).

## Screen Overview

- Splash screen with project branding.
- Main menu for navigation.
- Connection screen with validation.
- Lobby screen with online users, chat, invites, and spectate access.
- Snake customization screen for color/skin/control mapping.
- Match settings screen for map, duration, target score, and visual variation.
- Waiting screen while an invite is pending.
- Game screen with polished HUD.
- Pause overlay in-match.
- End-of-game results screen.
- Spectator view.
- Settings screen.
- Help and credits screens.

## Known Limitations

- The server currently supports many connected lobby users, but matches are organized as one independent thread-backed state object per active duel rather than a large multi-room scheduler.
- Audio files are not included in the uploaded assets, so volume controls are prepared in the UI but no live soundtrack is bundled.
- The lobby invite acceptance path is protocol-ready; if you want a clickable incoming-invite dialog instead of the current text-driven hint, that can be added as a next UI pass.

## Credits

- Course: EECE 350 Computing Networks
- Project theme and refactor: Πthon Arena
- Original uploaded materials: client code, server code, screenshots, and image assets
- Replace this section with final student names, IDs, and instructor/TAs before submission
