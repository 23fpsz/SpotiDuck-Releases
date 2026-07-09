<p align="center">
  <img src="./logo.webp" width="120" alt="SpotiDuck Logo" />
</p>

<h1 align="center">SpotiDuck Releases 🦆</h1>

<p align="center">
  <a href="https://github.com/23fpsz/SpotiDuck-Releases/releases/latest">
    <img src="https://img.shields.io/badge/Download-Latest_APK-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Download Latest APK" height="40" />
  </a>
</p>

<p align="center">
  <a href="https://discord.gg/g6NXTJPBYQ">
    <img src="https://img.shields.io/badge/Join-Discord_Community-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join Discord Community" height="40" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android-3DDC84?logo=android&logoColor=white&style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/Kotlin-1.9+-7F52FF?logo=kotlin&logoColor=white&style=flat-square" alt="Kotlin" />
  <img src="https://img.shields.io/badge/License-GNU_GPLv3-blue?style=flat-square" alt="License" />
</p>

> [!WARNING]
> **Official Source Only:** SpotiDuck is **only** published and distributed on this official GitHub repository. Do not download or trust builds of this application from any other websites, app stores, or third-party channels, as they are unverified and may contain malicious modifications.

Welcome to the download and releases page for **SpotiDuck**—a high-performance, web-wrapped Spotify client for Android featuring built-in ad-blocking, media controls, and widgets.

By wrapping the Spotify Web Player in a highly optimized Android WebView, SpotiDuck combines the full feature set of Spotify's web browser experience with native Android integrations—such as background service control, built-in ad-blocking, lock screen media sessions, widgets, and Android Auto.

> [!NOTE]
> **Credits:** SpotiDuck is built upon and inspired by **Spotifuck**, the original unofficial Android Spotify web wrapper developed by **deviato**. We would like to express our gratitude to the original creator for laying the groundwork for this project.

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

<p align="center">
  <img src="./screenshots/landscape_mode.png" width="60%" alt="Landscape Mode" />
</p>

---

## ⚠️ Compatibility & Playback Warnings

The application might not function correctly under the following conditions:

1. **Account Limitations**: Free accounts may experience playback loading errors on mobile WebViews. While SpotiDuck includes settings to handle platform compatibility, server-side changes to player browser policies may affect playback stability.
2. **Third-Party Logins**: Google or Facebook sign-ins may occasionally block authentications inside embedded browsers. Adjusting the compatibility configuration or user-agent scaling in settings may resolve these sign-in hurdles.
3. **DRM & Media Pipelines**: Secure media playback requires device-level DRM support. Custom ROMs or devices lacking proper security certifications may fail to start media streams.
4. **Aggressive Filters**: Loading custom or overly restrictive filter blocklists in settings can block essential server endpoints, preventing tracks from playing.
5. **System WebView Version**: For proper compatibility with preloading and layout adjustments, keep your device's System WebView updated to the latest version via the Google Play Store.