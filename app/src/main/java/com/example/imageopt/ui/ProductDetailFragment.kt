package com.example.imageopt.ui

import android.os.Bundle
import android.view.View
import androidx.core.view.doOnLayout
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.navigation.fragment.findNavController
import androidx.navigation.fragment.navArgs
import coil.dispose
import com.example.imageopt.R
import com.example.imageopt.databinding.FragmentProductDetailBinding
import com.example.imageopt.image.AppImageLoaders
import com.example.imageopt.image.ImageRequests

class ProductDetailFragment : Fragment(R.layout.fragment_product_detail) {
    private val args: ProductDetailFragmentArgs by navArgs()
    private val vm: ProductViewModel by activityViewModels()
    private var binding: FragmentProductDetailBinding? = null
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val b = FragmentProductDetailBinding.bind(view)
        binding = b
        (b.image.parent as? View)?.clipToOutline = true
        val product = vm.product(args.productId)
        b.image.ratio = product.imageWidth.toFloat() / product.imageHeight
        b.name.text = product.name
        b.price.text = product.price
        fun load() {
            if (binding !== b) return
            ImageRequests.loadDetail(b.image, product, vm.currentConfig(),
                AppImageLoaders.get(requireContext(), vm.currentConfig()))
        }
        b.image.doOnLayout { load() }
        b.btnRetry.setOnClickListener { load() }
        b.btnBack.setOnClickListener { findNavController().navigateUp() }
    }
    override fun onDestroyView() {
        binding?.image?.dispose()
        binding = null
        super.onDestroyView()
    }
}
