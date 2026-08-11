<p align="center">
  <img src="./logo.webp" width="120" alt="SpotiDuck Logo" />
</p>

<h1 align="center">SpotiDuck 🦆</h1>

<p align="center">
  <a href="https://github.com/RMNO21/SpotiDuck/releases/latest">
    <img src="https://img.shields.io/badge/Download-Latest_Release-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Download Latest Release" height="40" />
  </a>
  <a href="https://discord.gg/NNXDGZEDFs">
    <img src="https://img.shields.io/badge/Join-Discord_Community-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join Discord Community" height="40" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android_%2F_PWA-3DDC84?logo=android&logoColor=white&style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/PWA-Supported-7F52FF?logo=pwa&logoColor=white&style=flat-square" alt="PWA Ready" />
  <img src="https://img.shields.io/badge/License-GNU_GPLv3-blue?style=flat-square" alt="License" />
</p>

---

Welcome to **SpotiDuck**—a high-performance, native-like web client for Spotify featuring built-in ad-blocking, intelligent connection retry management, download & cache progress tracking, and offline Service Worker resilience.

By wrapping Spotify in an optimized native App Shell (PWA), SpotiDuck delivers a fast, desktop-grade Spotify experience with seamless native controls—eliminating the clunky "bare WebView" feel.

---

## ⚡ Key Features

* **⚡ Native App Shell & UI**: Modern glassmorphic interface with bottom navigation, responsive tabs, smooth micro-animations, and custom dark mode styling.
* **📡 Intelligent Connection Lost & Retry Engine**:
  * Real-time network detection with non-intrusive alert banners.
  * Automatic retry countdowns with exponential backoff strategy.
  * Manual "Retry Connection" button to instantly test network reachability.
* **📥 Download & Cache Progress Manager**:
  * Displays active and cached downloads, track sizes, percentage progress, and transfer speeds.
  * Total downloaded size metrics and cache-clearing management.
* **🛡️ Built-in Ad-Blocking & User-Agent Emulation**: Bypasses mobile WebView playback restrictions by disguising traffic as modern desktop client sessions.
* **📶 Live Spotify Health Monitoring**: Integrated status checks for Spotify Client Token, OAuth Auth, REST API, Widevine DRM, and Edge CDN endpoints.
* **📲 Progressive Web App (PWA)**: Standalone display mode, Service Worker cache-first offline support, and installable app manifest (`manifest.json`).

---

## 📸 App Interface Showcase

<p align="center">
  <img src="./screenshots/home_screen.jpg" width="31%" alt="Home Screen" />
  <img src="./screenshots/library_menu.png" width="31%" alt="Library Menu" />
  <img src="./screenshots/fullscreen_player.png" width="31%" alt="Full Screen Player" />
</p>

<p align="center">
  <img src="./screenshots/lockscreen_player.jpg" width="47%" alt="Lock Screen Player" />
  <img src="./screenshots/widget.png" width="47%" alt="Widget Support" />
</p>

---

## 🛠️ Local Development & Testing

You can run the native app shell locally using any HTTP server:

```bash
# Python
python -m http.server 8080

# Node.js
npx http-server -p 8080
```

Open `http://localhost:8080` in your browser to launch the SpotiDuck App Shell.