package com.example.imageopt.image

import android.content.Context
import com.example.imageopt.data.ImageSource

enum class ExperimentConfig(
    val label: String,
    val useCache: Boolean,
    val originalSize: Boolean,
    val thumbInList: Boolean,
    val polish: Boolean
) {
    A("A · Ảnh gốc, không cache, giải mã gốc", false, true, false, false),
    B("B · Ảnh gốc + cache RAM/đĩa", true, true, false, false),
    C("C · B + giải mã theo kích thước ô", true, false, false, false),
    D("D · C + thumbnail cho danh sách", true, false, true, false),
    E("E · D + crossfade, ảnh xem trước", true, false, true, true)
}

class ExperimentPrefs(context: Context) {
    private val sp = context.applicationContext.getSharedPreferences("experiment", Context.MODE_PRIVATE)
    var config: ExperimentConfig
        get() = ExperimentConfig.values().firstOrNull { it.name == sp.getString("config", "D") } ?: ExperimentConfig.D
        set(value) { sp.edit().putString("config", value.name).apply() }
    var count: Int
        get() = sp.getInt("count", 100).takeIf { it in listOf(100, 500, 1000) } ?: 100
        set(value) { sp.edit().putInt("count", value.takeIf { it in listOf(100, 500, 1000) } ?: 100).apply() }
    var source: ImageSource
        get() = runCatching { ImageSource.validated(
            sp.getString("baseUrl", null) ?: ImageSource().baseUrl,
            sp.getString("format", "JPEG") ?: "JPEG",
            sp.getInt("version", 1), sp.getBoolean("error", false), sp.getInt("delay", 0))
        }.getOrDefault(ImageSource())
        set(value) { sp.edit().putString("baseUrl", value.baseUrl).putString("format", value.format)
            .putInt("version", value.version).putBoolean("error", value.errorEnabled)
            .putInt("delay", value.delayMs).apply() }
}
