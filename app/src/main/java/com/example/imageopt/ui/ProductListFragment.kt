package com.example.imageopt.ui

import android.os.Bundle
import android.os.Parcelable
import android.os.SystemClock
import android.view.View
import android.view.WindowManager
import android.view.animation.LinearInterpolator
import androidx.core.view.doOnPreDraw
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import androidx.recyclerview.widget.RecyclerView
import androidx.recyclerview.widget.StaggeredGridLayoutManager
import com.example.imageopt.R
import com.example.imageopt.data.AppConfig
import com.example.imageopt.databinding.FragmentProductListBinding
import com.example.imageopt.image.AppImageLoaders
import com.example.imageopt.measurement.AutomationRun
import com.example.imageopt.measurement.MeasurementSession
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.File

class ProductListFragment : Fragment(R.layout.fragment_product_list) {
    private val vm: ProductViewModel by activityViewModels()
    private var _binding: FragmentProductListBinding? = null
    private var savedScroll: Parcelable? = null
    private var savedRevision = -1L
    private var shown: GalleryState? = null
    private var autoScrolling = false
    private var scrollGeneration = 0L
    private var scrollTask: Runnable? = null
    private var automation: AutomationRun? = null
    private var automationJob: Job? = null
    private var exporting = false

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val b = FragmentProductListBinding.bind(view)
        _binding = b
        b.recycler.layoutManager = StaggeredGridLayoutManager(2, RecyclerView.VERTICAL)
        b.recycler.itemAnimator = null
        b.recycler.setHasFixedSize(true)
        b.recycler.addOnScrollListener(object : RecyclerView.OnScrollListener() {
            override fun onScrollStateChanged(rv: RecyclerView, newState: Int) {
                if (newState == RecyclerView.SCROLL_STATE_IDLE && autoScrolling) finishScroll("auto_scroll_end")
            }
        })
        vm.state.observe(viewLifecycleOwner) { state ->
            if (_binding !== b || vm.automationPreparing || !vm.isCurrent(state)) return@observe
            val spec = vm.pendingAutomation
            vm.pendingAutomation = null
            val measuring = vm.pendingMeasurement || spec != null
            vm.pendingMeasurement = false
            automation = spec
            exporting = false
            if (spec?.mode == "scroll") startScroll(state, spec)
            else {
                display(state, measuring, spec)
                if (spec != null) waitForViewport(spec)
            }
        }
        b.btnReload.setOnClickListener { shown?.let { display(it, true) } }
        b.btnAutoScroll.setOnClickListener { shown?.let { startScroll(it) } }
        b.btnExperiment.setOnClickListener {
            finishScroll("open_results")
            MeasurementSession.stop("open_results")
            findNavController().navigate(ProductListFragmentDirections.actionListToExperiment())
        }
    }

    private fun display(state: GalleryState, startMeasurement: Boolean, spec: AutomationRun? = null) {
        if (!vm.isCurrent(state)) return
        val b = _binding ?: return
        autoScrolling = false
        scrollGeneration++
        scrollTask?.let { b.recycler.removeCallbacks(it) }
        b.recycler.stopScroll()
        b.recycler.adapter = null
        if (startMeasurement) {
            MeasurementSession.start(requireActivity(), state.config.name, state.products.size, state.source.description())
            MeasurementSession.setMetadata(mapOf(
                "label" to (spec?.label ?: "manual"),
                "mode" to (spec?.mode ?: "manual"),
                "cachePreparation" to (spec?.cache ?: "user_managed"),
                "initialPosition" to (spec?.position ?: 0).toString(),
                "uniqueRawUrls" to state.products.map { it.rawUrl }.toSet().size.toString(),
                "uniqueThumbUrls" to state.products.map { it.thumbUrl }.toSet().size.toString()
            ))
        }
        val runId = MeasurementSession.currentRunId
        val restore = !startMeasurement && state.revision == savedRevision
        shown = state
        b.tvSourceStatus.text = "${state.config.name} · ${state.products.size} ảnh · ${state.source.format} · v${state.source.version}"
        b.tvRunStatus.text = if (MeasurementSession.isActive) "Đang đo · ${spec?.label ?: "mở Thử nghiệm để dừng"}"
            else "Sẵn sàng · Tải lại để bắt đầu một phiên đo"
        b.btnAutoScroll.isEnabled = spec == null
        b.btnReload.isEnabled = spec == null
        val loader = AppImageLoaders.get(requireContext(), state.config)
        b.recycler.adapter = ProductAdapter(state.products, state.config, loader,
            onImageReady = { id, success -> if (runId != null) MeasurementSession.onImageDrawn(runId, id, success) },
            onClick = { product ->
                if (!autoScrolling && automation == null) findNavController().navigate(
                    ProductListFragmentDirections.actionListToDetail(product.id))
            })
        if (restore) b.recycler.layoutManager?.onRestoreInstanceState(savedScroll)
        else b.recycler.scrollToPosition(spec?.position ?: 0)
        b.recycler.doOnPreDraw { rv ->
            if (_binding !== b || runId == null) return@doOnPreDraw
            val ids = (0 until b.recycler.childCount).mapNotNull { index ->
                val child = b.recycler.getChildAt(index)
                val position = b.recycler.getChildAdapterPosition(child)
                if (child.bottom > rv.paddingTop && child.top < rv.height - rv.paddingBottom)
                    state.products.getOrNull(position)?.id else null
            }.toSet()
            MeasurementSession.setInitialViewport(runId, ids)
        }
    }

    private fun waitForViewport(spec: AutomationRun) {
        automationJob?.cancel()
        val runId = MeasurementSession.currentRunId ?: return
        automationJob = viewLifecycleOwner.lifecycleScope.launch {
            val began = SystemClock.elapsedRealtime()
            delay(spec.minMs)
            while (MeasurementSession.currentRunId == runId &&
                !MeasurementSession.viewportComplete(runId) &&
                SystemClock.elapsedRealtime() - began < spec.maxMs) delay(100)
            if (MeasurementSession.currentRunId == runId) finishAutomation(
                if (MeasurementSession.viewportComplete(runId)) "viewport_terminal" else "max_wait")
        }
    }

    private fun startScroll(state: GalleryState, spec: AutomationRun? = null) {
        if (autoScrolling || !vm.isCurrent(state)) return
        val b = _binding ?: return
        display(state, true, spec)
        autoScrolling = true
        b.btnAutoScroll.isEnabled = false
        b.btnReload.isEnabled = false
        b.tvRunStatus.text = "Đang đo và cuộn tự động trong 8 giây"
        val expected = ++scrollGeneration
        val task = Runnable {
            if (_binding === b && autoScrolling && expected == scrollGeneration) {
                val manager = b.recycler.layoutManager as StaggeredGridLayoutManager
                MeasurementSession.setMetadata(mapOf("scrollStartMaxPosition" to manager.findLastVisibleItemPositions(null).max().toString(), "scrollDistancePx" to (b.recycler.height * AppConfig.AUTO_SCROLL_VIEWPORTS).toString(), "recyclerHeightPx" to b.recycler.height.toString()))
                b.recycler.smoothScrollBy(0, b.recycler.height * AppConfig.AUTO_SCROLL_VIEWPORTS,
                    LinearInterpolator(), AppConfig.AUTO_SCROLL_MS)
                b.recycler.postDelayed({
                    if (_binding === b && autoScrolling && expected == scrollGeneration) finishScroll("auto_scroll_timeout")
                }, AppConfig.AUTO_SCROLL_MS.toLong() + 1500)
            }
        }
        scrollTask = task
        b.recycler.doOnPreDraw {
            if (_binding === b && autoScrolling && expected == scrollGeneration) b.recycler.postOnAnimation(task)
        }
    }

    private fun finishScroll(reason: String) {
        if (!autoScrolling) return
        autoScrolling = false
        scrollGeneration++
        _binding?.recycler?.let { rv ->
            val manager = rv.layoutManager as StaggeredGridLayoutManager
            MeasurementSession.setMetadata(mapOf("scrollEndMaxPosition" to manager.findLastVisibleItemPositions(null).max().toString()))
        }
        MeasurementSession.stop(reason)
        _binding?.let {
            it.recycler.stopScroll()
            it.btnAutoScroll.isEnabled = true
            it.btnReload.isEnabled = true
            it.tvRunStatus.text = "Đã dừng đo · mở Thử nghiệm để xem kết quả"
        }
        if (reason != "view_destroyed" && automation != null) finishAutomation(reason)
    }

    private fun finishAutomation(reason: String) {
        val spec = automation ?: return
        if (exporting) return
        exporting = true
        MeasurementSession.stop(reason)
        viewLifecycleOwner.lifecycleScope.launch {
            try {
                spec.finish(requireActivity(), reason)
                _binding?.tvRunStatus?.text = "Đã lưu ${spec.label}"
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) {
                val dir = File(requireContext().getExternalFilesDir(null), "automation").apply { mkdirs() }
                File(dir, "${spec.label}.error.json").writeText(JSONObject().put("error", e.toString()).toString())
            } finally {
                automation = null
                exporting = false
                activity?.window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                _binding?.btnReload?.isEnabled = true
                _binding?.btnAutoScroll?.isEnabled = true
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (!MeasurementSession.isActive) _binding?.tvRunStatus?.text = "Sẵn sàng · Tải lại để bắt đầu phiên đo mới"
    }

    override fun onDestroyView() {
        val b = _binding
        savedScroll = b?.recycler?.layoutManager?.onSaveInstanceState()
        savedRevision = shown?.revision ?: -1
        automationJob?.cancel()
        finishScroll("view_destroyed")
        scrollTask?.let { b?.recycler?.removeCallbacks(it) }
        b?.recycler?.adapter = null
        _binding = null
        super.onDestroyView()
    }
}
