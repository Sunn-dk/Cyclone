package com.example.imageopt.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.RadioButton
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.core.content.FileProvider
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.example.imageopt.R
import com.example.imageopt.data.ImageSource
import com.example.imageopt.databinding.FragmentExperimentBinding
import com.example.imageopt.image.ExperimentConfig
import com.example.imageopt.measurement.ImageLoadRecorder
import com.example.imageopt.measurement.MeasurementSession
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ExperimentFragment : Fragment(R.layout.fragment_experiment) {
    private val vm: ProductViewModel by activityViewModels()
    private var _binding: FragmentExperimentBinding? = null
    private val configIds = mapOf(R.id.rbA to ExperimentConfig.A, R.id.rbB to ExperimentConfig.B,
        R.id.rbC to ExperimentConfig.C, R.id.rbD to ExperimentConfig.D, R.id.rbE to ExperimentConfig.E)
    private val countIds = mapOf(R.id.rb100 to 100, R.id.rb500 to 500, R.id.rb1000 to 1000)
    private val formats = mapOf(R.id.rbJpeg to "JPEG", R.id.rbPng to "PNG", R.id.rbWebp to "WEBP")
    private var working = false

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val b = FragmentExperimentBinding.bind(view)
        _binding = b
        configIds.forEach { (id, cfg) -> view.findViewById<RadioButton>(id).text = cfg.label }
        b.rgConfig.check(configIds.entries.first { it.value == vm.currentConfig() }.key)
        b.rgCount.check(countIds.entries.first { it.value == vm.count.value }.key)
        b.etBaseUrl.setText(vm.source.baseUrl)
        b.etDelayMs.setText(vm.source.delayMs.toString())
        b.rgFormat.check(formats.entries.first { it.value == vm.source.format }.key)
        b.switchImageError.isChecked = vm.source.errorEnabled
        updateVersion()
        val backGuard = object : OnBackPressedCallback(false) { override fun handleOnBackPressed() {} }
        requireActivity().onBackPressedDispatcher.addCallback(viewLifecycleOwner, backGuard)
        fun enable(view: View, enabled: Boolean) {
            view.isEnabled = enabled
            if (view is ViewGroup) for (i in 0 until view.childCount) enable(view.getChildAt(i), enabled)
        }
        fun busy(value: Boolean) {
            working = value
            backGuard.isEnabled = value
            if (_binding === b) enable(b.root, !value)
        }
        vm.busy.observe(viewLifecycleOwner) { busy(it) }
        b.rgConfig.setOnCheckedChangeListener { _, id -> configIds[id]?.let { vm.setConfig(it); showStats() } }
        b.rgCount.setOnCheckedChangeListener { _, id -> countIds[id]?.let { vm.setCount(it); showStats() } }
        b.btnApplySource.setOnClickListener {
            try {
                val delay = b.etDelayMs.text.toString().toIntOrNull()
                    ?: throw IllegalArgumentException("Nhập độ trễ bằng số, ví dụ 0 hoặc 2000.")
                vm.setSource(ImageSource.validated(b.etBaseUrl.text.toString(),
                    formats[b.rgFormat.checkedRadioButtonId] ?: "JPEG", vm.source.version,
                    b.switchImageError.isChecked, delay))
                toast("Đã áp dụng nguồn ảnh. Quay lại để tải.")
                b.etBaseUrl.error = null
                showStats()
            } catch (e: IllegalArgumentException) { b.etBaseUrl.error = e.message }
        }
        b.switchImageError.setOnCheckedChangeListener { _, checked ->
            vm.setSource(vm.source.copy(errorEnabled = checked))
            showStats()
        }
        b.btnVersion.setOnClickListener {
            vm.setSource(vm.source.copy(version = if (vm.source.version == 999999) 1 else vm.source.version + 1))
            updateVersion()
            toast("Đã đổi khóa URL; muốn đổi nội dung local cần tạo lại ảnh trên server.")
        }
        fun clear(memoryOnly: Boolean) {
            if (working) return
            viewLifecycleOwner.lifecycleScope.launch {
                try {
                    vm.clearCache(memoryOnly)
                    if (_binding === b) { toast("Đã xóa cache. Bấm Bắt đầu đo để tải lại."); showStats() }
                } catch (e: CancellationException) { throw e }
                catch (e: Exception) { if (_binding === b) toast("Không xóa được cache: ${e.message}") }
            }
        }
        b.btnClear.setOnClickListener { clear(false) }
        b.btnClearMemory.setOnClickListener { clear(true) }
        b.btnMeasureStart.setOnClickListener {
            vm.pendingMeasurement = true
            findNavController().navigateUp()
        }
        b.btnMeasureStop.setOnClickListener { MeasurementSession.stop("manual"); showStats() }
        b.btnReset.setOnClickListener { ImageLoadRecorder.reset(vm.currentConfig().name); showStats() }
        b.btnRefresh.setOnClickListener { showStats() }
        fun export(share: Boolean) {
            if (working) return
            if (MeasurementSession.isActive) { toast("Dừng đo trước khi xuất."); return }
            val context = requireContext().applicationContext
            viewLifecycleOwner.lifecycleScope.launch {
                busy(true)
                try {
                    val file = withContext(Dispatchers.IO) {
                        if (share) MeasurementSession.exportBundle(context) else ImageLoadRecorder.exportCsv(context)
                    }
                    if (_binding !== b) return@launch
                    b.tvStats.text = "Đã lưu:\n${file.absolutePath}\n\n" + MeasurementSession.report()
                    if (share) {
                        val uri = FileProvider.getUriForFile(context, context.packageName + ".files", file)
                        val send = Intent(Intent.ACTION_SEND).apply {
                            type = "application/zip"
                            putExtra(Intent.EXTRA_STREAM, uri)
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            clipData = android.content.ClipData.newRawUri("Cyclone", uri)
                        }
                        startActivity(Intent.createChooser(send, "Lưu hoặc chia sẻ kết quả"))
                    }
                } catch (e: CancellationException) { throw e }
                catch (e: Exception) { if (_binding === b) toast("Không xuất được: ${e.message}") }
                finally { busy(false) }
            }
        }
        b.btnExport.setOnClickListener { export(false) }
        b.btnShare.setOnClickListener { export(true) }
        b.btnBack.setOnClickListener { if (!working) findNavController().navigateUp() }
        showStats()
    }
    private fun updateVersion() { _binding?.btnVersion?.text = "Đổi phiên bản URL · hiện tại v${vm.source.version}" }
    private fun showStats() { _binding?.tvStats?.text = MeasurementSession.report() }
    private fun toast(message: String) { Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show() }
    override fun onDestroyView() { _binding = null; super.onDestroyView() }
}
