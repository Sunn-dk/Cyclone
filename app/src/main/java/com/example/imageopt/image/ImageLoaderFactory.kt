package com.example.imageopt.image

import android.content.Context
import coil.ImageLoader
import coil.annotation.ExperimentalCoilApi
import coil.disk.DiskCache
import coil.memory.MemoryCache
import com.example.imageopt.measurement.ImageLoadRecorder
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

object AppImageLoaders {
    private val disks = HashMap<ExperimentConfig, DiskCache>()
    private val client = OkHttpClient.Builder().connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS).callTimeout(30, TimeUnit.SECONDS).build()
    private var active: Pair<ExperimentConfig, ImageLoader>? = null

    @Synchronized
    fun get(context: Context, config: ExperimentConfig): ImageLoader {
        active?.takeIf { it.first == config }?.let { return it.second }
        active?.second?.shutdown()
        return build(context.applicationContext, config).also { active = config to it }
    }

    @OptIn(ExperimentalCoilApi::class)
    fun clearCache(context: Context, config: ExperimentConfig) {
        val loader = get(context, config)
        loader.memoryCache?.clear()
        loader.diskCache?.clear()
    }

    @Synchronized
    fun clearAllMemory() { active?.second?.memoryCache?.clear() }

    fun prepare(context: Context, config: ExperimentConfig, cache: String) {
        if (cache == "cold") {
            val old = synchronized(this) { active?.second.also { active = null } }
            old?.shutdown()
            clearCache(context, config)
        } else if (cache == "memory") clearAllMemory()
    }

    private fun build(context: Context, config: ExperimentConfig): ImageLoader {
        val builder = ImageLoader.Builder(context).okHttpClient(client)
            .crossfade(false).eventListenerFactory(ImageLoadRecorder)
        return if (config.useCache) builder
            .memoryCache { MemoryCache.Builder(context).maxSizePercent(0.25).build() }
            .diskCache { disks.getOrPut(config) { DiskCache.Builder()
                .directory(context.cacheDir.resolve("image_cache_${config.name}"))
                .maxSizeBytes(150L * 1024 * 1024).build() } }
            .respectCacheHeaders(false).build()
        else builder.memoryCache(null).diskCache(null).build()
    }
}
