// =========================================================================
// WhatsApp Chat Viewer Application Scripts (High-Performance Engine)
// =========================================================================

(function() {
  'use strict';

  // -------------------------------------------------------------------------
  // Utility: Debounce for smooth typing without lag
  // -------------------------------------------------------------------------
  function debounce(fn, delay) {
    let timer = null;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // -------------------------------------------------------------------------
  // High-Performance Search without destroying the DOM
  // -------------------------------------------------------------------------
  const chatContainer = document.getElementById('chat-container');
  const searchInput   = document.getElementById('search-input');
  const searchCount   = document.getElementById('search-count');
  const btnPrev       = document.getElementById('search-prev');
  const btnNext       = document.getElementById('search-next');

  let searchMatches   = [];
  let currentMatchIdx = -1;

  // Clear all previous highlight marks cleanly without resetting audio/video or innerHTML
  function clearHighlights() {
    if (!chatContainer) return;
    const marks = chatContainer.querySelectorAll('mark.wa-highlight');
    for (let i = 0; i < marks.length; i++) {
      const mark = marks[i];
      const parent = mark.parentNode;
      if (parent) {
        parent.replaceChild(document.createTextNode(mark.textContent), mark);
        parent.normalize();
      }
    }
  }

  function clearSearch() {
    clearHighlights();
    searchMatches = [];
    currentMatchIdx = -1;
    if (searchCount) searchCount.textContent = '';
    if (btnPrev) btnPrev.disabled = true;
    if (btnNext) btnNext.disabled = true;

    if (chatContainer) {
      chatContainer.querySelectorAll('.search-hidden').forEach(el => {
        el.classList.remove('search-hidden');
      });
    }
  }

  function highlightTextNode(node, regex) {
    const text = node.nodeValue;
    let match = regex.exec(text);
    if (!match) return;

    const fragment = document.createDocumentFragment();
    let lastIndex = 0;

    do {
      const matchIndex = match.index;
      const matchedText = match[0];

      if (matchIndex > lastIndex) {
        fragment.appendChild(document.createTextNode(text.substring(lastIndex, matchIndex)));
      }

      const mark = document.createElement('mark');
      mark.className = 'wa-highlight';
      mark.textContent = matchedText;
      fragment.appendChild(mark);

      lastIndex = matchIndex + matchedText.length;
    } while ((match = regex.exec(text)) !== null);

    if (lastIndex < text.length) {
      fragment.appendChild(document.createTextNode(text.substring(lastIndex)));
    }

    node.parentNode.replaceChild(fragment, node);
  }

  function highlightInElement(element, regex) {
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function(node) {
          if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          if (node.parentNode && node.parentNode.tagName === 'MARK') return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      }
    );

    const textNodes = [];
    while (walker.nextNode()) {
      textNodes.push(walker.currentNode);
    }

    for (let i = 0; i < textNodes.length; i++) {
      highlightTextNode(textNodes[i], regex);
    }
  }

  // -------------------------------------------------------------------------
  // Offscreen Web Worker Search Engine (zero frame drops during typing)
  // -------------------------------------------------------------------------
  let searchWorker = null;
  let textIndex = null;

  try {
    const workerBlob = new Blob([`
      let index = [];
      self.onmessage = function(e) {
        if (e.data.action === 'init') {
          index = e.data.items || [];
        } else if (e.data.action === 'search') {
          const q = (e.data.query || '').toLowerCase();
          const matches = [];
          if (q) {
            for (let i = 0; i < index.length; i++) {
              if (index[i].text.includes(q)) {
                matches.push(index[i].id);
              }
            }
          }
          self.postMessage({ action: 'result', query: e.data.query, matchIds: matches });
        }
      };
    `], { type: 'application/javascript' });
    searchWorker = new Worker(URL.createObjectURL(workerBlob));
    searchWorker.onmessage = function(e) {
      if (e.data.action === 'result') {
        applySearchResults(e.data.query, e.data.matchIds);
      }
    };
  } catch (err) {
    searchWorker = null;
  }

  function buildTextIndex() {
    if (textIndex || !chatContainer) return;
    textIndex = [];
    const subMessages = chatContainer.querySelectorAll('.sub-message');
    for (let i = 0; i < subMessages.length; i++) {
      const sm = subMessages[i];
      const textEl = sm.querySelector('.text');
      if (textEl && sm.id) {
        textIndex.push({ id: sm.id, text: textEl.textContent.toLowerCase() });
      }
    }
    if (searchWorker && textIndex.length > 0) {
      searchWorker.postMessage({ action: 'init', items: textIndex });
    }
  }

  if (window.requestIdleCallback) {
    requestIdleCallback(buildTextIndex);
  } else {
    setTimeout(buildTextIndex, 300);
  }

  function applySearchResults(q, matchIds) {
    clearHighlights();
    searchMatches = [];
    currentMatchIdx = -1;

    if (!q) {
      clearSearch();
      return;
    }

    const regex = new RegExp('(' + escapeRegex(q) + ')', 'gi');
    const matchingRows = new Set();
    const idSet = new Set(matchIds);

    for (let i = 0; i < matchIds.length; i++) {
      const sm = document.getElementById(matchIds[i]);
      if (sm) {
        const textEl = sm.querySelector('.text');
        if (textEl) highlightInElement(textEl, regex);
        const row = sm.closest('.message-row');
        if (row) matchingRows.add(row);
      }
    }

    // Hide / show message rows
    const rows = chatContainer.querySelectorAll('.message-row');
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      row.classList.toggle('search-hidden', !matchingRows.has(row));
    }

    // Hide / show day-groups
    const dayGroups = chatContainer.querySelectorAll('.day-group');
    for (let i = 0; i < dayGroups.length; i++) {
      const dg = dayGroups[i];
      const hasVisible = !!dg.querySelector('.message-row:not(.search-hidden)');
      dg.classList.toggle('search-hidden', !hasVisible);
    }

    // Hide / show standalone date separators if any
    const separators = chatContainer.querySelectorAll('.date-separator');
    for (let i = 0; i < separators.length; i++) {
      const sep = separators[i];
      let next = sep.nextElementSibling;
      let hasVisibleChild = false;
      while (next && !next.classList.contains('date-separator')) {
        if (!next.classList.contains('search-hidden')) {
          hasVisibleChild = true;
          break;
        }
        next = next.nextElementSibling;
      }
      sep.classList.toggle('search-hidden', !hasVisibleChild);
    }

    // Collect matches
    searchMatches = Array.from(chatContainer.querySelectorAll('mark.wa-highlight'));
    if (btnPrev) btnPrev.disabled = (searchMatches.length === 0);
    if (btnNext) btnNext.disabled = (searchMatches.length === 0);

    if (searchMatches.length > 0) {
      goToMatch(0);
    } else {
      if (searchCount) searchCount.textContent = 'Aucun résultat';
    }
  }

  function runSearch(query) {
    const q = query ? query.trim() : '';
    if (!q) {
      clearSearch();
      return;
    }

    if (searchWorker && textIndex && textIndex.length > 0) {
      searchWorker.postMessage({ action: 'search', query: q });
      return;
    }

    // Fast synchronous fallback
    clearHighlights();
    searchMatches = [];
    currentMatchIdx = -1;

    const qLower = q.toLowerCase();
    const regex = new RegExp('(' + escapeRegex(q) + ')', 'gi');

    const matchingRows = new Set();
    const textEls = chatContainer.querySelectorAll('.sub-message .text');
    for (let i = 0; i < textEls.length; i++) {
      const el = textEls[i];
      if (el.textContent.toLowerCase().includes(qLower)) {
        highlightInElement(el, regex);
        const row = el.closest('.message-row');
        if (row) matchingRows.add(row);
      }
    }

    const rows = chatContainer.querySelectorAll('.message-row');
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      row.classList.toggle('search-hidden', !matchingRows.has(row));
    }

    const dayGroups = chatContainer.querySelectorAll('.day-group');
    for (let i = 0; i < dayGroups.length; i++) {
      const dg = dayGroups[i];
      const hasVisible = !!dg.querySelector('.message-row:not(.search-hidden)');
      dg.classList.toggle('search-hidden', !hasVisible);
    }

    const separators = chatContainer.querySelectorAll('.date-separator');
    for (let i = 0; i < separators.length; i++) {
      const sep = separators[i];
      let next = sep.nextElementSibling;
      let hasVisibleChild = false;
      while (next && !next.classList.contains('date-separator')) {
        if (!next.classList.contains('search-hidden')) {
          hasVisibleChild = true;
          break;
        }
        next = next.nextElementSibling;
      }
      sep.classList.toggle('search-hidden', !hasVisibleChild);
    }

    searchMatches = Array.from(chatContainer.querySelectorAll('mark.wa-highlight'));
    if (btnPrev) btnPrev.disabled = (searchMatches.length === 0);
    if (btnNext) btnNext.disabled = (searchMatches.length === 0);

    if (searchMatches.length > 0) {
      goToMatch(0);
    } else {
      if (searchCount) searchCount.textContent = 'Aucun résultat';
    }
  }

  function goToMatch(idx) {
    if (!searchMatches.length) return;
    for (let i = 0; i < searchMatches.length; i++) {
      searchMatches[i].classList.remove('match-active');
    }
    currentMatchIdx = ((idx % searchMatches.length) + searchMatches.length) % searchMatches.length;
    const active = searchMatches[currentMatchIdx];
    active.classList.add('match-active');
    active.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (searchCount) {
      searchCount.textContent = (currentMatchIdx + 1) + ' / ' + searchMatches.length;
    }
  }

  if (searchInput) {
    // 200ms debounce ensures fluid typing without freezing on large datasets
    const debouncedSearch = debounce(val => runSearch(val), 200);

    searchInput.addEventListener('input', e => {
      debouncedSearch(e.target.value);
    });

    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        goToMatch(e.shiftKey ? currentMatchIdx - 1 : currentMatchIdx + 1);
      }
      if (e.key === 'Escape') {
        searchInput.value = '';
        clearSearch();
      }
    });
  }

  if (btnPrev) btnPrev.addEventListener('click', () => goToMatch(currentMatchIdx - 1));
  if (btnNext) btnNext.addEventListener('click', () => goToMatch(currentMatchIdx + 1));

  // -------------------------------------------------------------------------
  // Lightbox with Zoom & Pan
  // -------------------------------------------------------------------------
  const lightbox    = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightbox-img');
  const lbImgWrap   = document.getElementById('lb-img-wrap');
  let lbImages = [];
  let lbIdx    = 0;
  let lbScale  = 1;
  let lbPanX   = 0;
  let lbPanY   = 0;
  let lbDragging   = false;
  let lbDragStartX = 0;
  let lbDragStartY = 0;
  let lbPanStartX  = 0;
  let lbPanStartY  = 0;

  function lbUpdateTransform() {
    if (!lightboxImg) return;
    lightboxImg.style.transform = 'translate(' + lbPanX + 'px, ' + lbPanY + 'px) scale(' + lbScale + ')';
    const label = document.getElementById('lb-zoom-label');
    if (label) label.textContent = Math.round(lbScale * 100) + '%';
  }

  function lbResetZoom() {
    lbScale = 1; lbPanX = 0; lbPanY = 0;
    lbUpdateTransform();
  }

  function lbZoom(delta, cx, cy) {
    const wrap = lbImgWrap;
    const factor = delta > 0 ? 1.2 : 0.85;
    const newScale = Math.min(8, Math.max(0.5, lbScale * factor));
    if (wrap && cx !== undefined && cy !== undefined) {
      const rect = wrap.getBoundingClientRect();
      const ox = cx - rect.left - rect.width / 2;
      const oy = cy - rect.top - rect.height / 2;
      lbPanX = ox - (ox - lbPanX) * (newScale / lbScale);
      lbPanY = oy - (oy - lbPanY) * (newScale / lbScale);
    }
    lbScale = newScale;
    lbUpdateTransform();
  }

  const lbVideo     = document.getElementById('lightbox-video');
  const lbFullscreen= document.getElementById('lb-fullscreen');

  function attachImageListeners() {
    // Handled via high-performance event delegation on chatContainer
  }

  if (chatContainer) {
    chatContainer.addEventListener('click', function(e) {
      const img = e.target.closest('.media-img');
      if (img) openLightbox(img);
    });
  }

  function toggleLightboxFullscreen() {
    if (!document.fullscreenElement) {
      if (lightbox && lightbox.requestFullscreen) {
        lightbox.requestFullscreen();
      } else if (lightbox && lightbox.webkitRequestFullscreen) {
        lightbox.webkitRequestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      }
    }
  }

  function openLightbox(img) {
    if (!lightbox || !lightboxImg) return;
    if (lbVideo) {
      lbVideo.pause();
      lbVideo.src = '';
      lbVideo.style.display = 'none';
    }
    lightboxImg.style.display = 'block';
    const zoomControls = [lbZoomIn, lbZoomOut, lbZoomReset, document.getElementById('lb-zoom-label')];
    zoomControls.forEach(el => { if (el) el.style.display = ''; });

    lbImages = Array.from(document.querySelectorAll('.media-img'));
    lbIdx = lbImages.indexOf(img);
    lightboxImg.src = img.src;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
    lbResetZoom();
  }

  window.openLightboxVideo = function(videoSrc) {
    if (!lightbox || !lbVideo) return;
    if (lightboxImg) lightboxImg.style.display = 'none';
    lbVideo.style.display = 'block';
    lbVideo.src = videoSrc;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
    const zoomControls = [lbZoomIn, lbZoomOut, lbZoomReset, document.getElementById('lb-zoom-label')];
    zoomControls.forEach(el => { if (el) el.style.display = 'none'; });
    lbVideo.play().catch(() => {});
  };

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
    if (lbVideo) {
      lbVideo.pause();
      lbVideo.src = '';
      lbVideo.style.display = 'none';
    }
    if (lightboxImg) lightboxImg.style.display = 'block';
    const zoomControls = [lbZoomIn, lbZoomOut, lbZoomReset, document.getElementById('lb-zoom-label')];
    zoomControls.forEach(el => { if (el) el.style.display = ''; });
    lbResetZoom();
  }

  function lbMove(delta) {
    if (!lbImages.length || !lightboxImg) return;
    lbIdx = ((lbIdx + delta + lbImages.length) % lbImages.length);
    lightboxImg.src = lbImages[lbIdx].src;
    lbResetZoom();
  }

  const lbClose     = document.getElementById('lb-close');
  const lbPrev      = document.getElementById('lb-prev');
  const lbNext      = document.getElementById('lb-next');
  const lbZoomIn    = document.getElementById('lb-zoom-in');
  const lbZoomOut   = document.getElementById('lb-zoom-out');
  const lbZoomReset = document.getElementById('lb-zoom-reset');

  if (lbClose)      lbClose.addEventListener('click', closeLightbox);
  if (lbPrev)       lbPrev.addEventListener('click', () => lbMove(-1));
  if (lbNext)       lbNext.addEventListener('click', () => lbMove(1));
  if (lbZoomIn)     lbZoomIn.addEventListener('click', () => lbZoom(1));
  if (lbZoomOut)    lbZoomOut.addEventListener('click', () => lbZoom(-1));
  if (lbZoomReset)  lbZoomReset.addEventListener('click', lbResetZoom);
  if (lbFullscreen) lbFullscreen.addEventListener('click', toggleLightboxFullscreen);

  if (lightbox) {
    lightbox.addEventListener('click', e => {
      if (e.target === lightbox || e.target === lbImgWrap) closeLightbox();
    });
  }

  // Double-click to zoom / reset
  if (lightboxImg) {
    lightboxImg.addEventListener('dblclick', e => {
      e.preventDefault();
      if (lbScale > 1) {
        lbResetZoom();
      } else {
        lbZoom(1, e.clientX, e.clientY);
      }
    });
  }

  // Mouse wheel zoom in lightbox
  if (lbImgWrap) {
    lbImgWrap.addEventListener('wheel', e => {
      if (!lightbox || !lightbox.classList.contains('active')) return;
      if (lightboxImg.style.display === 'none') return; // Don't zoom video
      e.preventDefault();
      lbZoom(-e.deltaY, e.clientX, e.clientY);
    }, { passive: false });

    // Pan via mouse drag
    lbImgWrap.addEventListener('mousedown', e => {
      if (lbScale <= 1) return;
      lbDragging = true;
      lbDragStartX = e.clientX;
      lbDragStartY = e.clientY;
      lbPanStartX = lbPanX;
      lbPanStartY = lbPanY;
      lbImgWrap.classList.add('grabbing');
    });
    document.addEventListener('mousemove', e => {
      if (!lbDragging) return;
      lbPanX = lbPanStartX + (e.clientX - lbDragStartX);
      lbPanY = lbPanStartY + (e.clientY - lbDragStartY);
      lbUpdateTransform();
    });
    document.addEventListener('mouseup', () => {
      if (lbDragging) { lbDragging = false; lbImgWrap.classList.remove('grabbing'); }
    });
  }

  document.addEventListener('keydown', e => {
    if (!lightbox || !lightbox.classList.contains('active')) return;
    if (e.key === 'Escape')     closeLightbox();
    if (e.key === 'ArrowLeft')  lbMove(-1);
    if (e.key === 'ArrowRight') lbMove(1);
    if (e.key === '+' || e.key === '=') lbZoom(1);
    if (e.key === '-')          lbZoom(-1);
    if (e.key === '0')          lbResetZoom();
    if (e.key === 'f' || e.key === 'F') toggleLightboxFullscreen();
  });

  attachImageListeners();

  // -------------------------------------------------------------------------
  // Audio playback speed (1x -> 1.5x -> 2x -> 1x)
  // -------------------------------------------------------------------------
  window.toggleAudioSpeed = function(btn) {
    const container = btn.closest('.audio-container');
    const audio = container ? container.querySelector('audio') : null;
    if (!audio) return;

    const speeds = [1, 1.5, 2];
    const currentSpeed = parseFloat(audio.dataset.speed || audio.playbackRate || 1);
    let nextIdx = speeds.findIndex(s => Math.abs(s - currentSpeed) < 0.05) + 1;
    if (nextIdx >= speeds.length || nextIdx < 0) nextIdx = 0;
    const newSpeed = speeds[nextIdx];

    audio.dataset.speed = newSpeed;
    audio.playbackRate = newSpeed;
    btn.dataset.speed = newSpeed;
    btn.textContent = (newSpeed % 1 === 0 ? newSpeed.toFixed(0) : newSpeed.toString()) + 'x';
    btn.classList.toggle('speed-boosted', newSpeed > 1);
  };

  // -------------------------------------------------------------------------
  // Singleton Audio Manager (coordinates single active playback, zero pipeline leaks)
  // -------------------------------------------------------------------------
  let activeAudio = null;

  document.addEventListener('play', function(e) {
    if (e.target && e.target.tagName === 'AUDIO') {
      const audio = e.target;
      if (activeAudio && activeAudio !== audio) {
        activeAudio.pause();
      }
      activeAudio = audio;
      const sp = parseFloat(audio.dataset.speed || 1);
      if (sp && sp !== 1) {
        audio.playbackRate = sp;
      }
    }
  }, true);

  document.addEventListener('pause', function(e) {
    if (e.target && e.target === activeAudio) {
      activeAudio = null;
    }
  }, true);

  // Delegated handler for speed buttons and fullscreen video buttons
  if (chatContainer) {
    chatContainer.addEventListener('click', function(e) {
      const speedBtn = e.target.closest('.audio-speed-btn');
      if (speedBtn) {
        toggleAudioSpeed(speedBtn);
        return;
      }
      const fsBtn = e.target.closest('.video-fs-btn');
      if (fsBtn) {
        const vid = fsBtn.previousElementSibling;
        if (vid && vid.requestFullscreen) vid.requestFullscreen();
        return;
      }
    });
  }

  // -------------------------------------------------------------------------
  // Dark Mode Management
  // -------------------------------------------------------------------------
  const themeToggleBtn = document.getElementById('theme-toggle');
  const themeIcon      = document.getElementById('theme-icon');

  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme, save) {
    if (save) {
      localStorage.setItem('wa_theme', theme);
    }
    const isDark = (theme === 'dark');
    document.body.classList.toggle('dark-mode', isDark);
    document.body.classList.toggle('light-mode', !isDark);
    if (themeIcon) {
      themeIcon.textContent = isDark ? '☀️' : '🌙';
    }
    if (themeToggleBtn) {
      themeToggleBtn.title = isDark ? 'Passer au mode clair' : 'Passer au mode sombre';
    }
  }

  const savedTheme = localStorage.getItem('wa_theme');
  if (savedTheme === 'dark' || savedTheme === 'light') {
    applyTheme(savedTheme, false);
  } else {
    applyTheme(getSystemTheme(), false);
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if (!localStorage.getItem('wa_theme')) {
      applyTheme(e.matches ? 'dark' : 'light', false);
    }
  });

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const isCurrentlyDark = document.body.classList.contains('dark-mode') ||
        (!document.body.classList.contains('light-mode') && getSystemTheme() === 'dark');
      applyTheme(isCurrentlyDark ? 'light' : 'dark', true);
    });
  }

  // -------------------------------------------------------------------------
  // "Me" vs "Others" (Right / Left alignment switcher)
  // -------------------------------------------------------------------------
  let currentMeUser = '';
  let dynamicMeStyle = null;

  window.setMeUser = function(userName) {
    currentMeUser = userName ? userName.trim() : '';
    if (currentMeUser) {
      localStorage.setItem('wa_me_user', currentMeUser);
    } else {
      localStorage.removeItem('wa_me_user');
    }

    const select = document.getElementById('me-select');
    if (select && select.value !== currentMeUser) {
      select.value = currentMeUser;
    }

    document.querySelectorAll('.legend-item').forEach(item => {
      const s = item.getAttribute('data-sender') || '';
      const isSelected = currentMeUser && s === currentMeUser;
      item.classList.toggle('legend-active-me', isSelected);
    });

    const initialMe = document.body.getAttribute('data-initial-me') || '';
    if (!dynamicMeStyle) {
      dynamicMeStyle = document.getElementById('dynamic-me-style');
      if (!dynamicMeStyle) {
        dynamicMeStyle = document.createElement('style');
        dynamicMeStyle.id = 'dynamic-me-style';
        document.head.appendChild(dynamicMeStyle);
      }
    }

    if (currentMeUser === initialMe) {
      // The HTML generated already has .is-me correctly placed on the elements
      dynamicMeStyle.textContent = '';
      return;
    }

    if (!currentMeUser) {
      // All aligned to left
      dynamicMeStyle.textContent = `
        .message-row { justify-content: flex-start !important; }
        .message-row .avatar { display: flex !important; }
        .message-row .sender { display: block !important; }
        .message-row .message {
          border-bottom-left-radius: 2px !important;
          border-bottom-right-radius: 10px !important;
          background: var(--bubble-received-bg) !important;
          border-color: var(--bubble-received-border) !important;
          color: var(--bubble-received-text) !important;
        }
      `;
    } else {
      const esc = (window.CSS && CSS.escape) ? CSS.escape(currentMeUser) : currentMeUser.replace(/["\\]/g, '\\$&');
      dynamicMeStyle.textContent = `
        .message-row { justify-content: flex-start !important; }
        .message-row .avatar { display: flex !important; }
        .message-row .sender { display: block !important; }
        .message-row .message {
          border-bottom-left-radius: 2px !important;
          border-bottom-right-radius: 10px !important;
          background: var(--bubble-received-bg) !important;
          border-color: var(--bubble-received-border) !important;
          color: var(--bubble-received-text) !important;
        }
        .message-row[data-sender="${esc}"] { justify-content: flex-end !important; }
        .message-row[data-sender="${esc}"] .avatar { display: none !important; }
        .message-row[data-sender="${esc}"] .sender { display: none !important; }
        .message-row[data-sender="${esc}"] .message {
          border-bottom-left-radius: 10px !important;
          border-bottom-right-radius: 2px !important;
          background: var(--bubble-sent-bg) !important;
          border-color: var(--bubble-sent-border) !important;
          color: var(--bubble-sent-text) !important;
        }
      `;
    }
  };

  const meSelectEl = document.getElementById('me-select');
  const validParticipant = function(name) {
    if (!name || !meSelectEl) return false;
    return Array.from(meSelectEl.options).some(o => o.value === name);
  };

  const initialMeAttr = document.body.getAttribute('data-initial-me') || '';
  let storedMe = localStorage.getItem('wa_me_user');
  if (storedMe && !validParticipant(storedMe)) {
    storedMe = null;
  }
  const resolvedActiveMe = (storedMe !== null) ? storedMe : initialMeAttr;
  if (resolvedActiveMe) {
    window.setMeUser(resolvedActiveMe);
  }

  // -------------------------------------------------------------------------
  // WhatsApp Doodle Wallpaper Toggle
  // -------------------------------------------------------------------------
  (function() {
    const wallpaperBtn  = document.getElementById('wallpaper-toggle');
    const wallpaperIcon = document.getElementById('wallpaper-icon');
    if (!wallpaperBtn) return;
    let wallpaperOn = localStorage.getItem('wa_wallpaper') === '1';

    function applyWallpaper(on) {
      wallpaperOn = on;
      document.body.classList.toggle('wallpaper-on', on);
      if (wallpaperIcon) wallpaperIcon.textContent = on ? '🏔️' : '🏞️';
      localStorage.setItem('wa_wallpaper', on ? '1' : '0');
    }

    applyWallpaper(wallpaperOn);
    wallpaperBtn.addEventListener('click', () => applyWallpaper(!wallpaperOn));
  })();

  // -------------------------------------------------------------------------
  // Advanced Filters: by sender, by month, media only
  // -------------------------------------------------------------------------
  (function() {
    const filterSender    = document.getElementById('filter-sender');
    const filterMonth     = document.getElementById('filter-month');
    const filterMediaOnly = document.getElementById('filter-media-only');
    const filterReset     = document.getElementById('filter-reset');
    if (!filterSender) return;

    let activeSender = '';
    let activeMonth  = '';
    let mediaOnly    = false;

    // Populate sender options instantly from me-select options
    const meSelectEl = document.getElementById('me-select');
    if (meSelectEl) {
      Array.from(meSelectEl.options).forEach(opt => {
        if (opt.value) {
          const sOpt = document.createElement('option');
          sOpt.value = opt.value;
          sOpt.textContent = '👤 ' + opt.value;
          filterSender.appendChild(sOpt);
        }
      });
    }

    // Populate month options from date-separators data-date attribute
    const monthMap = new Map();
    document.querySelectorAll('.date-separator[data-date]').forEach(sep => {
      const dateVal = sep.getAttribute('data-date');
      if (dateVal) {
        const d = new Date(dateVal + 'T12:00:00');
        const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
        if (!monthMap.has(key)) {
          const label = d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
          monthMap.set(key, label.charAt(0).toUpperCase() + label.slice(1));
        }
      }
    });
    monthMap.forEach((label, key) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = '📅 ' + label;
      filterMonth.appendChild(opt);
    });

    const filterSummary = document.getElementById('filter-summary');

    function applyFilters() {
      const rows = chatContainer ? chatContainer.querySelectorAll('.message-row') : [];
      let visibleCount = 0;
      for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        let show = true;
        const sender = row.getAttribute('data-sender') || '';
        if (activeSender && sender !== activeSender) show = false;
        if (show && mediaOnly && row.getAttribute('data-has-media') !== 'true') show = false;
        if (show && activeMonth) {
          const rowMonth = row.getAttribute('data-month');
          if (rowMonth) {
            if (rowMonth !== activeMonth) show = false;
          } else {
            let sep = row.previousElementSibling;
            while (sep && !sep.classList.contains('date-separator')) {
              sep = sep.previousElementSibling;
            }
            if (sep && sep.getAttribute('data-month') !== activeMonth) show = false;
          }
        }
        row.classList.toggle('filter-hidden', !show);
        if (show) visibleCount++;
      }

      // Hide day-groups that have no visible children
      const dayGroups = chatContainer ? chatContainer.querySelectorAll('.day-group') : [];
      for (let i = 0; i < dayGroups.length; i++) {
        const dg = dayGroups[i];
        const hasVisible = !!dg.querySelector('.message-row:not(.filter-hidden):not(.search-hidden)');
        dg.classList.toggle('filter-hidden', !hasVisible);
      }

      // Hide date separators that have no visible children
      const separators = chatContainer ? chatContainer.querySelectorAll('.date-separator') : [];
      for (let i = 0; i < separators.length; i++) {
        const sep = separators[i];
        let next = sep.nextElementSibling;
        let hasVisible = false;
        while (next && !next.classList.contains('date-separator')) {
          if (!next.classList.contains('filter-hidden') && !next.classList.contains('search-hidden') && !next.classList.contains('system-message')) {
            hasVisible = true;
            break;
          }
          next = next.nextElementSibling;
        }
        sep.classList.toggle('filter-hidden', !hasVisible);
      }

      if (filterSummary) {
        if (activeSender || activeMonth || mediaOnly) {
          filterSummary.textContent = visibleCount + ' / ' + rows.length + ' messages';
        } else {
          filterSummary.textContent = '';
        }
      }

      // Scroll to first visible month
      if (activeMonth) {
        const firstSep = document.querySelector('.day-group[data-month="' + activeMonth + '"]:not(.filter-hidden)') ||
                         document.querySelector('.date-separator[data-month="' + activeMonth + '"]:not(.filter-hidden)');
        if (firstSep) firstSep.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    filterSender.addEventListener('change', () => {
      activeSender = filterSender.value;
      applyFilters();
    });
    filterMonth.addEventListener('change', () => {
      activeMonth = filterMonth.value;
      applyFilters();
    });
    filterMediaOnly.addEventListener('click', () => {
      mediaOnly = !mediaOnly;
      filterMediaOnly.classList.toggle('filter-active', mediaOnly);
      applyFilters();
    });
    filterReset.addEventListener('click', () => {
      activeSender = ''; activeMonth = ''; mediaOnly = false;
      filterSender.value = ''; filterMonth.value = '';
      filterMediaOnly.classList.remove('filter-active');
      if (filterSummary) filterSummary.textContent = '';
      document.querySelectorAll('.filter-hidden').forEach(el => el.classList.remove('filter-hidden'));
    });
  })();

  // -------------------------------------------------------------------------
  // Jump to Message helper (scroll + pulse animation)
  // -------------------------------------------------------------------------
  window.jumpToMessage = function(msgId) {
    if (!msgId) return;
    const target = document.getElementById(msgId);
    if (!target) return;

    // Close gallery modal if open
    const galleryModal = document.getElementById('gallery-modal');
    if (galleryModal && galleryModal.classList.contains('active')) {
      galleryModal.classList.remove('active');
      document.body.style.overflow = '';
    }

    // Ensure target message row is visible
    const row = target.closest('.message-row');
    if (row) {
      row.classList.remove('filter-hidden', 'search-hidden');
      let prev = row.previousElementSibling;
      while (prev && !prev.classList.contains('date-separator')) {
        prev = prev.previousElementSibling;
      }
      if (prev) prev.classList.remove('filter-hidden', 'search-hidden');
    }

    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    target.classList.remove('msg-jump-pulse');
    void target.offsetWidth;
    target.classList.add('msg-jump-pulse');
    setTimeout(() => target.classList.remove('msg-jump-pulse'), 2200);
  };

  // -------------------------------------------------------------------------
  // Media Gallery (High-Performance On-Demand Lazy Loading)
  // -------------------------------------------------------------------------
  (function() {
    const galleryModal  = document.getElementById('gallery-modal');
    const galleryBtn    = document.getElementById('gallery-btn');
    const galleryClose  = document.getElementById('gallery-close');
    const galleryDataEl = document.getElementById('gallery-data');
    if (!galleryModal || !galleryDataEl) return;

    let galleryData = {};
    try { galleryData = JSON.parse(galleryDataEl.textContent); } catch (e) { galleryData = {}; }

    const photos = galleryData.photos || [];
    const audios = galleryData.audios || [];
    const docs   = galleryData.docs   || [];
    const links  = galleryData.links  || [];

    // Tab counts
    function setTabCount(id, n) {
      const el = document.getElementById(id);
      if (el) el.textContent = n > 0 ? n : '';
    }
    setTabCount('gtc-photos', photos.length);
    setTabCount('gtc-audios', audios.length);
    setTabCount('gtc-docs', docs.length + links.length);

    // Gallery badge
    const badge = document.getElementById('gallery-count-badge');
    const totalMedia = photos.length + audios.length + docs.length + links.length;
    if (badge) {
      badge.textContent = totalMedia > 0 ? totalMedia : '';
      if (!totalMedia) badge.setAttribute('data-zero', '1');
    }

    // Lazy load state (only render elements when tab is active / requested)
    const loadedCount = { photos: 0, audios: 0, docs: 0 };
    const allDocs = docs.map(d => Object.assign({}, d, {type: 'doc'})).concat(links.map(l => Object.assign({}, l, {type: 'link'})));

    function loadMorePhotos(limit = 48) {
      const photoPanel = document.getElementById('gp-photos');
      if (!photoPanel) return;
      if (photos.length === 0) {
        photoPanel.innerHTML = '<div class="g-empty">📷 Aucune photo ou vidéo</div>';
        return;
      }
      let grid = photoPanel.querySelector('.g-photo-grid');
      if (!grid) {
        grid = document.createElement('div');
        grid.className = 'g-photo-grid';
        photoPanel.appendChild(grid);
      }
      const start = loadedCount.photos;
      const end = Math.min(start + limit, photos.length);
      for (let i = start; i < end; i++) {
        const p = photos[i];
        const wrap = document.createElement('div');
        wrap.className = 'g-thumb-wrap';
        if (p.video) {
          wrap.innerHTML =
            '<video src="' + p.src + '" style="width:100%;height:100%;object-fit:cover" preload="metadata"></video>' +
            '<div class="g-video-badge">▶️</div>' +
            '<div class="g-thumb-meta">' + p.sender + ' · ' + p.time + '</div>' +
            '<button class="g-jump-btn" title="Aller au message">➔</button>';
          wrap.addEventListener('click', function(e) {
            if (e.target.classList.contains('g-jump-btn')) {
              e.stopPropagation();
              window.jumpToMessage(p.msgId);
              return;
            }
            window.openLightboxVideo(p.src);
          });
        } else {
          const img = document.createElement('img');
          img.src = p.src;
          img.loading = 'lazy';
          img.alt = '';
          const meta = document.createElement('div');
          meta.className = 'g-thumb-meta';
          meta.textContent = p.sender + ' · ' + p.time;
          const jumpBtn = document.createElement('button');
          jumpBtn.className = 'g-jump-btn';
          jumpBtn.title = 'Aller au message';
          jumpBtn.textContent = '➔';
          jumpBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            window.jumpToMessage(p.msgId);
          });
          wrap.appendChild(img);
          wrap.appendChild(meta);
          wrap.appendChild(jumpBtn);
          wrap.addEventListener('click', function(e) {
            if (e.target !== jumpBtn) openLightbox(img);
          });
        }
        grid.appendChild(wrap);
      }
      loadedCount.photos = end;
    }

    function loadMoreAudios(limit = 25) {
      const audioPanel = document.getElementById('gp-audios');
      if (!audioPanel) return;
      if (audios.length === 0) {
        audioPanel.innerHTML = '<div class="g-empty">🎤 Aucune note vocale</div>';
        return;
      }
      let list = audioPanel.querySelector('.g-audio-list');
      if (!list) {
        list = document.createElement('div');
        list.className = 'g-audio-list';
        audioPanel.appendChild(list);
      }
      const start = loadedCount.audios;
      const end = Math.min(start + limit, audios.length);
      for (let i = start; i < end; i++) {
        const a = audios[i];
        const item = document.createElement('div');
        item.className = 'g-audio-item';
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.preload = 'none';
        audio.src = a.src;
        const metaEl = document.createElement('div');
        metaEl.className = 'g-audio-meta';
        metaEl.textContent = '🎤 ' + a.sender + ' · ' + a.time;
        const jumpBtn = document.createElement('button');
        jumpBtn.className = 'g-jump-link';
        jumpBtn.textContent = 'Aller au message ➔';
        jumpBtn.addEventListener('click', function() { window.jumpToMessage(a.msgId); });
        item.appendChild(audio);
        item.appendChild(metaEl);
        item.appendChild(jumpBtn);
        list.appendChild(item);
      }
      loadedCount.audios = end;
    }

    function loadMoreDocs(limit = 40) {
      const docPanel = document.getElementById('gp-docs');
      if (!docPanel) return;
      if (allDocs.length === 0) {
        docPanel.innerHTML = '<div class="g-empty">📄 Aucun document ou lien</div>';
        return;
      }
      let list = docPanel.querySelector('.g-doc-list');
      if (!list) {
        list = document.createElement('div');
        list.className = 'g-doc-list';
        docPanel.appendChild(list);
      }
      const start = loadedCount.docs;
      const end = Math.min(start + limit, allDocs.length);
      for (let i = start; i < end; i++) {
        const item = allDocs[i];
        const itemWrap = document.createElement('div');
        itemWrap.style.display = 'flex';
        itemWrap.style.flexDirection = 'column';
        itemWrap.style.gap = '2px';

        const a = document.createElement('a');
        a.className = 'g-doc-item';
        a.href = item.href || '#';
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        const icon = item.type === 'doc' ? '📄' : '🔗';
        const label = item.label || item.href || '';
        const iconEl = document.createElement('span');
        iconEl.className = 'g-doc-icon';
        iconEl.textContent = icon;
        const info = document.createElement('div');
        info.className = 'g-doc-info';
        const labelEl = document.createElement('div');
        labelEl.className = 'g-doc-label';
        labelEl.textContent = label;
        const metaEl = document.createElement('div');
        metaEl.className = 'g-doc-meta';
        metaEl.textContent = item.sender + ' · ' + item.time;
        info.appendChild(labelEl);
        info.appendChild(metaEl);
        a.appendChild(iconEl);
        a.appendChild(info);

        const jumpBtn = document.createElement('button');
        jumpBtn.className = 'g-jump-link';
        jumpBtn.textContent = 'Aller au message ➔';
        jumpBtn.addEventListener('click', function(e) {
          e.preventDefault();
          window.jumpToMessage(item.msgId);
        });

        itemWrap.appendChild(a);
        itemWrap.appendChild(jumpBtn);
        list.appendChild(itemWrap);
      }
      loadedCount.docs = end;
    }

    function renderCurrentTabChunk(tabName) {
      if (tabName === 'photos') loadMorePhotos();
      else if (tabName === 'audios') loadMoreAudios();
      else if (tabName === 'docs') loadMoreDocs();
    }

    // Tab switching
    document.querySelectorAll('.g-tab').forEach(function(tab) {
      tab.addEventListener('click', function() {
        const target = tab.getAttribute('data-tab');
        document.querySelectorAll('.g-tab').forEach(function(t) { t.classList.remove('active'); });
        document.querySelectorAll('.g-panel').forEach(function(p) { p.classList.remove('active'); });
        tab.classList.add('active');
        const panel = document.getElementById('gp-' + target);
        if (panel) panel.classList.add('active');
        if (loadedCount[target] === 0) {
          renderCurrentTabChunk(target);
        }
      });
    });

    // Infinite scroll inside gallery content
    const galleryContent = document.getElementById('gallery-content');
    if (galleryContent) {
      galleryContent.addEventListener('scroll', debounce(function() {
        if (galleryContent.scrollTop + galleryContent.clientHeight >= galleryContent.scrollHeight - 300) {
          const activeTab = document.querySelector('.g-tab.active');
          const tabName = activeTab ? activeTab.getAttribute('data-tab') : 'photos';
          renderCurrentTabChunk(tabName);
        }
      }, 60));
    }

    // Open/close gallery modal
    function openGallery() {
      galleryModal.classList.add('active');
      document.body.style.overflow = 'hidden';
      const activeTab = document.querySelector('.g-tab.active');
      const tabName = activeTab ? activeTab.getAttribute('data-tab') : 'photos';
      if (loadedCount[tabName] === 0) {
        renderCurrentTabChunk(tabName);
      }
    }

    function closeGallery() {
      galleryModal.classList.remove('active');
      document.body.style.overflow = '';
    }

    if (galleryBtn)   galleryBtn.addEventListener('click', openGallery);
    if (galleryClose) galleryClose.addEventListener('click', closeGallery);
    galleryModal.addEventListener('click', function(e) {
      if (e.target === galleryModal) closeGallery();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && galleryModal.classList.contains('active')) closeGallery();
    });
  })();

})();
