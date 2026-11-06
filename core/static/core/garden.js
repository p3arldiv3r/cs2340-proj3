/* Shared progressive enhancement. Conversation text stays in this page's DOM. */
(() => {
  'use strict';
  const root = document.documentElement;
  const readPreference = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const savePreference = (key, value) => { try { localStorage.setItem(key, value); } catch { /* Storage is optional. */ } };
  const sizes = ['standard', 'large', 'largest'];
  function setTextSize(size) {
    root.dataset.textSize = sizes.includes(size) ? size : 'standard';
    document.querySelectorAll('[data-text-size]').forEach(button => {
      if (button.tagName === 'BUTTON') button.setAttribute('aria-pressed', String(button.dataset.textSize === root.dataset.textSize));
    });
  }
  function setContrast(enabled) {
    root.dataset.contrast = String(enabled);
    document.querySelector('[data-contrast]')?.setAttribute('aria-pressed', String(enabled));
  }
  setTextSize(readPreference('garden.textSize'));
  setContrast(readPreference('garden.contrast') === 'true');
  document.querySelectorAll('button[data-text-size]').forEach(button => button.addEventListener('click', () => {
    setTextSize(button.dataset.textSize);
    savePreference('garden.textSize', root.dataset.textSize);
  }));
  document.querySelector('[data-contrast]')?.addEventListener('click', () => {
    setContrast(root.dataset.contrast !== 'true');
    savePreference('garden.contrast', root.dataset.contrast);
  });

  const popup = document.querySelector('#chat-popup');
  let opener;
  document.querySelectorAll('[data-open-chat]').forEach(trigger => trigger.addEventListener('click', event => {
    if (!popup || typeof popup.showModal !== 'function') return; // Link remains a usable fallback.
    event.preventDefault();
    opener = trigger;
    popup.showModal();
    trigger.setAttribute('aria-expanded', 'true');
    popup.querySelector('[data-question-input]').focus();
  }));
  popup?.querySelector('[data-close-chat]')?.addEventListener('click', () => popup.close());
  popup?.addEventListener('close', () => {
    opener?.setAttribute('aria-expanded', 'false');
    opener?.focus();
  });

  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function message(author, text) {
    const article = element('article', `message message-${author === 'You' ? 'user' : 'assistant'}`);
    article.append(element('p', 'message-label', author), element('div', 'answer-copy', text));
    return article;
  }
  function appendSources(article, sources) {
    if (!sources?.length) return;
    const wrapper = element('div', 'source-list');
    wrapper.append(element('h3', '', 'Sources used'));
    const list = element('ol');
    for (const source of sources) {
      const item = element('li');
      const details = element('details', 'source-detail');
      details.append(element('summary', '', `Source ${source.number}: ${source.title}`));
      const content = element('div', 'source-content');
      content.append(element('p', 'record-id', `Record ID: ${source.external_id}`), element('blockquote', '', source.excerpt));
      let url;
      try { url = new URL(source.url); } catch { /* File sources have no URL. */ }
      if (url && ['http:', 'https:'].includes(url.protocol)) {
        const link = element('a', '', `Read original: ${source.title} ↗`);
        link.href = url.href;
        link.rel = 'noopener noreferrer';
        content.append(link);
      } else {
        content.append(element('p', 'muted', 'This document was provided as a file. The supporting passage is shown above.'));
      }
      details.append(content);
      item.append(details);
      list.append(item);
    }
    wrapper.append(list);
    article.append(wrapper);
  }

  document.querySelectorAll('[data-chat-root]').forEach(surface => {
    const form = surface.querySelector('[data-chat-form]');
    const input = surface.querySelector('[data-question-input]');
    const log = surface.querySelector('[data-chat-log]');
    const errors = surface.querySelector('[data-chat-errors]');
    const status = surface.querySelector('[data-chat-status]');
    const send = surface.querySelector('[data-send]');
    const stop = surface.querySelector('[data-stop]');
    let controller;
    surface.querySelectorAll('[data-quick-question]').forEach(button => button.addEventListener('click', () => {
      input.value = button.dataset.quickQuestion;
      input.focus();
    }));
    stop.addEventListener('click', () => controller?.abort());
    form.addEventListener('submit', async event => {
      if (!window.fetch || !window.AbortController) return;
      event.preventDefault();
      if (controller) return;
      const question = input.value.trim();
      if (!question || question.length > 1000) {
        errors.textContent = 'Enter a question between 1 and 1,000 characters.';
        errors.hidden = false;
        input.focus();
        return;
      }
      errors.hidden = true;
      errors.textContent = '';
      controller = new AbortController();
      const timeout = window.setTimeout(() => controller?.abort(), 30000);
      send.hidden = true;
      stop.hidden = false;
      if (document.activeElement === send) stop.focus();
      status.textContent = 'Looking through our sources…';
      form.setAttribute('aria-busy', 'true');
      try {
        const body = new FormData(form);
        body.set('question', question);
        const response = await fetch(form.dataset.endpoint, { method: 'POST', body, signal: controller.signal, credentials: 'same-origin', headers: { Accept: 'application/json' } });
        if (!(response.headers.get('content-type') || '').includes('application/json')) throw new Error('We could not answer right now. Refresh the page and try again.');
        const answer = await response.json();
        if (!response.ok) throw new Error(answer.error || 'We could not answer right now. Please try again shortly.');
        const reply = message('Assistant', answer.text);
        appendSources(reply, answer.sources);
        const turn = element('div', 'chat-turn');
        turn.append(message('You', question), reply);
        log.append(turn);
        // Preserve any new draft typed while this answer was being prepared.
        if (input.value.trim() === question) input.value = '';
        log.scrollTop = log.scrollHeight;
        status.textContent = '';
      } catch (error) {
        errors.textContent = error.name === 'AbortError' ? 'The request stopped. Your question is still here; you can send it again.' : error.message;
        errors.hidden = false;
        status.textContent = '';
      } finally {
        window.clearTimeout(timeout);
        controller = undefined;
        form.removeAttribute('aria-busy');
        send.hidden = false;
        stop.hidden = true;
        // Do not move focus away from a different page control or a closed popup.
        if (document.activeElement === stop) input.focus();
      }
    });
  });
})();
