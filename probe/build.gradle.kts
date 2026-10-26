plugins { id("com.android.application") }
android {
    namespace = "com.example.cycloneprobe"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.example.cycloneprobe"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
