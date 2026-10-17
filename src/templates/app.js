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

  function runSearch(query) {
    clearHighlights();
    searchMatches = [];
    currentMatchIdx = -1;

    const q = query ? query.trim() : '';
    if (!q) {
      clearSearch();
      return;
    }

    const qLower = q.toLowerCase();
    const regex = new RegExp('(' + escapeRegex(q) + ')', 'gi');

    // 1. Fast pre-filter: iterate over text elements without altering DOM of non-matches
    const textEls = chatContainer.querySelectorAll('.sub-message .text');
    for (let i = 0; i < textEls.length; i++) {
      const el = textEls[i];
      if (el.textContent.toLowerCase().includes(qLower)) {
        highlightInElement(el, regex);
      }
    }

    // 2. Hide / show message rows based on whether they contain a mark
    const rows = chatContainer.querySelectorAll('.message-row');
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const hasMark = !!row.querySelector('mark.wa-highlight');
      row.classList.toggle('search-hidden', !hasMark);
    }

    // 3. Hide / show date separators
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

    // 4. Collect matches
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
  // Lightbox
  // -------------------------------------------------------------------------
  const lightbox    = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightbox-img');
  let lbImages = [];
  let lbIdx = 0;

  function attachImageListeners() {
    document.querySelectorAll('.media-img').forEach(img => {
      img.onclick = () => openLightbox(img);
    });
  }

  function openLightbox(img) {
    if (!lightbox || !lightboxImg) return;
    lbImages = Array.from(document.querySelectorAll('.media-img'));
    lbIdx = lbImages.indexOf(img);
    lightboxImg.src = img.src;
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
  }

  function lbMove(delta) {
    if (!lbImages.length || !lightboxImg) return;
    lbIdx = ((lbIdx + delta + lbImages.length) % lbImages.length);
    lightboxImg.src = lbImages[lbIdx].src;
  }

  const lbClose = document.getElementById('lb-close');
  const lbPrev  = document.getElementById('lb-prev');
  const lbNext  = document.getElementById('lb-next');

  if (lbClose) lbClose.addEventListener('click', closeLightbox);
  if (lbPrev)  lbPrev.addEventListener('click', () => lbMove(-1));
  if (lbNext)  lbNext.addEventListener('click', () => lbMove(1));
  if (lightbox) {
    lightbox.addEventListener('click', e => {
      if (e.target === lightbox) closeLightbox();
    });
  }

  document.addEventListener('keydown', e => {
    if (!lightbox || !lightbox.classList.contains('active')) return;
    if (e.key === 'Escape')     closeLightbox();
    if (e.key === 'ArrowLeft')  lbMove(-1);
    if (e.key === 'ArrowRight') lbMove(1);
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

  document.addEventListener('play', function(e) {
    if (e.target && e.target.tagName === 'AUDIO') {
      const sp = parseFloat(e.target.dataset.speed || 1);
      if (sp && sp !== 1) {
        e.target.playbackRate = sp;
      }
    }
  }, true);

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

    document.querySelectorAll('.message-row').forEach(row => {
      const s = row.getAttribute('data-sender') || '';
      const isMe = currentMeUser && s === currentMeUser;
      row.classList.toggle('is-me', isMe);
    });
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
})();
