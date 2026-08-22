"""
webrtc_signaling.py — Aurion WebRTC Signaling Server

Relays SDP offer/answer and ICE candidates between the Android app
and the Python backend so Aurion can show a live video call face.

Run standalone:
    python webrtc_signaling.py

Or import and register onto an existing Flask app:
    from webrtc_signaling import register_signaling
    register_signaling(app)        # attaches /signal namespace via SocketIO

Rooms:
    Each call session gets a room named by its call_id UUID.
    Android joins as "caller", Python backend joins as "callee".

Socket events (client → server):
    join        {call_id}            — join/create room
    offer       {call_id, sdp}       — caller sends SDP offer
    answer      {call_id, sdp}       — callee sends SDP answer
    ice         {call_id, candidate} — either side sends ICE candidate
    leave       {call_id}            — tear down room

Socket events (server → client):
    peer_joined {role}               — other peer entered the room
    offer       {sdp}                — forwarded offer
    answer      {sdp}                — forwarded answer
    ice         {candidate}          — forwarded ICE candidate
    peer_left   {}                   — other peer disconnected
    error       {message}            — signaling error
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Set

logger = logging.getLogger("aurion.signaling")

# ---------------------------------------------------------------------------
# Lazy imports — flask-socketio is optional; graceful degradation if absent
# ---------------------------------------------------------------------------
try:
    from flask import Flask
    from flask_socketio import SocketIO, join_room, leave_room, emit, rooms
    _SOCKETIO_AVAILABLE = True
except ImportError:
    _SOCKETIO_AVAILABLE = False
    logger.warning("flask-socketio not installed — WebRTC signaling disabled. "
                   "Run: pip install flask-socketio")

# ---------------------------------------------------------------------------
# In-memory room registry  {call_id: {sid, sid}}
# ---------------------------------------------------------------------------
_rooms: Dict[str, Set[str]] = {}
_sid_to_call: Dict[str, str] = {}   # reverse map for disconnect cleanup

MAX_ROOM_SIZE = 2


def _room_role(call_id: str, sid: str) -> str:
    """First joiner = caller, second = callee."""
    members = _rooms.get(call_id, set())
    sids = list(members)
    if not sids:
        return "caller"
    return "caller" if sids[0] == sid else "callee"


def register_signaling(app: "Flask", socketio: "SocketIO | None" = None,
                       cors_allowed_origins: str = "*") -> "SocketIO":
    """
    Attach signaling namespace /signal to *app*.

    If *socketio* is provided (e.g. already created by web_ui.py) the
    namespace is registered on it.  Otherwise a new SocketIO instance is
    created and returned.
    """
    if not _SOCKETIO_AVAILABLE:
        logger.error("flask-socketio unavailable; signaling not registered.")
        return None  # type: ignore

    if socketio is None:
        socketio = SocketIO(app, cors_allowed_origins=cors_allowed_origins,
                            async_mode="threading", logger=False,
                            engineio_logger=False)

    ns = "/signal"

    @socketio.on("join", namespace=ns)
    def on_join(data):
        call_id = str(data.get("call_id", "default"))
        from flask_socketio import request as sio_req
        sid = sio_req.sid

        if call_id not in _rooms:
            _rooms[call_id] = set()

        if len(_rooms[call_id]) >= MAX_ROOM_SIZE:
            emit("error", {"message": "Room full"}, namespace=ns)
            return

        _rooms[call_id].add(sid)
        _sid_to_call[sid] = call_id
        join_room(call_id, namespace=ns)

        role = _room_role(call_id, sid)
        emit("peer_joined", {"role": role}, room=call_id, namespace=ns,
             include_self=False)
        logger.info(f"[{call_id}] {sid[:8]} joined as {role}")

    @socketio.on("offer", namespace=ns)
    def on_offer(data):
        call_id = data.get("call_id")
        if call_id and data.get("sdp"):
            emit("offer", {"sdp": data["sdp"]}, room=call_id, namespace=ns,
                 include_self=False)

    @socketio.on("answer", namespace=ns)
    def on_answer(data):
        call_id = data.get("call_id")
        if call_id and data.get("sdp"):
            emit("answer", {"sdp": data["sdp"]}, room=call_id, namespace=ns,
                 include_self=False)

    @socketio.on("ice", namespace=ns)
    def on_ice(data):
        call_id = data.get("call_id")
        if call_id and data.get("candidate"):
            emit("ice", {"candidate": data["candidate"]}, room=call_id,
                 namespace=ns, include_self=False)

    @socketio.on("leave", namespace=ns)
    def on_leave(data):
        call_id = str(data.get("call_id", ""))
        _cleanup_sid(call_id, _get_sid())

    @socketio.on("disconnect", namespace=ns)
    def on_disconnect():
        sid = _get_sid()
        call_id = _sid_to_call.get(sid)
        if call_id:
            _cleanup_sid(call_id, sid)

    return socketio


def _get_sid() -> str:
    try:
        from flask_socketio import request as sio_req
        return sio_req.sid
    except Exception:
        return ""


def _cleanup_sid(call_id: str, sid: str) -> None:
    if call_id in _rooms:
        _rooms[call_id].discard(sid)
        if not _rooms[call_id]:
            del _rooms[call_id]
        else:
            from flask_socketio import emit as _emit
            _emit("peer_left", {}, room=call_id, namespace="/signal",
                  include_self=False)
    _sid_to_call.pop(sid, None)
    leave_room(call_id, namespace="/signal")
    logger.info(f"[{call_id}] {sid[:8]} left")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if not _SOCKETIO_AVAILABLE:
        print("Install flask-socketio first:  pip install flask-socketio")
        raise SystemExit(1)

    _app = Flask(__name__)
    _app.config["SECRET_KEY"] = os.environ.get("SIGNALING_SECRET", "aurion-dev-secret")
    _sio = register_signaling(_app)
    port = int(os.environ.get("SIGNALING_PORT", 7861))
    print(f"Aurion WebRTC signaling server on ws://0.0.0.0:{port}/signal")
    _sio.run(_app, host="0.0.0.0", port=port, debug=False)
