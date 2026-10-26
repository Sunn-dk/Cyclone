package com.example.imageopt.image

import android.widget.ImageView
import coil.ImageLoader
import coil.load
import coil.request.CachePolicy
import coil.size.Size
import com.example.imageopt.R
import com.example.imageopt.data.Product

object ImageRequests {
    fun loadList(view: ImageView, p: Product, config: ExperimentConfig, loader: ImageLoader,
                 onResult: (Boolean) -> Unit = {}) {
        val url = if (config.thumbInList) p.thumbUrl else p.rawUrl
        view.load(url, loader) {
            if (config.originalSize) size(Size.ORIGINAL)
            else size(view.width.coerceAtLeast(1), view.height.coerceAtLeast(1))
            if (!config.useCache) {
                memoryCachePolicy(CachePolicy.DISABLED)
                diskCachePolicy(CachePolicy.DISABLED)
            }
            placeholder(R.drawable.bg_placeholder)
            crossfade(if (config.polish) 200 else 0)
            if (config.polish) memoryCacheKey(url)
            error(R.drawable.ic_error)
            listener(onSuccess = { _, _ -> onResult(true) }, onError = { _, _ -> onResult(false) })
        }
    }

    fun loadDetail(view: ImageView, p: Product, config: ExperimentConfig, loader: ImageLoader) {
        val url = if (config.polish) p.detailUrl else p.rawUrl
        view.load(url, loader) {
            if (config.originalSize) size(Size.ORIGINAL)
            if (!config.useCache) {
                memoryCachePolicy(CachePolicy.DISABLED)
                diskCachePolicy(CachePolicy.DISABLED)
            }
            placeholder(R.drawable.bg_placeholder)
            if (config.polish) placeholderMemoryCacheKey(p.thumbUrl)
            crossfade(if (config.polish) 200 else 0)
            error(R.drawable.ic_error)
        }
    }
}
