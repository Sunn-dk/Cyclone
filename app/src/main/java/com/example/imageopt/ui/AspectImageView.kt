package com.example.imageopt.ui

import android.content.Context
import android.util.AttributeSet
import androidx.appcompat.widget.AppCompatImageView
import kotlin.math.ceil

class AspectImageView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null
) : AppCompatImageView(context, attrs) {
    var ratio: Float = 1f
        set(value) {
            val safe = if (value.isFinite() && value > 0f) value.coerceIn(0.05f, 20f) else 1f
            if (field == safe) return
            field = safe
            requestLayout()
        }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        super.onMeasure(widthMeasureSpec, heightMeasureSpec)
        val contentWidth = (measuredWidth - paddingLeft - paddingRight).coerceAtLeast(0)
        val desiredHeight = ceil(contentWidth / ratio.toDouble()).toInt() + paddingTop + paddingBottom
        // Respect parent constraints while keeping the drawable in fitCenter.
        val height = resolveSizeAndState(desiredHeight.coerceAtLeast(suggestedMinimumHeight), heightMeasureSpec, 0)
        setMeasuredDimension(measuredWidthAndState, height)
    }
}
