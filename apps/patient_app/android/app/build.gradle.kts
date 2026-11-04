import java.util.Properties

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val nativeAuth = Properties().apply {
    val settings = rootProject.file("native-auth.properties")
    if (settings.exists()) settings.inputStream().use { load(it) }
}
fun nativeAuthValue(name: String): String =
    (System.getenv("CARELINK_$name") ?: nativeAuth.getProperty(name, ""))
        .trim().removeSurrounding("\"").removeSurrounding("'")

val googleServerClientId = nativeAuthValue("GOOGLE_SERVER_CLIENT_ID")
val facebookAppId = nativeAuthValue("FACEBOOK_APP_ID")
val facebookClientToken = nativeAuthValue("FACEBOOK_CLIENT_TOKEN")
val facebookConfigured = facebookAppId.matches(Regex("[0-9]+")) &&
    facebookClientToken.isNotEmpty()

android {
    namespace = "com.carelinkteam.patient"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    buildFeatures {
        resValues = true
    }

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // Stable patient-app identity. Keep this ID for future Play Store updates.
        applicationId = "com.carelinkteam.patient"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        resValue("string", "carelink_google_server_client_id", googleServerClientId)
        resValue("string", "facebook_app_id", facebookAppId.ifEmpty { "0" })
        resValue("string", "facebook_client_token", facebookClientToken.ifEmpty { "not-configured" })
        resValue("string", "fb_login_protocol_scheme", "fb${facebookAppId.ifEmpty { "0" }}")
        resValue("bool", "carelink_facebook_configured", facebookConfigured.toString())
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
