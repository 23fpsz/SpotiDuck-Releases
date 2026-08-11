/**
 * SpotiDuck Native App Shell Core Engine
 * Manages Connection Retry, Downloads Progress, Spotify Status, and PWA Shell.
 */

(function () {
  'use strict';

  // State Management
  const state = {
    isOnline: navigator.onLine,
    retryCount: 0,
    retryTimer: null,
    retrySecondsLeft: 5,
    downloads: [
      { id: 'dl-1', title: 'Spotify Web Player Core Bundle', size: '14.2 MB', progress: 100, status: 'completed', speed: '0 KB/s' },
      { id: 'dl-2', title: 'Widevine DRM License Certificates', size: '1.8 MB', progress: 100, status: 'completed', speed: '0 KB/s' },
      { id: 'dl-3', title: 'Offline Audio Stream Buffer #1', size: '8.5 MB', progress: 100, status: 'completed', speed: '0 KB/s' }
    ],
    statusHistory: [],
    chartInstance: null
  };

  // DOM Selectors
  const elements = {
    connectionBanner: document.getElementById('connection-banner'),
    bannerText: document.getElementById('banner-text'),
    retryCountdown: document.getElementById('retry-countdown'),
    btnManualRetry: document.getElementById('btn-manual-retry'),
    btnOfflineRetry: document.getElementById('btn-offline-retry'),
    networkBadge: document.getElementById('network-badge'),
    networkStatusText: document.getElementById('network-status-text'),
    offlineLayer: document.getElementById('offline-layer'),
    spotifyFrame: document.getElementById('spotify-frame'),

    // Downloads
    btnQuickDownload: document.getElementById('btn-quick-download'),
    btnAddTestDl: document.getElementById('btn-add-test-dl'),
    btnClearDownloads: document.getElementById('btn-clear-downloads'),
    dlTotalCount: document.getElementById('dl-total-count'),
    dlTotalSize: document.getElementById('dl-total-size'),
    dlSpeed: document.getElementById('dl-speed'),
    dlProgressPercent: document.getElementById('dl-progress-percent'),
    dlProgressFill: document.getElementById('dl-progress-fill'),
    downloadList: document.getElementById('download-list'),

    // Navigation & Tabs
    navItems: document.querySelectorAll('.nav-item'),
    tabPanes: document.querySelectorAll('.tab-pane'),

    // Status
    btnRefreshStatus: document.getElementById('btn-refresh-status'),
    servicesList: document.getElementById('services-list')
  };

  // Initializer
  function init() {
    setupTabNavigation();
    setupNetworkListeners();
    setupDownloadManager();
    setupStatusDashboard();
    registerServiceWorker();
    
    // Initial connection check
    checkNetworkStatus();
  }

  // --- 1. TAB NAVIGATION SYSTEM ---
  function setupTabNavigation() {
    elements.navItems.forEach(item => {
      item.addEventListener('click', () => {
        const targetTabId = item.getAttribute('data-tab');
        switchTab(targetTabId);
      });
    });

    elements.btnQuickDownload.addEventListener('click', () => {
      switchTab('tab-downloads');
    });
  }

  function switchTab(tabId) {
    elements.navItems.forEach(item => {
      const isTarget = item.getAttribute('data-tab') === tabId;
      item.classList.toggle('active', isTarget);
    });

    elements.tabPanes.forEach(pane => {
      const isTarget = pane.id === tabId;
      pane.classList.toggle('active', isTarget);
    });

    if (tabId === 'tab-status') {
      renderStatusChart();
    }
  }

  // --- 2. NETWORK CONNECTION & RETRY ENGINE ---
  function setupNetworkListeners() {
    window.addEventListener('online', () => handleNetworkChange(true));
    window.addEventListener('offline', () => handleNetworkChange(false));

    elements.btnManualRetry.addEventListener('click', () => triggerManualRetry());
    elements.btnOfflineRetry.addEventListener('click', () => triggerManualRetry());

    // Periodic network sanity check every 15s
    setInterval(checkNetworkStatus, 15000);
  }

  async function checkNetworkStatus() {
    if (!navigator.onLine) {
      handleNetworkChange(false);
      return;
    }

    try {
      // Light ping to check actual WAN reachability
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 4000);
      
      const res = await fetch('https://open.spotify.com/cdn-cgi/trace', {
        mode: 'no-cors',
        cache: 'no-store',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      handleNetworkChange(true);
    } catch (err) {
      // Failed ping attempt
      handleNetworkChange(false);
    }
  }

  function handleNetworkChange(isOnline) {
    state.isOnline = isOnline;

    if (isOnline) {
      // Connected State
      state.retryCount = 0;
      clearInterval(state.retryTimer);
      state.retryTimer = null;

      elements.connectionBanner.classList.remove('visible');
      elements.networkBadge.className = 'network-badge online';
      elements.networkStatusText.textContent = 'Online';
      elements.offlineLayer.style.display = 'none';
    } else {
      // Disconnected State
      elements.networkBadge.className = 'network-badge offline';
      elements.networkStatusText.textContent = 'Offline';
      elements.offlineLayer.style.display = 'flex';

      showConnectionBanner();
    }
  }

  function showConnectionBanner() {
    elements.connectionBanner.classList.add('visible');

    if (!state.retryTimer) {
      state.retrySecondsLeft = 5;
      updateCountdownUI();

      state.retryTimer = setInterval(() => {
        state.retrySecondsLeft--;
        updateCountdownUI();

        if (state.retrySecondsLeft <= 0) {
          clearInterval(state.retryTimer);
          state.retryTimer = null;
          triggerManualRetry();
        }
      }, 1000);
    }
  }

  function updateCountdownUI() {
    elements.retryCountdown.textContent = state.retrySecondsLeft;
  }

  function triggerManualRetry() {
    elements.bannerText.innerHTML = '⚡ Checking connection...';
    checkNetworkStatus().then(() => {
      if (!state.isOnline) {
        state.retryCount++;
        const backoffSeconds = Math.min(30, 5 * Math.pow(1.5, state.retryCount - 1));
        state.retrySecondsLeft = Math.round(backoffSeconds);
        elements.bannerText.innerHTML = `Connection failed. Auto-retrying in <strong id="retry-countdown">${state.retrySecondsLeft}</strong>s...`;
        elements.retryCountdown = document.getElementById('retry-countdown');
      }
    });
  }

  // --- 3. DOWNLOAD & CACHE PROGRESS MANAGER ---
  function setupDownloadManager() {
    renderDownloads();

    elements.btnAddTestDl.addEventListener('click', () => simulateNewDownload());
    elements.btnClearDownloads.addEventListener('click', () => clearDownloads());
  }

  function renderDownloads() {
    elements.downloadList.innerHTML = '';

    let totalSizeMB = 0;
    let completedCount = 0;
    let currentSpeedSum = 0;
    let totalProgressSum = 0;

    state.downloads.forEach(item => {
      const sizeVal = parseFloat(item.size);
      totalSizeMB += (item.progress / 100) * sizeVal;
      totalProgressSum += item.progress;

      if (item.status === 'completed') completedCount++;

      const card = document.createElement('div');
      card.className = 'download-item';
      card.innerHTML = `
        <div class="download-item-info">
          <span class="item-title">${item.title}</span>
          <span class="item-sub">${item.size} • ${item.speed}</span>
          <div class="progress-bar-container" style="margin-top: 6px; height: 6px;">
            <div class="progress-fill" style="width: ${item.progress}%;"></div>
          </div>
        </div>
        <span class="item-status-badge ${item.status}">${item.status.toUpperCase()}</span>
      `;
      elements.downloadList.appendChild(card);
    });

    const overallProgress = state.downloads.length > 0 
      ? Math.round(totalProgressSum / state.downloads.length) 
      : 100;

    elements.dlTotalCount.textContent = completedCount;
    elements.dlTotalSize.textContent = `${totalSizeMB.toFixed(1)} MB`;
    elements.dlProgressPercent.textContent = `${overallProgress}%`;
    elements.dlProgressFill.style.width = `${overallProgress}%`;
  }

  function simulateNewDownload() {
    const trackNames = [
      'High-Resolution Audio Cache Segment #',
      'Spotify Desktop Web Bundle Asset v',
      'Widevine Key Preload Module #',
      'Album Art & Metadata Cache Cluster #'
    ];
    const randomTrack = trackNames[Math.floor(Math.random() * trackNames.length)] + Math.floor(Math.random() * 90 + 10);
    const randomSize = (Math.random() * 12 + 3).toFixed(1) + ' MB';

    const newDownload = {
      id: 'dl-' + Date.now(),
      title: randomTrack,
      size: randomSize,
      progress: 0,
      status: 'downloading',
      speed: '1.2 MB/s'
    };

    state.downloads.unshift(newDownload);
    renderDownloads();

    // Animate Progress
    const interval = setInterval(() => {
      newDownload.progress += Math.floor(Math.random() * 15 + 10);
      newDownload.speed = (Math.random() * 2 + 0.8).toFixed(1) + ' MB/s';

      if (newDownload.progress >= 100) {
        newDownload.progress = 100;
        newDownload.status = 'completed';
        newDownload.speed = '0 KB/s';
        clearInterval(interval);
      }
      renderDownloads();
    }, 400);
  }

  function clearDownloads() {
    state.downloads = [];
    renderDownloads();
  }

  // --- 4. SPOTIFY HEALTH & STATUS DASHBOARD ---
  function setupStatusDashboard() {
    const defaultServices = [
      { name: 'Client Token Provider', role: 'Web Client Authorization Engine', sub: 'clienttoken.spotify.com/v1/clienttoken', code: 204, ms: 142 },
      { name: 'Auth Server', role: 'OAuth2 & Login Authority', sub: 'accounts.spotify.com', code: 200, ms: 98 },
      { name: 'REST API Service', role: 'Catalog, Playlists & Metadata', sub: 'api.spotify.com/v1/', code: 200, ms: 115 },
      { name: 'DRM License Server', role: 'Widevine L3 Certificate Authority', sub: 'spclient.wg.spotify.com', code: 200, ms: 185 },
      { name: 'Web Player Edge CDN', role: 'Web App & Audio Streaming CDN', sub: 'open.spotify.com', code: 200, ms: 64 }
    ];

    renderServiceCards(defaultServices);

    elements.btnRefreshStatus.addEventListener('click', () => {
      elements.btnRefreshStatus.classList.add('loading');
      setTimeout(() => {
        defaultServices.forEach(s => {
          s.ms = Math.floor(Math.random() * 100 + 50);
        });
        renderServiceCards(defaultServices);
        renderStatusChart();
        elements.btnRefreshStatus.classList.remove('loading');
      }, 600);
    });
  }

  function renderServiceCards(services) {
    elements.servicesList.innerHTML = '';
    services.forEach(s => {
      const card = document.createElement('div');
      card.className = 'service-card';
      const isErr = s.code >= 400 || s.code === 0;
      card.innerHTML = `
        <div class="service-meta-col">
          <span class="service-name">${s.name}</span>
          <span class="service-endpoint">${s.sub}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="badge-code ${isErr ? 'err' : ''}">${s.code === 204 || s.code === 200 ? 'HTTP ' + s.code : 'HTTP ' + s.code}</span>
          <span style="font-family: var(--font-code); font-size: 0.8rem; color: var(--text-dim);">${s.ms}ms</span>
        </div>
      `;
      elements.servicesList.appendChild(card);
    });
  }

  function renderStatusChart() {
    const canvas = document.getElementById('statusChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (state.chartInstance) {
      state.chartInstance.destroy();
    }

    const labels = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', 'Now'];
    
    state.chartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          { label: 'Token Service (ms)', data: [120, 140, 110, 155, 130, 145, 142], borderColor: '#1DB954', borderWidth: 2, tension: 0.3 },
          { label: 'Auth Authority (ms)', data: [90, 95, 105, 110, 92, 100, 98], borderColor: '#3b82f6', borderWidth: 2, tension: 0.3 },
          { label: 'DRM License (ms)', data: [160, 175, 190, 180, 165, 195, 185], borderColor: '#f59e0b', borderWidth: 2, tension: 0.3 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#a1a1aa', font: { family: 'Outfit', size: 11 } } }
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#71717a' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#71717a' } }
        }
      }
    });
  }

  // --- 5. PWA SERVICE WORKER REGISTRATION ---
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js')
        .then(reg => console.log('[SpotiDuck] Service Worker Registered:', reg.scope))
        .catch(err => console.warn('[SpotiDuck] Service Worker Registration failed:', err));
    }
  }

  // Run App Engine
  document.addEventListener('DOMContentLoaded', init);

})();
