package com.aurion.mobile

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.aurion.mobile.databinding.ActivityMainBinding

/**
 * Entry point — connects to the Aurion Python backend via Retrofit.
 *
 * BLOCKED: Avatar rendering (GLB/SceneForm) and voice playback require the
 * MSIX voice packs from D:\Downloads\Others\Aurion files\. These are large
 * binary assets not included in source control. See android_app/README.md.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        // TODO: wire AurionApiClient → ChatFragment once backend URL is known
    }
}
