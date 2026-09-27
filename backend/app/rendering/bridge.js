/* GREPO bridge v1.1. Upstream Archify is immutable; this wrapper uses its public
 * focus/view APIs and audited data-node-id DOM seam. No repository code executes. */
(() => {
  'use strict';
  const manifest = JSON.parse(document.getElementById('codecanopy-manifest').textContent);
  const ids = new Set(manifest.graph.entities.map(entity => entity.id));
  let nonce = null;
  const emit = (type, entityId, camera) => {
    if (nonce && window.parent !== window) window.parent.postMessage({
      channel: 'codecanopy-archify', version: '1.1', nonce,
      snapshotId: manifest.snapshot.id, viewId: manifest.view_id, type, entityId, camera,
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
    if (data.type === 'restore-camera') {
      const c = data.camera;
      if (c && [c.x,c.y,c.scale].every(Number.isFinite) && Math.abs(c.x)<1000000 && Math.abs(c.y)<1000000 && c.scale>=1 && c.scale<=3) Archify.view.centerAt(c.x,c.y,{scale:c.scale,instant:true});
    }
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
  // Observe the pinned viewer's transform instead of polling or changing vendor code.
  const svg = document.querySelector('.diagram-container > svg');
  let lastCamera = '';
  const reportCamera = () => {
    if (!nonce || !Archify.view) return;
    const viewport = Archify.view.logicalViewport();
    if (!viewport) return;
    const state = Archify.view.state();
    const camera = {x: viewport.x + viewport.width / 2, y: viewport.y + viewport.height / 2, scale: state.scale};
    // logicalViewport clamps its visible rectangle to the diagram. Recover the
    // actual camera center from the SVG metrics so edge pans also round-trip.
    const box = svg?.viewBox.baseVal;
    if (box && box.width > 0 && box.height > 0 && !(innerWidth <= 720 && svg.parentElement.hasAttribute('data-wide-diagram'))) {
      const width = svg.clientWidth, height = svg.clientHeight;
      const fit = Math.min(width / box.width, height / box.height);
      if (fit > 0) {
        camera.x = box.x + ((width / 2 - state.x) / state.scale - (width - box.width * fit) / 2) / fit;
        camera.y = box.y + ((height / 2 - state.y) / state.scale - (height - box.height * fit) / 2) / fit;
      }
    }
    const serialized = JSON.stringify(camera);
    if (serialized !== lastCamera) {lastCamera = serialized; emit('camera', undefined, camera);}
  };
  if (svg) new MutationObserver(reportCamera).observe(svg, {attributes:true, attributeFilter:['style','data-view-scale']});
  document.querySelector('.diagram-container')?.addEventListener('scroll', reportCamera, {passive:true});
  const palette = {lime:'#8aaf42', blue:'#4678bc', violet:'#8660b5', amber:'#b78524'};
  for (const entity of manifest.graph.entities) {
    const color = palette[entity.metadata?.group_color];
    if (color) {
      const node = document.querySelector('[data-node-id="n_' + entity.id + '"]');
      const shape = node?.querySelector('rect');
      if (shape) {shape.style.stroke=color; shape.style.strokeWidth='3px';}
    }
  }
  let readerTheme = null;
  try { readerTheme = localStorage.getItem('archify-theme'); } catch (_) { /* Opaque embeds have no storage. */ }
  const requestedTheme = new URLSearchParams(window.location.search).get('theme');
  const hasExplicitTheme = requestedTheme === 'light' || requestedTheme === 'dark';
  // An explicit viewer request wins; otherwise embedded readers and first opens
  // use the saved view theme, while standalone readers retain their own choice.
  if (!hasExplicitTheme && (window.parent !== window || !readerTheme) && document.documentElement.dataset.theme !== manifest.preferences.theme) Archify.theme.toggle();
  // A visible offline disclosure and machine-readable manifest preserve provenance.
  const disclosure = document.createElement('p');
  disclosure.className = 'codecanopy-provenance';
  disclosure.textContent = 'GREPO · Repository structure · ' + manifest.graph.entities.length +
    ' entities in this view · source code not included · Archify 9e35d2b · ' +
    'View labels and groups are user preferences, not source changes. ' +
    manifest.export_scope + ' Not connected: ' + manifest.deferred_capabilities.join(', ') + '.';
  document.querySelector('.header')?.appendChild(disclosure);
})();
