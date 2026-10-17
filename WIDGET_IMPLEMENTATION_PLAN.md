# Approved Home-Screen Widget Implementation Plan

## Goal
Implement the approved Android home-screen music widget in the experimental build while preserving the current performance changes.

## Exact widget design (do not redesign)
- Large Spotify-style rounded card with album artwork on the left.
- Track line formatted exactly as `Song Title • Artist`.
- Playlist name on the second line when available.
- One horizontal row of controls: Shuffle (cycle No Shuffle → Shuffle → Smart Shuffle), Previous, Play/Pause, Next, Repeat (Off → All → One), Like.
- Bottom row of five playlist/album tiles, matching the approved mockup.
- No SpotiDuck branding in the widget.
- Keep `fast-performance-build` untouched; implement on `widget-design-experiment`.

## Requirements
1. Use the actual native Android source project; release APK files and a binary-patching workflow alone are insufficient for reliable native widget development.
2. Use system media-session metadata for title, artist and artwork; show playlist name only when reliably available.
3. Connect controls to the active playback session and reflect supported states. Do not claim Smart Shuffle works unless the playback integration truly supports it.
4. Keep widget updates event-driven/lightweight; avoid tight polling loops or extra WebView/network work.
5. Build and verify the APK before sharing it; a mockup is not a working widget.

## Current blocker
This releases repository contains release artifacts and a workflow that decodes/rebuilds the APK, not the complete Android Gradle project. Locate the appropriate source project/fork or obtain the source before implementing native widget changes.

## Performance constraints
Retain the performance changes from `fast-performance-build`. Do not redesign the widget or change the main branch.
