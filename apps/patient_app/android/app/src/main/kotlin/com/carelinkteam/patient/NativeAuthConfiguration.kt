package com.carelinkteam.patient

import android.content.res.Resources
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/** Only public client configuration and readiness cross this channel. */
object NativeAuthConfiguration {
    fun install(engine: FlutterEngine, resources: Resources) {
        MethodChannel(engine.dartExecutor.binaryMessenger, "carelink/native_auth_config")
            .setMethodCallHandler { call, result ->
                if (call.method == "configuration") {
                    result.success(mapOf(
                        "googleServerClientId" to resources.getString(R.string.carelink_google_server_client_id),
                        "facebookConfigured" to resources.getBoolean(R.bool.carelink_facebook_configured)
                    ))
                } else {
                    result.notImplemented()
                }
            }
    }
}
