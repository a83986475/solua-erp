(function () {
  const grid = document.querySelector('#catalog-grid');
  const status = document.querySelector('#catalog-status');
  const menu = document.querySelector('#navigation');
  const menuToggle = document.querySelector('.menu-toggle');
  const lightByCode = {
    SH151077: 'BLACKOUT 100%',
    SH151084: 'BLACKOUT 100%',
    SH151022: 'MUITO ESCURO 95%',
    SH151121: 'MUITO ESCURO 95%'
  };
  const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const imageUrl = (value) => {
    if (!value) return '';
    return value.startsWith('/') ? value : `/${value}`;
  };
  const renderCard = (card) => {
    const variants = (card.variants || []).filter((item) => item.image || item.color_name || item.color_code).slice(0, 8);
    const firstImage = imageUrl(card.image || (variants[0] && variants[0].image));
    const code = card.order_code || card.template_code || '';
    const light = lightByCode[code] || '';
    const colors = variants.map((item) => `<a href="/colors?q=${encodeURIComponent(item.order_code || code || item.item_code || '')}">${escapeHtml(item.color_name || item.color_code || item.item_code)}</a>`).join('');
    return `<article class="catalog-card"><div class="catalog-image">${firstImage ? `<img src="${escapeHtml(firstImage)}" loading="lazy" alt="${escapeHtml(card.name || card.item_name || 'Cortina')}">` : '<div class="catalog-image-fallback">IMAGEM POR CONFIRMAR</div>'}<span class="catalog-badge">COLEÇÃO PUBLICADA</span></div><div class="catalog-meta"><span>${escapeHtml(code)}</span><span>${escapeHtml(card.stock_uom || 'Cortina')}</span></div><h3>${escapeHtml(card.name || card.item_name || 'Cortina')}</h3>${light ? `<p class="catalog-light">${light}</p>` : ''}<p class="catalog-spec">${escapeHtml(card.spec_summary || 'Medidas e composição a confirmar com a equipa.')}</p>${colors ? `<div class="catalog-colors">${colors}</div>` : ''}<a class="catalog-action" href="/colors?q=${encodeURIComponent(code)}">Ver cores <span aria-hidden="true">↗</span></a></article>`;
  };

  if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', String(open));
      menuToggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
    });
    menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      menu.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.setAttribute('aria-label', 'Abrir menu');
    }));
  }

  fetch('/api/method/solua_home.api.color_card.get_public_catalog?limit=60', {credentials:'same-origin'})
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((payload) => {
      const data = payload.message || payload;
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        grid.innerHTML = '<div class="catalog-placeholder">Ainda não há coleções publicadas para esta vitrine. Consulte a cartela de cores para procurar um artigo.</div>';
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
