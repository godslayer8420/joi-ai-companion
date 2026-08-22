package com.aurion.mobile

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.aurion.mobile.databinding.ActivityMainBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Entry point — chat UI + video call launcher.
 *
 * Chat: sends messages to web_ui.py /chat endpoint via Retrofit.
 * Video: launches VideoCallActivity (WebRTC via webrtc_signaling.py on :7861).
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val chatHistory = StringBuilder()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnSend.setOnClickListener { sendMessage() }
        binding.editMessage.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) { sendMessage(); true } else false
        }
        binding.fabVideoCall.setOnClickListener {
            startActivity(Intent(this, VideoCallActivity::class.java))
        }
    }

    private fun sendMessage() {
        val text = binding.editMessage.text.toString().trim()
        if (text.isBlank()) return
        binding.editMessage.setText("")
        appendChat("You", text)
        binding.btnSend.isEnabled = false

        lifecycleScope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    AurionApiClient.api.chat(ChatRequest(message = text))
                }
                appendChat("Aurion", response.reply)
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                withContext(Dispatchers.Main) { binding.btnSend.isEnabled = true }
            }
        }
    }

    private fun appendChat(speaker: String, text: String) {
        chatHistory.append("$speaker: $text\n\n")
        binding.tvResponse.text = chatHistory
        // Auto-scroll
        binding.scrollChat.post {
            binding.scrollChat.fullScroll(View.FOCUS_DOWN)
        }
    }
}

