import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val signingPropertiesFile = rootProject.file("keystore.properties")
val signingProperties = Properties().apply {
    if (signingPropertiesFile.exists()) {
        signingPropertiesFile.inputStream().use(::load)
    }
}

android {
    namespace = "ir.neginpakhsh.seller"
    compileSdk = 35

    defaultConfig {
        applicationId = "ir.neginpakhsh.seller"
        minSdk = 26
        targetSdk = 35
        versionCode = 14
        versionName = "1.3.9"
        buildConfigField("String", "NEGIN_BASE_URL", "\"${providers.gradleProperty("NEGIN_BASE_URL").getOrElse("https://ai.neginpakhsh.com").removeSuffix("/")}\"")
        buildConfigField("String", "ASSISTANT_URL", "\"https://ai.neginpakhsh.com/assistant\"")
        buildConfigField("String", "UPDATE_URL", "\"https://ai.neginpakhsh.com/app/android/version.json\"")
        manifestPlaceholders["usesCleartextTraffic"] = "false"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
    }

    signingConfigs {
        if (signingPropertiesFile.exists()) {
            create("release") {
                storeFile = rootProject.file(signingProperties.getProperty("storeFile"))
                storePassword = signingProperties.getProperty("storePassword")
                keyAlias = signingProperties.getProperty("keyAlias")
                keyPassword = signingProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        debug {
            // Android Emulator reaches the host loopback through 10.0.2.2.
            buildConfigField(
                "String",
                "ASSISTANT_URL",
                "\"${providers.gradleProperty("ASSISTANT_URL").getOrElse("http://10.0.2.2:8000/assistant")}\""
            )
            manifestPlaceholders["usesCleartextTraffic"] = "true"
        }
        release {
            buildConfigField(
                "String",
                "ASSISTANT_URL",
                "\"${providers.gradleProperty("ASSISTANT_URL").getOrElse("https://ai.neginpakhsh.com/assistant")}\""
            )
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            signingConfig = signingConfigs.findByName("release")
        }
    }

    buildFeatures { compose = true; buildConfig = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.14" }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    // Neshan's map layouts reference these attributes but its published AAR
    // does not expose all of them transitively.
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("com.google.android.material:material:1.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    // The Neshan licence is package-name and signing-SHA1 bound; see README.
    implementation("neshan-android-sdk:mobile-sdk:1.0.1")
    implementation("neshan-android-sdk:services-sdk:1.0.0")
    implementation("neshan-android-sdk:common-sdk:0.0.2")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
