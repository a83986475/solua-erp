(function () {
  const grid = document.querySelector('#catalog-grid');
  const status = document.querySelector('#catalog-status');
  const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const imageUrl = (value) => {
    if (!value) return '';
    return value.startsWith('/') ? value : `/${value}`;
  };
  const renderCard = (card) => {
    const variants = (card.variants || []).filter((item) => item.image || item.color_name || item.color_code).slice(0, 8);
    const firstImage = imageUrl(card.image || (variants[0] && variants[0].image));
    const colors = variants.map((item) => `<a href="/colors?q=${encodeURIComponent(item.order_code || card.order_code || item.item_code || '')}">${escapeHtml(item.color_name || item.color_code || item.item_code)}</a>`).join('');
    return `<article class="catalog-card">${firstImage ? `<img src="${escapeHtml(firstImage)}" loading="lazy" alt="${escapeHtml(card.name || card.item_name || 'Cortina')}">` : '<div class="catalog-image-fallback">IMAGEM POR CONFIRMAR</div>'}<div class="catalog-meta"><span class="catalog-code">${escapeHtml(card.order_code || card.template_code)}</span><h3>${escapeHtml(card.name || card.item_name || 'Cortina')}</h3><p>${escapeHtml(card.spec_summary || 'Medidas e composição a confirmar com a equipa.')}</p>${colors ? `<div class="catalog-colors">${colors}</div>` : ''}</div></article>`;
  };
  fetch('/api/method/solua_home.api.color_card.get_public_catalog?limit=60', {credentials:'same-origin'})
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((payload) => {
      const data = payload.message || payload;
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        grid.innerHTML = '<div class="catalog-placeholder">Ainda não há produtos publicados para esta vitrine. Consulte a cartela de cores para procurar um artigo.</div>';
        status.textContent = 'Catálogo público em preparação';
        return;
      }
      grid.innerHTML = items.map(renderCard).join('');
      status.textContent = `${items.length} ${items.length === 1 ? 'coleção publicada' : 'coleções publicadas'} · sem preços`;
    })
    .catch(() => {
      grid.innerHTML = '<div class="catalog-placeholder">Não foi possível carregar o catálogo agora. A cartela pública continua disponível em /colors.</div>';
      status.textContent = 'Catálogo temporariamente indisponível';
    });
}());
