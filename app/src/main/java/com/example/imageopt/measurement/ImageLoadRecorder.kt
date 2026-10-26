package com.example.imageopt.measurement

import android.content.Context
import android.graphics.drawable.BitmapDrawable
import android.util.Log
import coil.EventListener
import coil.decode.DecodeResult
import coil.decode.Decoder
import coil.fetch.FetchResult
import coil.fetch.Fetcher
import coil.request.ErrorResult
import coil.request.ImageRequest
import coil.request.Options
import coil.request.SuccessResult
import java.io.File
import java.util.Locale
import java.util.concurrent.atomic.AtomicLong

const val TAG = "IMG_BENCH"

object ImageLoadRecorder : EventListener.Factory {
    internal const val MAX_RESULTS = 5000
    private val lock = Any()
    private val sequence = AtomicLong()
    private val results = ArrayList<ExperimentResult>()
    private var activeRun: Long? = null
    private var startedNs = 0L
    private var omitted = 0
    private var created = 0
    private var started = 0
    private var terminal = 0
    @Volatile var config: String = "A"
        private set

    fun reset(newConfig: String) = MeasurementSession.reset(newConfig)

    internal fun beginRun(runId: Long, startNs: Long, newConfig: String) = synchronized(lock) {
        clearLocked(newConfig)
        startedNs = startNs
        activeRun = runId
    }

    internal fun clear(newConfig: String) = synchronized(lock) { clearLocked(newConfig) }

    private fun clearLocked(newConfig: String) {
        results.clear()
        activeRun = null
        omitted = 0
        created = 0
        started = 0
        terminal = 0
        startedNs = 0
        config = newConfig
    }

    internal fun endRun(runId: Long) = synchronized(lock) {
        if (activeRun == runId) activeRun = null
    }

    override fun create(request: ImageRequest): EventListener {
        val session = synchronized(lock) {
            activeRun?.let {
                created++
                Triple(it, startedNs, config)
            }
        } ?: return object : EventListener {}
        val requestId = sequence.incrementAndGet()
        return object : EventListener {
            private var startNs = 0L
            private var decodeStartNs = 0L
            private var fetchStartNs = 0L
            private var decodeNs = -1L
            private var fetchNs = -1L
            private var recorded = false
            private var hasStarted = false

            override fun onStart(request: ImageRequest) {
                startNs = System.nanoTime()
                synchronized(lock) {
                    if (activeRun == session.first && !hasStarted) {
                        hasStarted = true
                        started++
                    }
                }
            }
            override fun fetchStart(request: ImageRequest, fetcher: Fetcher, options: Options) {
                fetchStartNs = System.nanoTime()
            }
            override fun fetchEnd(request: ImageRequest, fetcher: Fetcher, options: Options, result: FetchResult?) {
                if (fetchStartNs > 0) fetchNs = fetchNs.coerceAtLeast(0) + System.nanoTime() - fetchStartNs
                fetchStartNs = 0
            }
            override fun decodeStart(request: ImageRequest, decoder: Decoder, options: Options) {
                decodeStartNs = System.nanoTime()
            }
            override fun decodeEnd(request: ImageRequest, decoder: Decoder, options: Options, result: DecodeResult?) {
                if (decodeStartNs > 0) decodeNs = decodeNs.coerceAtLeast(0) + System.nanoTime() - decodeStartNs
                decodeStartNs = 0
            }
            private fun record(request: ImageRequest, outcome: String, success: SuccessResult? = null, error: String = "") {
                val now = System.nanoTime()
                val bitmap = (success?.drawable as? BitmapDrawable)?.bitmap
                val row = ExperimentResult(
                    timeMs = (now - session.second) / 1_000_000,
                    config = session.third,
                    outcome = outcome,
                    source = success?.dataSource?.name ?: "-",
                    totalMs = if (startNs > 0) (now - startNs) / 1_000_000 else -1,
                    decodeMs = if (decodeNs >= 0) decodeNs / 1_000_000 else -1,
                    width = bitmap?.width ?: 0,
                    height = bitmap?.height ?: 0,
                    url = request.data.toString().take(2048),
                    runId = session.first,
                    requestId = requestId,
                    fetchMs = if (fetchNs >= 0) fetchNs / 1_000_000 else -1,
                    bitmapBytes = bitmap?.byteCount?.toLong() ?: -1,
                    allocationBytes = bitmap?.allocationByteCount?.toLong() ?: -1,
                    bitmapConfig = bitmap?.config?.name ?: "",
                    error = error.take(300)
                )
                synchronized(lock) {
                    if (activeRun != session.first || recorded) return
                    recorded = true
                    terminal++
                    if (results.size < MAX_RESULTS) results.add(row) else omitted++
                }
            }
            override fun onSuccess(request: ImageRequest, result: SuccessResult) = record(request, "OK", result)
            override fun onError(request: ImageRequest, result: ErrorResult) = record(
                request, "ERROR", error = "${result.throwable.javaClass.simpleName}: ${result.throwable.message.orEmpty()}"
            )
            override fun onCancel(request: ImageRequest) = record(request, "CANCEL")
        }
    }

    internal data class Snapshot(
        val config: String, val rows: List<ExperimentResult>, val omitted: Int,
        val created: Int, val started: Int, val terminal: Int
    ) {
        val incomplete: Int get() = (created - terminal).coerceAtLeast(0)
    }
    internal fun snapshot(): Snapshot = synchronized(lock) {
        Snapshot(config, ArrayList(results), omitted, created, started, terminal)
    }

    fun summaryLine(): String {
        val s = snapshot()
        val ok = s.rows.filter { it.outcome == "OK" }
        return "config=${s.config} ok=${ok.size} memoryCache=${ok.count { it.source == "MEMORY_CACHE" }} " +
            "disk=${ok.count { it.source == "DISK" }} network=${ok.count { it.source == "NETWORK" }} " +
            "error=${s.rows.count { it.outcome == "ERROR" }} cancel=${s.rows.count { it.outcome == "CANCEL" }} incomplete=${s.incomplete} omitted=${s.omitted}"
    }

    fun logSummary() { Log.i(TAG, "SUMMARY ${summaryLine()}") }
    fun report(): String = renderReport(snapshot())

    internal fun renderReport(s: Snapshot): String = buildString {
        val ok = s.rows.filter { it.outcome == "OK" }
        appendLine("Cấu hình: ${s.config}")
        appendLine("Request tạo: ${s.created}, bắt đầu: ${s.started}, kết thúc: ${s.terminal}, chưa có kết quả: ${s.incomplete}.")
        appendLine("Thành công: ${ok.size} | Lỗi: ${s.rows.count { it.outcome == "ERROR" }} | Hủy: ${s.rows.count { it.outcome == "CANCEL" }}")
        for (source in listOf("NETWORK", "DISK", "MEMORY_CACHE", "MEMORY")) {
            val times = ok.filter { it.source == source }.map { it.totalMs }.filter { it >= 0 }
            appendLine("$source: n=${times.size}, median=${percentile(times, .5)} / p90=${percentile(times, .9)} ms")
        }
        val decode = ok.map { it.decodeMs }.filter { it >= 0 }
        appendLine("Decode: n=${decode.size}, median=${percentile(decode, .5)} / p90=${percentile(decode, .9)} ms")
        val bytes = ok.map { it.allocationBytes }.filter { it >= 0 }
        if (bytes.isNotEmpty()) appendLine(String.format(Locale.US,
            "Bitmap allocation mỗi kết quả: TB %.2f MiB, lớn nhất %.2f MiB (không phải RAM tiến trình).",
            bytes.average() / 1048576.0, bytes.max() / 1048576.0))
        ok.firstOrNull()?.let { appendLine("Ví dụ bitmap: ${it.width}×${it.height}, ${it.bitmapConfig}.") }
        appendLine("-1 = không có số đo; memory hit thường không chạy decode. Thời gian request không phải thời gian hiển thị.")
        appendLine("Percentile chỉ gồm request thành công kết thúc trong phiên; request chưa xong khi dừng không có thời gian hoàn tất.")
        if (s.omitted > 0) appendLine("Đã bỏ ${s.omitted} bản ghi vượt giới hạn $MAX_RESULTS; thống kê request chỉ dùng phần được giữ.")
    }

    fun exportCsv(context: Context): File {
        check(MeasurementSession.hasSession) { "Chưa có phiên đo để xuất." }
        check(!MeasurementSession.isActive) { "Hãy dừng đo trước khi xuất kết quả." }
        val file = File(context.getExternalFilesDir(null) ?: context.filesDir, "requests_${System.currentTimeMillis()}.csv")
        file.writeText(csv(snapshot()))
        return file
    }

    internal fun csv(s: Snapshot): String = buildString {
        appendLine("runId,requestId,timeMs,config,outcome,source,totalMs,fetchMs,decodeMs,width,height,bitmapBytes,allocationBytes,bitmapConfig,url,error")
        s.rows.forEach { r -> appendLine(listOf(r.runId, r.requestId, r.timeMs, r.config, r.outcome, r.source,
            r.totalMs, r.fetchMs, r.decodeMs, r.width, r.height, r.bitmapBytes, r.allocationBytes,
            r.bitmapConfig, r.url, r.error).joinToString(",") { csvCell(it.toString()) }) }
    }
}

internal fun percentile(values: List<Long>, fraction: Double): Long {
    if (values.isEmpty()) return -1
    val sorted = values.sorted()
    return sorted[(kotlin.math.ceil(fraction * sorted.size).toInt() - 1).coerceIn(0, sorted.lastIndex)]
}

internal fun csvCell(value: String): String = "\"${value.replace("\"", "\"\"")}\""
