package com.example.imageopt.data

object ProductRepository {
    fun generate(count: Int, source: ImageSource = ImageSource()): List<Product> =
        List(count.coerceIn(1, 1000)) { byId(it + 1, source) }

    fun byId(id: Int, source: ImageSource = ImageSource()): Product {
        val ratio = listOf(2 to 3, 1 to 1, 3 to 2, 3 to 4, 4 to 3)[(id - 1).mod(5)]
        val w = if (ratio.first >= ratio.second) 3000 else 3000 * ratio.first / ratio.second
        val h = if (ratio.first >= ratio.second) 3000 * ratio.second / ratio.first else 3000
        fun scaled(edge: Int) = (w * edge / maxOf(w, h)) to (h * edge / maxOf(w, h))
        fun url(size: Pair<Int, Int>): String {
            val path = if (source.errorEnabled && id % 10 == 0) "/error/item$id"
                else "/seed/item$id/${size.first}/${size.second}"
            return source.baseUrl + path + "?format=${source.format}&v=${source.version}&delay_ms=${source.delayMs}"
        }
        return Product(id, "Khám phá #$id", "${50 + (id - 1) % 450}.000 đ",
            url(scaled(720)), url(scaled(1600)), w, h, url(w to h))
    }
}
