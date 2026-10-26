package com.example.imageopt.measurement

import android.app.Activity
import android.content.Context
import android.os.Build
import android.os.Debug
import android.os.Handler
import android.os.HandlerThread
import android.os.Looper
import android.util.Log
import android.view.FrameMetrics
import android.view.Window
import com.example.imageopt.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.Locale
import java.util.concurrent.atomic.AtomicLong
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object MeasurementSession {
    const val MAX_DURATION_MS = 120_000L
    const val PSS_INTERVAL_MS = 500L
    private const val MAX_FRAMES = 20_000
    private const val MAX_MEMORY_SAMPLES = 250
    private const val MAX_VIEWPORT_IDS = 500
    private val lock = Any()
    private val sequence = AtomicLong()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var run: Run? = null
    private var resources: Resources? = null

    private data class Frame(val timeMs: Long, val totalNs: Long, val budgetNs: Long, val deadlineNs: Long, val firstDraw: Boolean, val dropped: Int)
    private data class Memory(val timeMs: Long, val pssKb: Int, val javaHeapKb: Long, val nativeHeapKb: Long)
    private data class Draw(val success: Boolean, val timeMs: Long)
    private class Run(val id: Long, val config: String, val count: Int, val source: String) {
        val cpuStartMs = android.os.Process.getElapsedCpuTime()
        var cpuStopMs: Long? = null
        val metadata = LinkedHashMap<String, String>()
        val startNs = System.nanoTime()
        val startedAtEpochMs = System.currentTimeMillis()
        var stopNs: Long? = null
        var stopReason = ""
        val frames = ArrayList<Frame>()
        val memory = ArrayList<Memory>()
        var frameOverflow = 0
        var memoryOverflow = 0
        val warnings = LinkedHashSet<String>()
        var initialIds: Set<Int>? = null
        var viewportCapturedMs: Long? = null
        val imageDraws = HashMap<Int, Draw>()
        var viewportReadyMs: Long? = null
    }
    private data class Resources(
        val runId: Long,
        val window: Window,
        val listener: Window.OnFrameMetricsAvailableListener,
        val frameThread: HandlerThread,
        val scope: CoroutineScope,
        val timeout: Runnable
    )
    private data class Snapshot(
        val id: Long, val config: String, val count: Int, val source: String,
        val startedAtEpochMs: Long, val durationMs: Long, val cpuMs: Long, val metadata: Map<String, String>, val active: Boolean, val stopReason: String,
        val frames: List<Frame>, val memory: List<Memory>, val frameOverflow: Int, val memoryOverflow: Int,
        val warnings: List<String>, val initialIds: Set<Int>?, val viewportCapturedMs: Long?,
        val draws: Map<Int, Draw>, val viewportReadyMs: Long?, val requests: ImageLoadRecorder.Snapshot
    )

    val hasSession: Boolean get() = synchronized(lock) { run != null }
    val isActive: Boolean get() = synchronized(lock) { run?.stopNs == null && run != null }
    val currentRunId: Long? get() = synchronized(lock) { run?.takeIf { it.stopNs == null }?.id }

    @Suppress("DEPRECATION")
    fun start(activity: Activity, config: String, count: Int, source: String): Long {
        check(Looper.myLooper() == Looper.getMainLooper()) { "Start measurements on the main thread." }
        stop("replaced")
        val next = Run(sequence.incrementAndGet(), config, count, source.take(2048))
        val thread = HandlerThread("ImageOptFrames").apply { start() }
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        val display = activity.windowManager.defaultDisplay
        val listener = Window.OnFrameMetricsAvailableListener { _, metrics, dropped ->
            val totalNs = metrics.getMetric(FrameMetrics.TOTAL_DURATION)
            val intendedNs = metrics.getMetric(FrameMetrics.INTENDED_VSYNC_TIMESTAMP)
            if (totalNs < 0 || (intendedNs > 0 && intendedNs < next.startNs)) return@OnFrameMetricsAvailableListener
            val refresh = display.refreshRate.toDouble()
            val budgetNs = if (refresh > 0 && refresh.isFinite()) (1_000_000_000.0 / refresh).toLong() else -1
            val deadlineNs = if (Build.VERSION.SDK_INT >= 31) metrics.getMetric(FrameMetrics.DEADLINE) else -1L
            val frame = Frame(elapsedMs(next), totalNs, budgetNs, deadlineNs,
                metrics.getMetric(FrameMetrics.FIRST_DRAW_FRAME) == 1L, dropped.coerceAtLeast(0))
            synchronized(lock) {
                if (run !== next || next.stopNs != null) return@synchronized
                if (next.frames.size < MAX_FRAMES) next.frames.add(frame) else next.frameOverflow++
            }
        }
        val timeout = Runnable { if (currentRunId == next.id) stop("time_limit_120s") }
        synchronized(lock) {
            run = next
            ImageLoadRecorder.beginRun(next.id, next.startNs, config)
            resources = Resources(next.id, activity.window, listener, thread, scope, timeout)
        }
        try {
            activity.window.addOnFrameMetricsAvailableListener(listener, Handler(thread.looper))
        } catch (e: RuntimeException) {
            warning(next.id, "FrameMetrics unavailable: ${e.javaClass.simpleName}")
        }
        mainHandler.postDelayed(timeout, MAX_DURATION_MS)
        scope.launch {
            while (isActive && currentRunId == next.id) {
                sampleMemory(next)
                delay(PSS_INTERVAL_MS)
            }
        }
        Log.i(TAG, "RUN_START id=${next.id} config=$config count=$count source=$source")
        return next.id
    }

    fun stop(reason: String = "manual") {
        val captured = synchronized(lock) {
            val selected = run ?: return
            if (selected.stopNs != null) return
            selected.cpuStopMs = android.os.Process.getElapsedCpuTime()
            selected.stopNs = System.nanoTime()
            selected.stopReason = reason.take(200)
            ImageLoadRecorder.endRun(selected.id)
            resources.also { resources = null }
        }
        captured?.let { r ->
            mainHandler.removeCallbacks(r.timeout)
            r.scope.cancel()
            val cleanup = Runnable {
                try { r.window.removeOnFrameMetricsAvailableListener(r.listener) } catch (_: RuntimeException) { }
                r.frameThread.quitSafely()
            }
            if (Looper.myLooper() == Looper.getMainLooper()) cleanup.run() else mainHandler.post(cleanup)
        }
        Log.i(TAG, "RUN_STOP reason=$reason ${ImageLoadRecorder.summaryLine()}")
    }

    fun stopForActivity(activity: Activity, reason: String = "activity_stopped") {
        val matches = synchronized(lock) { resources?.window === activity.window }
        if (matches) stop(reason)
    }

    fun reset(config: String) {
        stop("reset")
        synchronized(lock) {
            run = null
            ImageLoadRecorder.clear(config)
        }
    }

    fun setMetadata(values: Map<String, String>) = synchronized(lock) { run?.metadata?.putAll(values) }
    fun viewportComplete(runId: Long): Boolean = synchronized(lock) { run?.let { it.id == runId && it.viewportReadyMs != null } ?: false }

    fun setInitialViewport(runId: Long, ids: Set<Int>) = synchronized(lock) {
        val selected = run?.takeIf { it.id == runId && it.stopNs == null } ?: return@synchronized
        if (selected.initialIds != null || ids.isEmpty()) return@synchronized
        if (ids.size > MAX_VIEWPORT_IDS) {
            selected.warnings.add("Initial viewport exceeds $MAX_VIEWPORT_IDS IDs; milestone unavailable.")
            return@synchronized
        }
        selected.initialIds = ids.toSet()
        selected.viewportCapturedMs = elapsedMs(selected)
        updateViewport(selected)
    }

    // Call at the next pre-draw after a terminal drawable has been set.
    fun onImageDrawn(runId: Long, productId: Int, success: Boolean) = synchronized(lock) {
        val selected = run?.takeIf { it.id == runId && it.stopNs == null } ?: return@synchronized
        if (selected.imageDraws.containsKey(productId)) return@synchronized
        if (selected.imageDraws.size >= MAX_VIEWPORT_IDS) return@synchronized
        selected.imageDraws[productId] = Draw(success, elapsedMs(selected))
        updateViewport(selected)
    }

    private fun updateViewport(selected: Run) {
        val ids = selected.initialIds ?: return
        if (selected.viewportReadyMs != null || !ids.all { selected.imageDraws.containsKey(it) }) return
        selected.viewportReadyMs = maxOf(selected.viewportCapturedMs ?: 0,
            ids.maxOf { selected.imageDraws.getValue(it).timeMs })
    }

    private fun elapsedMs(selected: Run): Long = (System.nanoTime() - selected.startNs) / 1_000_000

    private fun sampleMemory(selected: Run) {
        try {
            val info = Debug.MemoryInfo()
            Debug.getMemoryInfo(info)
            val runtime = Runtime.getRuntime()
            val sample = Memory(elapsedMs(selected), info.totalPss,
                (runtime.totalMemory() - runtime.freeMemory()) / 1024, Debug.getNativeHeapAllocatedSize() / 1024)
            synchronized(lock) {
                if (run !== selected || selected.stopNs != null) return@synchronized
                if (selected.memory.size < MAX_MEMORY_SAMPLES) selected.memory.add(sample) else selected.memoryOverflow++
            }
        } catch (e: RuntimeException) {
            warning(selected.id, "PSS sample failed: ${e.javaClass.simpleName}")
        }
    }

    private fun warning(runId: Long, message: String) = synchronized(lock) {
        run?.takeIf { it.id == runId && it.stopNs == null && it.warnings.size < 8 }?.warnings?.add(message)
    }

    private fun snapshot(): Snapshot? = synchronized(lock) {
        val s = run ?: return@synchronized null
        Snapshot(s.id, s.config, s.count, s.source, s.startedAtEpochMs,
            ((s.stopNs ?: System.nanoTime()) - s.startNs) / 1_000_000,
            (s.cpuStopMs ?: android.os.Process.getElapsedCpuTime()) - s.cpuStartMs, HashMap(s.metadata),
            s.stopNs == null, s.stopReason, ArrayList(s.frames), ArrayList(s.memory), s.frameOverflow,
            s.memoryOverflow, s.warnings.toList(), s.initialIds?.toSet(), s.viewportCapturedMs,
            HashMap(s.imageDraws), s.viewportReadyMs, ImageLoadRecorder.snapshot())
    }

    fun report(): String {
        val s = snapshot() ?: return "Chưa có phiên đo. Chọn Bắt đầu đo, mở bộ sưu tập, thực hiện cùng kịch bản rồi Dừng đo.\nKhông lấy số liệu khi chưa bắt đầu."
        return renderReport(s)
    }

    private fun renderReport(s: Snapshot): String = buildString {
        appendLine("Phiên ${s.id} · ${if (s.active) "ĐANG ĐO" else "ĐÃ DỪNG"} · ${s.durationMs} ms")
        appendLine("${s.count} ảnh · ${s.source}")
        if (!s.active) appendLine("Dừng: ${s.stopReason}")
        appendLine()
        append(ImageLoadRecorder.renderReport(s.requests))
        appendLine()
        val ids = s.initialIds
        val completed = ids?.count { s.draws.containsKey(it) } ?: 0
        val failed = ids?.count { s.draws[it]?.success == false } ?: 0
        appendLine("Viewport đầu: ${ids?.size ?: 0} ảnh, sẵn sàng $completed, lỗi $failed.")
        appendLine("Sẵn sàng vẽ viewport (pre-draw): ${s.viewportReadyMs?.let { "$it ms" } ?: "chưa đạt"} từ lúc phiên bắt đầu.")
        val successReady = s.viewportReadyMs?.takeIf { ids != null && failed == 0 && completed == ids.size }
        appendLine("Đủ ảnh thành công trong viewport: ${successReady?.let { "$it ms" } ?: "chưa đạt"}.")
        appendLine("Mốc gồm cả ảnh lỗi; không phải FullyDrawn hay thời điểm pixel xuất hiện trên màn hình.")
        val peak = s.memory.maxOfOrNull { it.pssKb }
        appendLine(String.format(Locale.US, "PSS đỉnh lấy mẫu: %s MiB, n=%d, chu kỳ ≥500 ms.",
            peak?.let { String.format(Locale.US, "%.2f", it / 1024.0) } ?: "—", s.memory.size))
        appendLine("CPU toàn tiến trình trong phiên: ${s.cpuMs} ms (tổng các luồng, không phải CPU%).")
        appendLine("PSS tính cả tiến trình; lấy mẫu có thể bỏ lỡ đỉnh giữa hai lần đo.")
        val eligible = s.frames.filter { !it.firstDraw && it.budgetNs > 0 }
        val deadlineFrames = s.frames.filter { !it.firstDraw && it.deadlineNs > 0 }
        if (deadlineFrames.isNotEmpty()) {
            val missed = deadlineFrames.count { it.totalNs >= it.deadlineNs }
            appendLine("Frame trễ hạn hệ thống: $missed/${deadlineFrames.size} (API31+, TOTAL_DURATION >= DEADLINE).")
        } else appendLine("Frame deadline hệ thống: chưa có số đo (cần API31+).")
        val over = eligible.count { it.totalNs > it.budgetNs }
        val percent = if (eligible.isEmpty()) "—" else String.format(Locale.US, "%.2f", over * 100.0 / eligible.size)
        appendLine("Frame vượt 1 chu kỳ màn hình: $over/${eligible.size} ($percent%).")
        appendLine("TOTAL_DURATION > 1/refreshRate; loại first-draw. Đây không phải chỉ số jank chính thức của Android.")
        appendLine("Frame p90: ${percentile(eligible.map { it.totalNs }, .9).let { if (it < 0) "—" else String.format(Locale.US, "%.2f ms", it / 1_000_000.0) }}.")
        appendLine("Callback frame bị rơi: ${s.frames.sumOf { it.dropped }}; frame vượt giới hạn lưu: ${s.frameOverflow}.")
        if (s.memoryOverflow > 0) appendLine("Mẫu PSS vượt giới hạn lưu: ${s.memoryOverflow}.")
        s.warnings.forEach { appendLine(it) }
        appendLine("Xuất sau khi dừng để tránh tác động I/O vào kết quả. Kết quả hiện tại chưa đại diện mọi thiết bị.")
    }

    fun exportBundle(context: Context): File {
        val s = snapshot() ?: error("Chưa có phiên đo để xuất.")
        check(!s.active) { "Hãy dừng đo trước khi xuất kết quả." }
        val dir = File(context.getExternalFilesDir(null) ?: context.filesDir, "measurements")
        check(dir.exists() || dir.mkdirs()) { "Không tạo được thư mục kết quả." }
        val file = File(dir, "Cyclone_run${s.id}_${System.currentTimeMillis()}.zip")
        ZipOutputStream(file.outputStream().buffered()).use { zip ->
            fun entry(name: String, content: String) {
                zip.putNextEntry(ZipEntry(name))
                zip.write(content.toByteArray(Charsets.UTF_8))
                zip.closeEntry()
            }
            entry("requests.csv", ImageLoadRecorder.csv(s.requests))
            entry("frames.csv", buildString {
                appendLine("runId,callbackTimeMs,totalNs,displayBudgetNs,systemDeadlineNs,firstDraw,overBudget,deadlineMissed,droppedCallbacks")
                s.frames.forEach { f -> appendLine("${s.id},${f.timeMs},${f.totalNs},${f.budgetNs},${f.deadlineNs},${f.firstDraw},${!f.firstDraw && f.budgetNs > 0 && f.totalNs > f.budgetNs},${!f.firstDraw && f.deadlineNs > 0 && f.totalNs >= f.deadlineNs},${f.dropped}") }
            })
            entry("memory.csv", buildString {
                appendLine("runId,timeMs,pssKb,javaHeapUsedKb,nativeHeapAllocatedKb")
                s.memory.forEach { m -> appendLine("${s.id},${m.timeMs},${m.pssKb},${m.javaHeapKb},${m.nativeHeapKb}") }
            })
            entry("viewport.csv", buildString {
                appendLine("runId,productId,terminalPreDrawMs,success")
                s.initialIds.orEmpty().sorted().forEach { id ->
                    val draw = s.draws[id]
                    appendLine("${s.id},$id,${draw?.timeMs ?: -1},${draw?.success ?: ""}")
                }
            })
            entry("summary.json", json(s).toString(2))
            entry("README.txt", renderReport(s) + "\nPercentile: nearest rank. Millisecond request values are rounded down. -1 means unavailable.\nRequest fetch time includes Coil fetcher work; NETWORK is Coil's source, not HTTP wire byte accounting.\nRAM sample and frame metrics introduce measurement overhead. Do not sum repeated bitmap allocations as process memory.\n")
        }
        return file
    }

    private fun json(s: Snapshot): JSONObject {
        val eligible = s.frames.filter { !it.firstDraw && it.budgetNs > 0 }
        return JSONObject().apply {
            put("schemaVersion", 4)
            put("automation", JSONObject(s.metadata))
            put("processCpuMs", s.cpuMs)
            put("processId", android.os.Process.myPid())
            put("javaMaxHeapBytes", Runtime.getRuntime().maxMemory())
            put("framesWithSystemDeadline", s.frames.count { !it.firstDraw && it.deadlineNs > 0 })
            put("framesMissingSystemDeadline", s.frames.count { !it.firstDraw && it.deadlineNs > 0 && it.totalNs >= it.deadlineNs })
            put("runId", s.id)
            put("config", s.config)
            put("count", s.count)
            put("source", s.source)
            put("startedAtEpochMs", s.startedAtEpochMs)
            put("durationMs", s.durationMs)
            put("stopReason", s.stopReason)
            put("device", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("androidSdk", Build.VERSION.SDK_INT)
            put("buildType", BuildConfig.BUILD_TYPE)
            put("versionName", BuildConfig.VERSION_NAME)
            put("requestsCreated", s.requests.created)
            put("requestsStarted", s.requests.started)
            put("requestsTerminal", s.requests.terminal)
            put("requestsIncompleteAtSnapshot", s.requests.incomplete)
            put("requestRows", s.requests.rows.size)
            put("requestRowsOmitted", s.requests.omitted)
            put("frameRowsOmitted", s.frameOverflow)
            put("memoryRowsOmitted", s.memoryOverflow)
            put("frameCallbacksDropped", s.frames.sumOf { it.dropped })
            put("eligibleFrames", eligible.size)
            put("framesOverDisplayPeriod", eligible.count { it.totalNs > it.budgetNs })
            put("frameP90Ns", percentile(eligible.map { it.totalNs }, .9))
            put("sampledPssPeakKb", s.memory.maxOfOrNull { it.pssKb } ?: JSONObject.NULL)
            put("pssSampleIntervalMs", PSS_INTERVAL_MS)
            put("pssSampleCount", s.memory.size)
            put("initialViewportIds", JSONArray(s.initialIds.orEmpty().sorted()))
            put("viewportCapturedMs", s.viewportCapturedMs ?: JSONObject.NULL)
            put("viewportTerminalPreDrawMs", s.viewportReadyMs ?: JSONObject.NULL)
            put("viewportSuccessfulPreDrawMs", s.viewportReadyMs?.takeIf { s.initialIds != null && s.initialIds.all { s.draws[it]?.success == true } } ?: JSONObject.NULL)
            put("viewportErrorCount", s.initialIds.orEmpty().count { s.draws[it]?.success == false })
            put("warnings", JSONArray(s.warnings))
            put("definitions", JSONObject().apply {
                put("requestsIncompleteAtSnapshot", "Requests whose listener was created in this run but no terminal callback was accepted before the snapshot/stop; late completion is excluded")
                put("requestPercentiles", "Nearest-rank percentiles of retained successful terminal rows only; incomplete requests are censored, not zero-duration")
                put("framesMissingSystemDeadline", "On API31+, TOTAL_DURATION >= FrameMetrics.DEADLINE excluding first-draw; app deadline overruns, not all compositor jank")
                put("processCpuMs", "Process.getElapsedCpuTime delta during session, all app threads, milliseconds; not elapsed wall time or CPU percent")
                put("requestTotalMs", "Coil EventListener onStart to onSuccess/onError/onCancel; excludes callbacks after stop; not draw latency")
                put("decodeMs", "Sum of completed Coil decoder callback intervals; -1 when not observed")
                put("sampledPssPeakKb", "Maximum process PSS observed at 500ms plus work/scheduling intervals; not continuous peak")
                put("framesOverDisplayPeriod", "TOTAL_DURATION > 1/current display refreshRate, excluding FIRST_DRAW_FRAME; not platform jank classification")
                put("viewportTerminalPreDrawMs", "Run start until all frozen initial visible product IDs have a terminal drawable at pre-draw, including errors; not FullyDrawn")
            })
        }
    }
}
