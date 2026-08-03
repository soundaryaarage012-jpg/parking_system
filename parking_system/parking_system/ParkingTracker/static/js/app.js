document.addEventListener('DOMContentLoaded', () => {
  const pageLoader = document.getElementById('pageLoader');
  requestAnimationFrame(() => {
    pageLoader?.classList.add('done');
  });

  const toggle = document.getElementById('themeToggle');
  const root = document.documentElement;
  const stored = window.localStorage.getItem('parking-theme');
  const initialTheme = stored || 'dark';
  root.setAttribute('data-theme', initialTheme);
  updateThemeIcon(initialTheme);

  if (toggle) {
    toggle.addEventListener('click', () => {
      const nextTheme = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', nextTheme);
      window.localStorage.setItem('parking-theme', nextTheme);
      updateThemeIcon(nextTheme);
    });
  }

  applyMagneticCtas();
  animateCounters();
  initLiveUpdates();
  initCityStatusBar();
  initPredictionPolling();
  initDemoModeToggle();
  initAiIntentButtons();
  initQRScanner();
  initAiRecommendationTicker();
});

function updateThemeIcon(theme) {
  const icon = document.querySelector('#themeToggle i');
  if (!icon) return;
  icon.className = theme === 'dark' ? 'bi bi-brightness-high' : 'bi bi-moon-stars-fill';
}

function applyMagneticCtas() {
  document.querySelectorAll('.magnetic-button, .cta-button, .secondary-button').forEach((button) => {
    button.addEventListener('pointermove', (event) => {
      const rect = button.getBoundingClientRect();
      const offsetX = event.clientX - rect.left - rect.width / 2;
      const offsetY = event.clientY - rect.top - rect.height / 2;
      button.style.transform = `translate(${offsetX * 0.12}px, ${offsetY * 0.12}px)`;
    });

    button.addEventListener('pointerleave', () => {
      button.style.transform = '';
    });

    button.addEventListener('click', (event) => {
      const ripple = document.createElement('span');
      const rect = button.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
      ripple.className = 'ripple';
      button.appendChild(ripple);
      setTimeout(() => ripple.remove(), 500);
    });
  });
}

function animateCounters() {
  const counters = document.querySelectorAll('.count-up');
  counters.forEach((counter) => {
    const target = Number(counter.dataset.target || 0);
    const duration = 1200;
    const step = (timestamp) => {
      if (!counter.startTime) counter.startTime = timestamp;
      const progress = Math.min((timestamp - counter.startTime) / duration, 1);
      counter.textContent = Math.floor(progress * target);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        counter.textContent = target;
      }
    };
    window.requestAnimationFrame(step);
  });
}

function initAiRecommendationTicker() {
  const textNode = document.getElementById('aiRecommendationText');
  if (!textNode) return;

  const recommendations = [
    'Zone B has 12 free slots, 90s from entrance.',
    'Fastest path is via Gate C with 6 open bays nearby.',
    'EV lane is ideal for low-range vehicles this hour.',
    'North deck has 9 premium spaces and a 48s walk.',
  ];

  let index = 0;
  setInterval(() => {
    index = (index + 1) % recommendations.length;
    textNode.textContent = recommendations[index];
  }, 4200);
}

function updatePredictionLine(payload) {
  const predictionLine = document.getElementById('predictionLine');
  if (!predictionLine) return;
  const zones = payload?.zones || [];
  if (!zones.length) return;
  const topZone = zones[0];
  predictionLine.textContent = `${topZone.name} expected to fill in ~${topZone.eta_minutes} min`;
}

function initPredictionPolling() {
  if (!document.getElementById('predictionLine')) return;
  const syncPrediction = () => {
    fetch('/api/predictions')
      .then((response) => response.json())
      .then((payload) => updatePredictionLine(payload))
      .catch(() => {});
  };
  syncPrediction();
  window.setInterval(syncPrediction, 8000);
}

function initCityStatusBar() {
  const statusBar = document.getElementById('smartCityStatusBar');
  if (!statusBar) return;

  const syncStatus = (payload) => {
    const status = payload && payload.status ? payload.status : payload || {};
    if (!status || typeof status !== 'object') return;

    statusBar.querySelectorAll('[data-status-key]').forEach((node) => {
      const key = node.dataset.statusKey;
      const ev = status.ev_chargers || {};

      if (key === 'ev_available') {
        node.textContent = `${ev.available ?? 0}/${ev.total ?? 0}`;
        return;
      }

      if (typeof status[key] === 'undefined') return;

      const val = status[key];
      if (key === 'co2_saved') {
        node.textContent = `${val}kg`;
        return;
      }

      if (key === 'average_search_time') {
        node.textContent = `${Number(val).toFixed(1)}m`;
        return;
      }

      if (key === 'occupancy_pct') {
        node.textContent = `${val}%`;
        return;
      }

      node.textContent = String(val);
    });
  };

  fetch('/api/city/status')
    .then((response) => response.json())
    .then(syncStatus)
    .catch(() => {});
}

function initDemoModeToggle() {
  const button = document.getElementById('demoModeToggle');
  if (!button) return;

  let demoMode = false;
  const icon = button.querySelector('i');

  const setDemoState = (enabled) => {
    demoMode = enabled;
    button.classList.toggle('active', enabled);
    if (icon) {
      icon.className = enabled ? 'bi bi-pause-circle-fill' : 'bi bi-play-circle-fill';
    }
  };

  button.addEventListener('click', async () => {
    const nextState = !demoMode;
    setDemoState(nextState);
    try {
      const response = await fetch('/api/demo/state');
      const payload = await response.json();
      const status = payload && payload.status ? payload.status : {};
      if (typeof status.available_slots !== 'undefined') {
        const statusBar = document.getElementById('smartCityStatusBar');
        statusBar?.querySelectorAll('[data-status-key]').forEach((node) => {
          const key = node.dataset.statusKey;
          if (key === 'ev_available') {
            node.textContent = `${status.ev_chargers?.available ?? 0}/${status.ev_chargers?.total ?? 0}`;
            return;
          }
          if (status[key] !== undefined) {
            const value = key === 'co2_saved' ? `${status[key]}kg` : key === 'average_search_time' ? `${Number(status[key]).toFixed(1)}m` : key === 'occupancy_pct' ? `${status[key]}%` : String(status[key]);
            node.textContent = value;
          }
        });
      }
    } catch (error) {
      setDemoState(false);
    }
  });
}

function initAiIntentButtons() {
  const buttons = document.querySelectorAll('.ai-intent-btn');
  if (!buttons.length) return;

  const recommendationBox = document.getElementById('aiRecommendationBox');
  const recommendationSummary = document.getElementById('aiRecommendationSummary');
  const timeline = document.getElementById('aiDecisionTimeline');

  const updateTimeline = (index) => {
    if (!timeline) return;
    Array.from(timeline.children).forEach((step, stepIndex) => {
      step.classList.toggle('active', stepIndex <= index);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener('click', async () => {
      const intent = button.dataset.intent;
      updateTimeline(0);

      try {
        const response = await fetch('/api/ai/recommendation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ intent })
        });
        const payload = await response.json();
        updateTimeline(3);

        if (recommendationBox) {
          recommendationBox.innerHTML = `
            <strong>${payload.message || 'Recommendation ready.'}</strong>
            <div class="mt-2 small text-muted">Confidence ${payload.confidence || 0}% • Parking score ${payload.parking_score || 0}/100</div>
          `;
        }

        if (recommendationSummary && payload.recommended_slot) {
          const slot = payload.recommended_slot;
          recommendationSummary.innerHTML = `
            <span class="eyebrow">Recommended slot</span>
            <h3 class="fw-bold mb-3">${slot.slot_number}</h3>
            <div class="assistant-metrics">
              <div><span>Floor</span><strong>${slot.floor || 'N/A'}</strong></div>
              <div><span>Status</span><strong>${slot.status || 'available'}</strong></div>
              <div><span>Distance</span><strong>${slot.distance_from_entrance || 0}m</strong></div>
            </div>
          `;
        }
      } catch (error) {
        if (recommendationBox) {
          recommendationBox.innerHTML = '<strong>Unable to load a recommendation right now.</strong>';
        }
      }
    });
  });
}

function initLiveUpdates() {
  if (!window.io) return;
  const banner = document.getElementById('liveUpdateBanner');
  const stats = document.querySelectorAll('[data-stat-key]');
  if (!banner || !stats.length) return;

  const socket = io();
  socket.on('connect', () => {
    banner.textContent = 'Live parking updates enabled.';
    banner.classList.add('alert-success');
  });

  socket.on('parking_update', (payload) => {
    banner.textContent = payload.message || 'Parking data updated.';
    banner.classList.remove('alert-secondary');
    banner.classList.add('alert-info');

    stats.forEach((el) => {
      const key = el.dataset.statKey;
      if (payload.stats && typeof payload.stats[key] !== 'undefined') {
        el.textContent = payload.stats[key];
      }
    });
  });
}

function initQRScanner() {
  const video = document.getElementById('qrVideo');
  const canvas = document.getElementById('qrCanvas');
  const message = document.getElementById('qrMessage');
  const startButton = document.getElementById('startScan');

  if (!video || !canvas || !message || !startButton) return;
  const context = canvas.getContext('2d');
  let activeStream = null;
  let scanning = false;

  const stopScanning = () => {
    scanning = false;
    if (activeStream) {
      activeStream.getTracks().forEach((track) => track.stop());
      activeStream = null;
    }
    message.textContent = 'Scanner stopped. Press start to scan again.';
  };

  const handleFrame = () => {
    if (!scanning) return;
    if (video.readyState === video.HAVE_ENOUGH_DATA) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
      if (window.jsQR) {
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        if (code) {
          message.textContent = `QR code found: ${code.data}`;
          if (code.data.includes('/parking/')) {
            window.location.href = code.data;
            return;
          }
        } else {
          message.textContent = 'Point the camera at a parking QR code.';
        }
      }
    }
    requestAnimationFrame(handleFrame);
  };

  startButton.addEventListener('click', async () => {
    if (scanning) {
      stopScanning();
      startButton.textContent = 'Start Scanner';
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      activeStream = stream;
      video.srcObject = stream;
      await video.play();
      scanning = true;
      startButton.textContent = 'Stop Scanner';
      message.textContent = 'Scanning for QR codes...';
      requestAnimationFrame(handleFrame);
    } catch (error) {
      message.textContent = 'Camera access denied or unavailable. Please allow camera permissions.';
    }
  });
}

const rippleCSS = `
  .ripple {
    position: absolute;
    border-radius: 50%;
    transform: scale(0);
    background: rgba(255,255,255,0.45);
    animation: ripple 0.52s ease-out;
    pointer-events: none;
  }

  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;

const styleTag = document.createElement('style');
styleTag.textContent = rippleCSS;
document.head.appendChild(styleTag);
