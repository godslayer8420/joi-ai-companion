package com.aurion.mobile

import android.util.Log
import io.socket.client.IO
import io.socket.client.Socket
import org.json.JSONObject
import java.net.URI
import java.util.UUID

private const val TAG = "AurionSignaling"

/** Thin wrapper around Socket.IO that handles the /signal namespace. */
class SignalingClient(
    private val serverUrl: String = "http://10.0.2.2:7861",
    private val callId: String = UUID.randomUUID().toString(),
    private val listener: Listener,
) {

    interface Listener {
        fun onPeerJoined(role: String)
        fun onOffer(sdp: String)
        fun onAnswer(sdp: String)
        fun onIceCandidate(candidate: JSONObject)
        fun onPeerLeft()
        fun onError(message: String)
    }

    private var socket: Socket? = null

    fun connect() {
        try {
            val opts = IO.Options.builder()
                .setPath("/socket.io")
                .build()
            socket = IO.socket(URI.create("$serverUrl/signal"), opts).also { s ->
                s.on("peer_joined") { args ->
                    val role = (args.firstOrNull() as? JSONObject)?.optString("role", "caller") ?: "caller"
                    listener.onPeerJoined(role)
                }
                s.on("offer") { args ->
                    val sdp = (args.firstOrNull() as? JSONObject)?.optString("sdp") ?: return@on
                    listener.onOffer(sdp)
                }
                s.on("answer") { args ->
                    val sdp = (args.firstOrNull() as? JSONObject)?.optString("sdp") ?: return@on
                    listener.onAnswer(sdp)
                }
                s.on("ice") { args ->
                    val candidate = (args.firstOrNull() as? JSONObject)?.optJSONObject("candidate") ?: return@on
                    listener.onIceCandidate(candidate)
                }
                s.on("peer_left") { _ -> listener.onPeerLeft() }
                s.on("error") { args ->
                    val msg = (args.firstOrNull() as? JSONObject)?.optString("message", "unknown") ?: "unknown"
                    listener.onError(msg)
                }
                s.on(Socket.EVENT_CONNECT_ERROR) { args ->
                    listener.onError("Socket connect error: ${args.firstOrNull()}")
                }
                s.connect()
            }
            // Join room after connect
            socket?.on(Socket.EVENT_CONNECT) {
                socket?.emit("join", JSONObject().put("call_id", callId))
                Log.d(TAG, "Connected and joined room $callId")
            }
        } catch (e: Exception) {
            Log.e(TAG, "connect failed", e)
            listener.onError(e.message ?: "connect failed")
        }
    }

    fun sendOffer(sdpString: String) {
        socket?.emit("offer", JSONObject()
            .put("call_id", callId)
            .put("sdp", sdpString))
    }

    fun sendAnswer(sdpString: String) {
        socket?.emit("answer", JSONObject()
            .put("call_id", callId)
            .put("sdp", sdpString))
    }

    fun sendIceCandidate(candidate: JSONObject) {
        socket?.emit("ice", JSONObject()
            .put("call_id", callId)
            .put("candidate", candidate))
    }

    fun disconnect() {
        socket?.emit("leave", JSONObject().put("call_id", callId))
        socket?.disconnect()
        socket = null
    }

    val currentCallId: String get() = callId
}
