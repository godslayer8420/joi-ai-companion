package com.aurion.mobile

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.aurion.mobile.databinding.ActivityVideoCallBinding
import org.json.JSONObject
import org.webrtc.*

private const val TAG = "VideoCallActivity"
private const val CAMERA_AUDIO_PERM_REQUEST = 1001

/**
 * Full-duplex video call between the user and Aurion's Python backend.
 *
 * Layout:
 *  - fullscreen [remoteSurfaceView]  — Aurion's camera / avatar feed
 *  - PiP        [localSurfaceView]   — user's front camera
 *  - FAB        [fabHangup]          — end call
 *
 * How it works:
 *  1. Both sides connect to webrtc_signaling.py via Socket.IO (/signal namespace).
 *  2. Android captures camera → adds to PeerConnection.
 *  3. Android creates SDP offer → sends via SignalingClient.
 *  4. Python backend answers → Android sets remote description.
 *  5. ICE candidates exchange automatically.
 *  6. Remote track rendered on [remoteSurfaceView].
 */
class VideoCallActivity : AppCompatActivity(), SignalingClient.Listener {

    private lateinit var binding: ActivityVideoCallBinding
    private var peerConnectionFactory: PeerConnectionFactory? = null
    private var peerConnection: PeerConnection? = null
    private var signalingClient: SignalingClient? = null
    private var localVideoTrack: VideoTrack? = null
    private var localAudioTrack: AudioTrack? = null
    private var eglBase: EglBase? = null

    // -------------------------------------------------------------------------
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVideoCallBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.fabHangup.setOnClickListener { hangup() }

        if (hasPermissions()) {
            initWebRtc()
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO),
                CAMERA_AUDIO_PERM_REQUEST,
            )
        }
    }

    private fun hasPermissions() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED &&
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_AUDIO_PERM_REQUEST &&
            grantResults.all { it == PackageManager.PERMISSION_GRANTED }
        ) {
            initWebRtc()
        } else {
            Toast.makeText(this, "Camera and mic required for video call", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    // -------------------------------------------------------------------------
    private fun initWebRtc() {
        eglBase = EglBase.create()

        // Initialise the WebRTC native library once per process
        PeerConnectionFactory.initialize(
            PeerConnectionFactory.InitializationOptions.builder(applicationContext)
                .setEnableInternalTracer(false)
                .createInitializationOptions()
        )

        val encoderFactory = DefaultVideoEncoderFactory(eglBase!!.eglBaseContext, true, true)
        val decoderFactory = DefaultVideoDecoderFactory(eglBase!!.eglBaseContext)

        peerConnectionFactory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(encoderFactory)
            .setVideoDecoderFactory(decoderFactory)
            .createPeerConnectionFactory()

        // Surface renderers
        binding.localSurfaceView.init(eglBase!!.eglBaseContext, null)
        binding.localSurfaceView.setMirror(true)
        binding.remoteSurfaceView.init(eglBase!!.eglBaseContext, null)

        // Local camera capture
        val capturer = createCameraCapturer()
        if (capturer != null) {
            val videoSource = peerConnectionFactory!!.createVideoSource(capturer.isScreencast)
            capturer.initialize(
                SurfaceTextureHelper.create("CaptureThread", eglBase!!.eglBaseContext),
                applicationContext,
                videoSource.capturerObserver,
            )
            capturer.startCapture(640, 480, 30)

            localVideoTrack = peerConnectionFactory!!.createVideoTrack("ARDAMSv0", videoSource)
            localVideoTrack?.addSink(binding.localSurfaceView)
        }

        val audioSource = peerConnectionFactory!!.createAudioSource(MediaConstraints())
        localAudioTrack = peerConnectionFactory!!.createAudioTrack("ARDAMSa0", audioSource)

        createPeerConnection()

        // Connect signaling
        signalingClient = SignalingClient(listener = this)
        signalingClient?.connect()
    }

    private fun createCameraCapturer(): CameraVideoCapturer? {
        val enumerator = Camera2Enumerator(this)
        // Prefer front camera
        for (name in enumerator.deviceNames) {
            if (enumerator.isFrontFacing(name)) {
                return enumerator.createCapturer(name, null)
            }
        }
        for (name in enumerator.deviceNames) {
            if (!enumerator.isFrontFacing(name)) {
                return enumerator.createCapturer(name, null)
            }
        }
        return null
    }

    private fun createPeerConnection() {
        val iceServers = listOf(
            PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer(),
        )
        val config = PeerConnection.RTCConfiguration(iceServers).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
        }

        peerConnection = peerConnectionFactory?.createPeerConnection(config, object : PeerConnection.Observer {
            override fun onIceCandidate(candidate: IceCandidate) {
                val json = JSONObject()
                    .put("sdpMid", candidate.sdpMid)
                    .put("sdpMLineIndex", candidate.sdpMLineIndex)
                    .put("sdp", candidate.sdp)
                signalingClient?.sendIceCandidate(json)
            }
            override fun onTrack(transceiver: RtpTransceiver) {
                val track = transceiver.receiver.track()
                if (track is VideoTrack) {
                    runOnUiThread {
                        track.addSink(binding.remoteSurfaceView)
                        binding.remoteSurfaceView.visibility = View.VISIBLE
                    }
                }
            }
            override fun onSignalingChange(state: PeerConnection.SignalingState) {}
            override fun onIceConnectionChange(state: PeerConnection.IceConnectionState) {
                Log.d(TAG, "ICE: $state")
                if (state == PeerConnection.IceConnectionState.DISCONNECTED ||
                    state == PeerConnection.IceConnectionState.FAILED) {
                    runOnUiThread { hangup() }
                }
            }
            override fun onIceConnectionReceivingChange(b: Boolean) {}
            override fun onIceGatheringChange(state: PeerConnection.IceGatheringState) {}
            override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>) {}
            override fun onAddStream(stream: MediaStream) {}
            override fun onRemoveStream(stream: MediaStream) {}
            override fun onDataChannel(channel: DataChannel) {}
            override fun onRenegotiationNeeded() {}
            override fun onAddTrack(receiver: RtpReceiver, streams: Array<out MediaStream>) {}
            override fun onConnectionChange(state: PeerConnection.PeerConnectionState) {}
        })

        // Add local tracks
        localVideoTrack?.let { peerConnection?.addTrack(it) }
        localAudioTrack?.let { peerConnection?.addTrack(it) }
    }

    // -------------------------------------------------------------------------
    // SignalingClient.Listener
    // -------------------------------------------------------------------------
    override fun onPeerJoined(role: String) {
        Log.d(TAG, "Peer joined, our role: $role")
        if (role == "caller") {
            // We are first — create and send offer
            val constraints = MediaConstraints().apply {
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "true"))
                mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "true"))
            }
            peerConnection?.createOffer(object : SimpleSdpObserver() {
                override fun onCreateSuccess(sdp: SessionDescription) {
                    peerConnection?.setLocalDescription(SimpleSdpObserver(), sdp)
                    signalingClient?.sendOffer(sdp.description)
                }
            }, constraints)
        }
    }

    override fun onOffer(sdp: String) {
        val desc = SessionDescription(SessionDescription.Type.OFFER, sdp)
        peerConnection?.setRemoteDescription(SimpleSdpObserver(), desc)
        peerConnection?.createAnswer(object : SimpleSdpObserver() {
            override fun onCreateSuccess(answer: SessionDescription) {
                peerConnection?.setLocalDescription(SimpleSdpObserver(), answer)
                signalingClient?.sendAnswer(answer.description)
            }
        }, MediaConstraints())
    }

    override fun onAnswer(sdp: String) {
        val desc = SessionDescription(SessionDescription.Type.ANSWER, sdp)
        peerConnection?.setRemoteDescription(SimpleSdpObserver(), desc)
    }

    override fun onIceCandidate(candidate: JSONObject) {
        val ice = IceCandidate(
            candidate.optString("sdpMid"),
            candidate.optInt("sdpMLineIndex"),
            candidate.optString("sdp"),
        )
        peerConnection?.addIceCandidate(ice)
    }

    override fun onPeerLeft() {
        runOnUiThread {
            Toast.makeText(this, "Aurion ended the call", Toast.LENGTH_SHORT).show()
            hangup()
        }
    }

    override fun onError(message: String) {
        Log.e(TAG, "Signaling error: $message")
        runOnUiThread {
            Toast.makeText(this, "Call error: $message", Toast.LENGTH_SHORT).show()
        }
    }

    // -------------------------------------------------------------------------
    private fun hangup() {
        signalingClient?.disconnect()
        peerConnection?.close()
        localVideoTrack?.dispose()
        localAudioTrack?.dispose()
        peerConnectionFactory?.dispose()
        eglBase?.release()
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        hangup()
    }
}

/** Convenience base with no-op implementations for SdpObserver. */
open class SimpleSdpObserver : SdpObserver {
    override fun onCreateSuccess(sdp: SessionDescription) {}
    override fun onSetSuccess() {}
    override fun onCreateFailure(error: String) { Log.e("SdpObserver", "create failed: $error") }
    override fun onSetFailure(error: String) { Log.e("SdpObserver", "set failed: $error") }
}
