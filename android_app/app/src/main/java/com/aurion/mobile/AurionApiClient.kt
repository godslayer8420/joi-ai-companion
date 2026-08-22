package com.aurion.mobile

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

/** Retrofit interface to the Aurion Python web_ui.py backend. */
interface AurionApi {
    @POST("/chat")
    suspend fun chat(@Body request: ChatRequest): ChatResponse
}

data class ChatRequest(val message: String, val user_name: String = "user")
data class ChatResponse(val reply: String, val emotion: String = "NEUTRAL")

object AurionApiClient {
    // Override via BuildConfig or an env var in local.properties:
    //   AURION_BASE_URL=http://10.0.2.2:7860/
    private const val BASE_URL = "http://10.0.2.2:7860/"

    private val client = OkHttpClient.Builder()
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    val api: AurionApi = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(AurionApi::class.java)
}
