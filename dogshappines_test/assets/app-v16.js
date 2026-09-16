(() => {
  'use strict';

  const wait = (tries = 220) => {
    if (window.V15 && window.V14 && window.showView && window.api) return boot();
    if (tries <= 0) return console.error('v16: runtime not ready');
    setTimeout(() => wait(tries - 1), 50);
  };

  function boot() {
    const q = id => document.getElementById(id);
    const pad = n => String(n).padStart(2, '0');
    const today = () => {
      const d = new Date();
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    };
    const localDateTime = (d = new Date()) =>
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

    window.V16 = { version: 16 };

    function tryShowPicker(input) {
      if (!input || input.disabled || input.readOnly || typeof input.showPicker !== 'function') return;
      try { input.showPicker(); } catch (_) {}
    }

    function enhancePicker(input) {
      if (!input || input.dataset.v16Picker || input.classList.contains('v15-hidden-time')) return;
      input.dataset.v16Picker = '1';
      input.classList.add('v16-native-picker');
      input.setAttribute('autocomplete', 'off');
      input.addEventListener('click', () => tryShowPicker(input));
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          tryShowPicker(input);
        }
      });
    }

    function enhanceButtons(root = document) {
      root.querySelectorAll?.('button:not([type])').forEach(btn => {
        if (btn.closest('form') && btn.closest('form').classList.contains('v14-chat-input')) return;
        btn.type = 'button';
      });
    }

    function enhanceControls(root = document) {
      root.querySelectorAll?.('input[type="date"],input[type="time"],input[type="datetime-local"]').forEach(enhancePicker);
      enhanceButtons(root);

      const bookDate = q('bookDate');
      if (bookDate) {
        bookDate.min = today();
        if (!bookDate.dataset.v16Refresh) {
          bookDate.dataset.v16Refresh = '1';
          ['input', 'change'].forEach(evt => bookDate.addEventListener(evt, () => {
            if (window.refreshBookingSlotsV15) setTimeout(() => window.refreshBookingSlotsV15(), 0);
          }));
        }
      }

      const editDate = q('v15EditDate');
      if (editDate) editDate.min = today();

      const blockStart = q('v14BlockStart');
      const blockEnd = q('v14BlockEnd');
      if (blockStart && blockEnd) {
        const now = new Date(Date.now() + 5 * 60 * 1000);
        const min = localDateTime(now);
        blockStart.min = min;
        blockEnd.min = blockStart.value || min;
        if (!blockStart.dataset.v16Linked) {
          blockStart.dataset.v16Linked = '1';
          blockStart.addEventListener('change', () => {
            blockEnd.min = blockStart.value;
            const a = new Date(blockStart.value);
            const b = new Date(blockEnd.value);
            if (blockStart.value && (!blockEnd.value || !Number.isFinite(b.getTime()) || b <= a)) {
              blockEnd.value = localDateTime(new Date(a.getTime() + 60 * 60 * 1000));
            }
          });
        }
      }
    }

    function normalizeVisibleView() {
      const view = document.querySelector('.view:not(.hidden)');
      if (!view) return;
      view.classList.add('v16-enhanced-view');
      enhanceControls(view);
    }

    function auditInlineHandlers() {
      const missing = new Set();
      document.querySelectorAll('[onclick]').forEach(el => {
        const raw = el.getAttribute('onclick') || '';
        const names = [...raw.matchAll(/(?:^|[;\s])([A-Za-z_$][\w$]*)\s*\(/g)].map(m => m[1]);
        names.forEach(name => {
          if (['if', 'for', 'while', 'confirm'].includes(name)) return;
          if (typeof window[name] !== 'function' && typeof globalThis[name] !== 'function') missing.add(name);
        });
      });
      if (missing.size) console.warn('v16: handlers not resolved yet', [...missing]);
    }

    const originalShow = window.showView;
    window.showView = async (...args) => {
      const result = await originalShow(...args);
      requestAnimationFrame(() => {
        normalizeVisibleView();
        enhanceControls(document);
      });
      return result;
    };

    const originalOpenAvailability = window.openAvailabilitySheetV14;
    if (originalOpenAvailability) {
      window.openAvailabilitySheetV14 = (...args) => {
        const result = originalOpenAvailability(...args);
        requestAnimationFrame(() => enhanceControls(document));
        return result;
      };
    }

    const originalOpenEdit = window.openEditOrderV15;
    if (originalOpenEdit) {
      window.openEditOrderV15 = async (...args) => {
        const result = await originalOpenEdit(...args);
        requestAnimationFrame(() => enhanceControls(document));
        return result;
      };
    }

    const originalOpenSettings = window.openSettingsV14;
    if (originalOpenSettings) {
      window.openSettingsV14 = async (...args) => {
        const result = await originalOpenSettings(...args);
        requestAnimationFrame(() => enhanceControls(document));
        return result;
      };
      window.openSettings = window.openSettingsV14;
    }

    const observer = new MutationObserver(mutations => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === 1) enhanceControls(node);
        });
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    document.addEventListener('pointerup', e => {
      const input = e.target.closest?.('input[type="date"],input[type="time"],input[type="datetime-local"]');
      if (input && !input.classList.contains('v15-hidden-time')) tryShowPicker(input);
    }, { passive: true });

    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape') return;
      q('v15Sheet')?.remove();
      q('v14SheetBackdrop')?.remove();
      q('v9Sheet')?.remove();
    });

    enhanceControls(document);
    normalizeVisibleView();
    setTimeout(auditInlineHandlers, 800);
  }

  wait();
})();
