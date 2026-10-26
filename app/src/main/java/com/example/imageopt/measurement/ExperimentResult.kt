package com.example.imageopt.measurement

data class ExperimentResult(
    val timeMs: Long,
    val config: String,
    val outcome: String,
    val source: String,
    val totalMs: Long,
    val decodeMs: Long,
    val width: Int,
    val height: Int,
    val url: String,
    val runId: Long,
    val requestId: Long,
    val fetchMs: Long = -1,
    val bitmapBytes: Long = -1,
    val allocationBytes: Long = -1,
    val bitmapConfig: String = "",
    val error: String = ""
)
