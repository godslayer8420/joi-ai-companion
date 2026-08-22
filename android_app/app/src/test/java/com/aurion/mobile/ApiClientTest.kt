package com.aurion.mobile

import org.junit.Assert.assertEquals
import org.junit.Test

/** Unit tests for data model serialisation — no network calls. */
class ApiClientTest {

    @Test
    fun chatRequest_defaultUserName() {
        val req = ChatRequest(message = "hello")
        assertEquals("user", req.user_name)
    }

    @Test
    fun chatResponse_defaultEmotion() {
        val resp = ChatResponse(reply = "Hi there")
        assertEquals("NEUTRAL", resp.emotion)
    }

    @Test
    fun chatRequest_customUserName() {
        val req = ChatRequest(message = "hi", user_name = "billy")
        assertEquals("billy", req.user_name)
    }
}
