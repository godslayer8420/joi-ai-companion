# Aurion Mobile — ProGuard rules
# Keep Retrofit + OkHttp + Gson model classes
-keepattributes Signature
-keepattributes *Annotation*
-keep class com.aurion.mobile.** { *; }
-keep class retrofit2.** { *; }
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}
-keep class okhttp3.** { *; }
-keep class com.google.gson.** { *; }

# WebRTC
-keep class org.webrtc.** { *; }
-keepclassmembers class org.webrtc.** { *; }

# Socket.IO
-keep class io.socket.** { *; }
-keep class io.engineio.** { *; }
-dontwarn io.socket.**
-dontwarn io.engineio.**
