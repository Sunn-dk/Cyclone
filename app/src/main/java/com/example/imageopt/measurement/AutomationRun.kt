package com.example.imageopt.measurement

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.os.Handler
import android.os.Looper
import android.view.PixelCopy
import com.example.imageopt.BuildConfig
import com.example.imageopt.data.ImageSource
import com.example.imageopt.image.ExperimentConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import kotlin.coroutines.resume

data class AutomationRun(
    val label: String, val config: ExperimentConfig, val count: Int, val source: ImageSource,
    val mode: String, val cache: String, val position: Int, val maxMs: Long, val minMs: Long, val screenshot: Boolean
) {
    companion object {
        fun from(intent: Intent): AutomationRun? {
            if (!intent.getBooleanExtra("automation", false)) return null
            require(BuildConfig.BUILD_TYPE != "release") { "Automation is disabled in release." }
            val label = intent.getStringExtra("run_label") ?: "run_${System.currentTimeMillis()}"
            require(label.matches(Regex("[A-Za-z0-9_-]{1,100}"))) { "Invalid run label." }
            val count = intent.getIntExtra("count", 100)
            require(count in listOf(100, 500, 1000))
            val mode = intent.getStringExtra("mode") ?: "load"
            require(mode in listOf("load", "scroll"))
            val cache = intent.getStringExtra("cache") ?: "keep"
            require(cache in listOf("cold", "memory", "keep"))
            return AutomationRun(label,
                ExperimentConfig.valueOf(intent.getStringExtra("config") ?: "D"), count,
                ImageSource.validated(intent.getStringExtra("source") ?: "http://127.0.0.1:8000",
                    intent.getStringExtra("format") ?: "JPEG", intent.getIntExtra("url_version", 1),
                    intent.getBooleanExtra("image_error", false), intent.getIntExtra("delay_ms", 0)),
                mode, cache, intent.getIntExtra("position", 0).coerceIn(0, count - 1),
                intent.getLongExtra("max_ms", 45000).coerceIn(2000, 90000),
                intent.getLongExtra("min_ms", 2000).coerceIn(500, 10000), intent.getBooleanExtra("capture", false))
        }
    }

    suspend fun finish(activity: Activity, reason: String) {
        MeasurementSession.stop(reason)
        val dir = File(activity.getExternalFilesDir(null) ?: activity.filesDir, "automation")
        val shot = if (screenshot) capture(activity) else null
        withContext(Dispatchers.IO) {
            check(dir.exists() || dir.mkdirs())
            val zip = MeasurementSession.exportBundle(activity)
            val destination = File(dir, "${label}.zip")
            zip.copyTo(destination, overwrite = true)
            if (shot != null) {
                File(dir, "${label}.png").outputStream().use { shot.compress(Bitmap.CompressFormat.PNG, 100, it) }
                shot.recycle()
            }
            File(dir, "${label}.done.json").writeText(JSONObject().apply {
                put("label", label); put("reason", reason); put("zip", destination.name)
                put("screenshot", if (shot != null) "${label}.png" else JSONObject.NULL)
                put("config", config.name); put("count", count); put("mode", mode)
                put("cachePreparation", cache); put("source", source.description())
            }.toString(2))
        }
    }

    private suspend fun capture(activity: Activity): Bitmap? {
        val view = activity.window.decorView
        if (view.width <= 0 || view.height <= 0) return null
        val bitmap = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
        return try {
            val ok = suspendCancellableCoroutine<Boolean> { continuation ->
                PixelCopy.request(activity.window, bitmap, { result ->
                    if (continuation.isActive) continuation.resume(result == PixelCopy.SUCCESS)
                }, Handler(Looper.getMainLooper()))
            }
            if (ok) bitmap else { bitmap.recycle(); null }
        } catch (_: Exception) { bitmap.recycle(); null }
    }
}
