package com.example.imageopt.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.view.doOnLayout
import androidx.core.view.doOnPreDraw
import androidx.recyclerview.widget.RecyclerView
import coil.ImageLoader
import coil.dispose
import com.example.imageopt.R
import com.example.imageopt.data.Product
import com.example.imageopt.databinding.ItemProductBinding
import com.example.imageopt.image.ExperimentConfig
import com.example.imageopt.image.ImageRequests

class ProductAdapter(
    private val items: List<Product>,
    private val config: ExperimentConfig,
    private val loader: ImageLoader,
    private val onImageReady: (Int, Boolean) -> Unit,
    private val onClick: (Product) -> Unit
) : RecyclerView.Adapter<ProductAdapter.VH>() {
    init { setHasStableIds(true) }
    override fun getItemId(position: Int) = items[position].id.toLong()
    override fun getItemCount() = items.size
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemProductBinding.inflate(LayoutInflater.from(parent.context), parent, false)).also {
            it.binding.root.clipToOutline = true
        }
    override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(items[position])
    override fun onViewRecycled(holder: VH) { holder.cancel(); super.onViewRecycled(holder) }

    inner class VH(val binding: ItemProductBinding) : RecyclerView.ViewHolder(binding.root) {
        private var token = 0L
        fun cancel() {
            token++
            binding.thumb.dispose()
        }
        fun bind(p: Product) {
            cancel()
            val expected = token
            val thumb = binding.thumb
            thumb.setImageResource(R.drawable.bg_placeholder)
            val params = thumb.layoutParams as androidx.constraintlayout.widget.ConstraintLayout.LayoutParams
            val ratio = "H,${p.imageWidth}:${p.imageHeight}"
            if (params.dimensionRatio != ratio) {
                params.dimensionRatio = ratio
                thumb.layoutParams = params
            }
            binding.name.text = p.name
            binding.price.text = p.price
            binding.root.contentDescription = binding.root.context.getString(R.string.ui_open_product, p.name, p.price)
            binding.root.setOnClickListener { onClick(p) }
            // Chờ đúng kích thước ô, không ép layout lại nếu tỷ lệ không đổi.
            thumb.doOnLayout {
                if (expected != token || thumb.width <= 0 || thumb.height <= 0) return@doOnLayout
                ImageRequests.loadList(thumb, p, config, loader) { success ->
                    thumb.doOnPreDraw {
                        if (expected == token && thumb.isAttachedToWindow) onImageReady(p.id, success)
                    }
                }
            }
        }
    }
}
