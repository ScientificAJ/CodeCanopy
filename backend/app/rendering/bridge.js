/* CodeCanopy bridge v1.1. Upstream Archify is immutable; this wrapper uses its public
 * focus/view APIs and audited data-node-id DOM seam. No repository code executes. */
(() => {
  'use strict';
  const manifest = JSON.parse(document.getElementById('codecanopy-manifest').textContent);
  const ids = new Set(manifest.graph.entities.map(entity => entity.id));
  let nonce = null;
  const emit = (type, entityId) => {
    if (nonce && window.parent !== window) window.parent.postMessage({
      channel: 'codecanopy-archify', version: '1.1', nonce,
      snapshotId: manifest.snapshot.id, viewId: manifest.view_id, type, entityId,
    }, '*'); // Opaque sandbox origins require '*'; receiver verifies source + nonce.
  };
  window.addEventListener('message', event => {
    const data = event.data;
    if (event.source !== window.parent || !data || data.channel !== 'codecanopy-archify' ||
        data.version !== '1.1' || data.snapshotId !== manifest.snapshot.id ||
        data.viewId !== manifest.view_id || typeof data.nonce !== 'string' || data.nonce.length < 16) return;
    if (data.type === 'init' && nonce === null) { nonce = data.nonce; emit('ready'); }
    if (data.nonce !== nonce) return;
    if (data.type === 'select' && ids.has(data.entityId)) Archify.focus.set('n_' + data.entityId, {toggle: false, updateUrl: false});
    if (data.type === 'zoom-in') Archify.view.zoomIn();
    if (data.type === 'zoom-out') Archify.view.zoomOut();
    if (data.type === 'fit' || data.type === 'reset') {
      Archify.focus.clear({updateUrl: false}); Archify.view.reset();
    }
  });
  const selected = target => target.closest && target.closest('[data-node-id]');
  document.addEventListener('click', event => {
    const node = selected(event.target);
    if (node && ids.has(manifest.renderer_ids[node.dataset.nodeId])) emit('select', manifest.renderer_ids[node.dataset.nodeId]);
  });
  document.addEventListener('dblclick', event => {
    const node = selected(event.target);
    if (node && ids.has(manifest.renderer_ids[node.dataset.nodeId])) emit('open', manifest.renderer_ids[node.dataset.nodeId]);
  });
  document.addEventListener('keydown', event => {
    const node = selected(event.target);
    if (node && ids.has(manifest.renderer_ids[node.dataset.nodeId]) && (event.key === 'Enter' || event.key === ' ')) emit('select', manifest.renderer_ids[node.dataset.nodeId]);
  });
  let readerTheme = null;
  try { readerTheme = localStorage.getItem('archify-theme'); } catch (_) { /* Opaque embeds have no storage. */ }
  // A standalone reader's explicit theme choice takes precedence on reopening.
  if ((window.parent !== window || !readerTheme) && document.documentElement.dataset.theme !== manifest.preferences.theme) Archify.theme.toggle();
  // A visible offline disclosure and machine-readable manifest preserve provenance.
  const footer = document.createElement('p');
  footer.className = 'codecanopy-provenance';
  footer.textContent = 'CodeCanopy · Repository structure · ' + manifest.graph.entities.length +
    ' entities in this view · source code not included · Archify 9e35d2b · ' +
    'View labels and groups are user preferences, not source changes. ' +
    'Not connected: ' + manifest.deferred_capabilities.join(', ') + '.';
  document.body.appendChild(footer);
})();
