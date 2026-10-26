package com.example.imageopt.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
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
        VH(ItemProductBinding.inflate(LayoutInflater.from(parent.context), parent, false))
    override fun onBindViewHolder(holder: VH, position: Int) = holder.bind(items[position])
    override fun onViewRecycled(holder: VH) { holder.cancel(); super.onViewRecycled(holder) }

    inner class VH(val binding: ItemProductBinding) : RecyclerView.ViewHolder(binding.root) {
        private var token = 0L
        private var layoutListener: View.OnLayoutChangeListener? = null
        fun cancel() {
            token++
            layoutListener?.let { binding.thumb.removeOnLayoutChangeListener(it) }
            layoutListener = null
            binding.thumb.dispose()
        }
        fun bind(p: Product) {
            binding.root.clipToOutline = true
            cancel()
            val expected = token
            val thumb = binding.thumb
            thumb.setImageResource(R.drawable.bg_placeholder)
            val params = thumb.layoutParams as androidx.constraintlayout.widget.ConstraintLayout.LayoutParams
            params.dimensionRatio = "H,${p.imageWidth}:${p.imageHeight}"
            thumb.layoutParams = params
            binding.name.text = p.name
            binding.price.text = p.price
            binding.root.setOnClickListener { onClick(p) }
            // Chờ layout mới để không dùng kích thước của ảnh trước.
            val listener = object : View.OnLayoutChangeListener {
                override fun onLayoutChange(v: View, l: Int, t: Int, r: Int, b: Int,
                                            oldL: Int, oldT: Int, oldR: Int, oldB: Int) {
                    thumb.removeOnLayoutChangeListener(this)
                    layoutListener = null
                    if (expected != token || thumb.width <= 0 || thumb.height <= 0) return
                    ImageRequests.loadList(thumb, p, config, loader) { success ->
                        thumb.doOnPreDraw {
                            if (expected == token && thumb.isAttachedToWindow) onImageReady(p.id, success)
                        }
                    }
                }
            }
            layoutListener = listener
            thumb.addOnLayoutChangeListener(listener)
            thumb.requestLayout()
        }
    }
}
