package com.example.imageopt.data

import java.net.URI

data class ImageSource(
    val baseUrl: String = AppConfig.BASE_URL,
    val format: String = "JPEG",
    val version: Int = 1,
    val errorEnabled: Boolean = false,
    val delayMs: Int = 0
) {
    val isPicsum: Boolean get() = URI(baseUrl).host.equals("picsum.photos", true)
    fun description() = "$baseUrl · $format · v$version · lỗi=$errorEnabled · trễ=${delayMs}ms"

    companion object {
        fun validated(base: String, format: String, version: Int, error: Boolean, delay: Int): ImageSource {
            val clean = base.trim().trimEnd('/')
            val uri = runCatching { URI(clean) }.getOrNull()
            require(uri != null && uri.scheme in listOf("http", "https") && !uri.host.isNullOrBlank()
                && uri.userInfo == null && uri.query == null && uri.fragment == null) {
                "URL cần bắt đầu http:// hoặc https://, không chứa query hay tài khoản."
            }
            require(format in listOf("JPEG", "PNG", "WEBP")) { "Định dạng không hợp lệ." }
            require(delay in 0..60000) { "Độ trễ phải từ 0 đến 60000 ms." }
            val source = ImageSource(clean, format, version.coerceIn(1, 999999), error, delay)
            require(!source.isPicsum || (format == "JPEG" && delay == 0)) {
                "PNG/WebP và độ trễ cần máy chủ local. Picsum chỉ dùng JPEG, trễ 0."
            }
            return source
        }
    }
}
