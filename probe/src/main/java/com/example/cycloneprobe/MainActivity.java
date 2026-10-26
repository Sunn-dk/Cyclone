package com.example.cycloneprobe;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.widget.TextView;
import android.widget.ScrollView;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipEntry;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        JSONObject result = new JSONObject();
        try {
            Intent intent = getIntent();
            Uri uri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
            if (uri == null || !"content".equals(uri.getScheme())
                    || !"com.example.imageopt.files".equals(uri.getAuthority())) {
                throw new IOException("Only the Cyclone test provider is accepted.");
            }
            result.put("uri", uri.toString());
            result.put("grant_flag", (intent.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream input = getContentResolver().openInputStream(uri)) {
                if (input == null) throw new IOException("No input stream");
                byte[] buffer = new byte[8192];
                int length;
                while ((length = input.read(buffer)) != -1) {
                    bytes.write(buffer, 0, length);
                    if (bytes.size() > 20 * 1024 * 1024) throw new IOException("Test ZIP too large");
                }
            }
            byte[] data = bytes.toByteArray();
            MessageDigest hash = MessageDigest.getInstance("SHA-256");
            StringBuilder digest = new StringBuilder();
            for (byte b : hash.digest(data)) digest.append(String.format("%02x", b & 255));
            result.put("sha256", digest.toString());
            result.put("bytes", data.length);
            JSONArray entries = new JSONArray();
            try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream(data))) {
                ZipEntry entry;
                while ((entry = zip.getNextEntry()) != null) {
                    entries.put(entry.getName());
                    if ("summary.json".equals(entry.getName())) {
                        ByteArrayOutputStream summary = new ByteArrayOutputStream();
                        byte[] buffer = new byte[4096];
                        int length;
                        while ((length = zip.read(buffer)) != -1) summary.write(buffer, 0, length);
                        result.put("summary", new JSONObject(summary.toString("UTF-8")));
                    }
                    zip.closeEntry();
                }
            }
            result.put("entries", entries);
            result.put("read_ok", result.has("summary") && entries.length() >= 6);
        } catch (Exception e) {
            try { result.put("read_ok", false); result.put("error", e.toString()); } catch (Exception ignored) {}
        }
        try {
            File dir = getExternalFilesDir(null);
            if (dir == null) dir = getFilesDir();
            try (Writer writer = new OutputStreamWriter(new FileOutputStream(new File(dir, "result.json")), StandardCharsets.UTF_8)) {
                writer.write(result.toString(2));
            }
        } catch (Exception ignored) {}
        TextView text = new TextView(this);
        text.setTextSize(16);
        text.setPadding(24, 24, 24, 24);
        try { text.setText("Kiểm tra ZIP Cyclone\n\n" + result.toString(2)); } catch (Exception ignored) {}
        ScrollView scroll = new ScrollView(this);
        scroll.addView(text);
        setContentView(scroll);
    }
}
