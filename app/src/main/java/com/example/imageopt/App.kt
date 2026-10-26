package com.example.imageopt

import android.app.Application
import android.os.StrictMode

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            // Báo ra Logcat nếu lỡ đọc đĩa/mạng trên Main Thread
            StrictMode.setThreadPolicy(
                StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build()
            )
        }
    }
}
