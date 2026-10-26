package com.example.imageopt.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.example.imageopt.data.ImageSource
import com.example.imageopt.data.Product
import com.example.imageopt.data.ProductRepository
import com.example.imageopt.image.AppImageLoaders
import com.example.imageopt.image.ExperimentConfig
import com.example.imageopt.image.ExperimentPrefs
import com.example.imageopt.measurement.MeasurementSession
import com.example.imageopt.measurement.AutomationRun
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class GalleryState(val products: List<Product>, val config: ExperimentConfig,
    val source: ImageSource, val revision: Long)

class ProductViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = ExperimentPrefs(app)
    val config = MutableLiveData(prefs.config)
    val count = MutableLiveData(prefs.count)
    val state = MutableLiveData<GalleryState>()
    val busy = MutableLiveData(false)
    var source: ImageSource = prefs.source
        private set
    var automationPreparing = false
    var pendingMeasurement = false
    var pendingAutomation: AutomationRun? = null
    private var revision = 0L
    private var loadJob: Job? = null

    init { rebuild() }
    fun isCurrent(value: GalleryState): Boolean = value.revision == revision
    fun currentConfig(): ExperimentConfig = config.value ?: ExperimentConfig.D
    fun product(id: Int): Product = ProductRepository.byId(id, source)

    fun setConfig(value: ExperimentConfig) {
        if (busy.value == true || value == currentConfig()) return
        MeasurementSession.stop("configuration_changed")
        prefs.config = value
        config.value = value
        AppImageLoaders.clearAllMemory()
        rebuild()
    }

    fun setCount(value: Int) {
        if (busy.value == true || value == count.value) return
        require(value in listOf(100, 500, 1000))
        MeasurementSession.stop("count_changed")
        prefs.count = value
        count.value = value
        rebuild()
    }

    fun setSource(value: ImageSource) {
        if (busy.value == true || source == value) return
        MeasurementSession.stop("source_changed")
        source = value
        prefs.source = value
        AppImageLoaders.clearAllMemory()
        rebuild()
    }

    suspend fun clearCache(memoryOnly: Boolean) {
        if (busy.value == true) return
        busy.value = true
        MeasurementSession.stop("cache_cleared")
        try {
            val selected = currentConfig()
            withContext(Dispatchers.IO) {
                if (memoryOnly) AppImageLoaders.clearAllMemory()
                else AppImageLoaders.clearCache(getApplication(), selected)
            }
            rebuild()
        } finally { busy.value = false }
    }


    suspend fun prepareAutomation(spec: AutomationRun) {
        MeasurementSession.stop("automation_prepare")
        busy.value = true
        loadJob?.cancel()
        try {
            prefs.config = spec.config
            prefs.count = spec.count
            prefs.source = spec.source
            config.value = spec.config
            count.value = spec.count
            source = spec.source
            withContext(Dispatchers.IO) {
                AppImageLoaders.prepare(getApplication(), spec.config, spec.cache)
            }
            val generation = ++revision
            val products = withContext(Dispatchers.Default) { ProductRepository.generate(spec.count, spec.source) }
            pendingAutomation = spec
            automationPreparing = false
            state.value = GalleryState(products, spec.config, spec.source, generation)
        } finally { busy.value = false }
    }

    private fun rebuild() {
        val selected = currentConfig()
        val selectedSource = source
        val selectedCount = count.value ?: 100
        val generation = ++revision
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            val products = withContext(Dispatchers.Default) {
                ProductRepository.generate(selectedCount, selectedSource)
            }
            if (generation == revision) state.value = GalleryState(products, selected, selectedSource, generation)
        }
    }
}
