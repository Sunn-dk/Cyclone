package com.example.imageopt

import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.NavHostFragment
import com.example.imageopt.image.ExperimentConfig
import com.example.imageopt.image.ExperimentPrefs
import com.example.imageopt.measurement.AutomationRun
import com.example.imageopt.measurement.MeasurementSession
import com.example.imageopt.ui.ProductViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.File

class MainActivity : AppCompatActivity() {
    private val vm: ProductViewModel by viewModels()
    private var preparing = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) {
            val prefs = ExperimentPrefs(this)
            intent.getStringExtra("config")?.let { name ->
                ExperimentConfig.values().firstOrNull { it.name == name }?.let { prefs.config = it }
            }
            if (intent.hasExtra("count")) prefs.count = intent.getIntExtra("count", 100)
        }
        vm.automationPreparing = savedInstanceState == null && intent.getBooleanExtra("automation", false)
        setContentView(R.layout.activity_main)
        if (savedInstanceState == null) handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent) {
        if (!intent.getBooleanExtra("automation", false)) {
            intent.getStringExtra("config")?.let { name ->
                ExperimentConfig.values().firstOrNull { it.name == name }?.let { vm.setConfig(it) }
            }
            if (intent.hasExtra("count")) vm.setCount(intent.getIntExtra("count", 100).takeIf {
                it in listOf(100, 500, 1000)
            } ?: 100)
            return
        }
        if (preparing) return
        preparing = true
        vm.automationPreparing = true
        lifecycleScope.launch {
            try {
                val spec = AutomationRun.from(intent) ?: return@launch
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                delay(150)
                val host = supportFragmentManager.findFragmentById(R.id.nav_host) as NavHostFragment
                val nav = host.navController
                nav.popBackStack(R.id.productListFragment, false)
                if (nav.currentDestination?.id != R.id.experimentFragment) nav.navigate(R.id.experimentFragment)
                // Hủy view/request cũ trước khi chuẩn bị cache.
                delay(300)
                vm.prepareAutomation(spec)
                nav.popBackStack(R.id.productListFragment, false)
            } catch (e: CancellationException) { throw e }
            catch (e: Exception) {
                vm.automationPreparing = false
                val dir = File(getExternalFilesDir(null) ?: filesDir, "automation").apply { mkdirs() }
                val label = intent.getStringExtra("run_label")?.takeIf {
                    it.matches(Regex("[A-Za-z0-9_-]{1,100}"))
                } ?: "invalid"
                File(dir, "$label.error.json").writeText(JSONObject().put("error", e.toString()).toString())
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            } finally { preparing = false }
        }
    }

    override fun onStop() {
        MeasurementSession.stopForActivity(this, "activity_background")
        super.onStop()
    }
    override fun onDestroy() {
        MeasurementSession.stopForActivity(this, "activity_destroyed")
        super.onDestroy()
    }
}
