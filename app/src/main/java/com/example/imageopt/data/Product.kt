package com.example.imageopt.data

data class Product(
    val id: Int,
    val name: String,
    val price: String,
    val thumbUrl: String,   // ảnh nhỏ
    val detailUrl: String,  // ảnh chi tiết vừa phải
    val imageWidth: Int,
    val imageHeight: Int,
    val rawUrl: String      // ảnh gốc lớn
)
