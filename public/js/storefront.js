(() => {
  const api = "/api/method/solua_home.api.color_card.";
  const names = {
    SH151114: "Morandi",
    SH151107: "Coleção Dourada",
    SH151046: "Coleção Sombra",
  };
  const reference = (card) => card.order_code || card.template_code || card.item_code || "";
  const localized = (value, fallback = "") => value && !/\p{Script=Han}/u.test(value) ? value : fallback;
  const productName = (card) => names[card.template_code] || localized(card.name, "Cortina");
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const detailUrl = (card) => "/colors?" + new URLSearchParams({ q: reference(card) });
  const dimensions = (card) => {
    const size = String(card.spec_summary || "").match(/^\s*(\d+(?:[.,]\d+)?)\s*[*×x]\s*(\d+(?:[.,]\d+)?)\s*cm\s*$/i);
    return size ? size[1] + " × " + size[2] + " cm" : "";
  };
  const facts = (card) => [dimensions(card), card.stock_uom === "条" ? "Unidade: painel" : ""].filter(Boolean).join(" · ");
  const photo = (path, alt, zoom = false, loading = "lazy") => {
    if (typeof path !== "string" || !/^\/files\/[\w. %()-]+\.(png|jpe?g|webp|avif|gif)$/i.test(path) || /%(2f|5c)/i.test(path)) {
      return '<span class="media-empty">Imagem indisponível</span>';
    }
    const img = `<img src="${escape(path)}" alt="${escape(alt)}" width="650" height="650" loading="${loading}">`;
    return zoom ? `<a class="zoom" href="${escape(path)}" aria-label="${escape("Abrir imagem: " + alt)}">${img}</a>` : img;
  };

  async function request(method, params) {
    const response = await fetch(api + method + "?" + new URLSearchParams(params), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
    return (await response.json()).message;
  }

  async function loadCatalog() {
    const grid = document.querySelector("#catalog-grid");
    const status = document.querySelector("#catalog-status");
    status.textContent = "A carregar as coleções…";
    try {
      const { items } = await request("get_public_catalog", { limit: 60 });
      const cards = items.filter((card) => reference(card));
      grid.innerHTML = cards.map((card) => {
        const title = productName(card);
        return `<article class="product-card">
          <a class="product-link" href="${escape(detailUrl(card))}">
            <div class="card-media">${photo(card.image, "")}</div>
            <div class="card-copy">
              <p class="reference">${escape(reference(card))}</p>
              <h3>${escape(title)}</h3>
              <p class="specs">${escape(facts(card) || "Medidas por confirmar")}</p>
              <span class="card-action">Ver cartela <span aria-hidden="true">↗</span></span>
            </div>
          </a>
        </article>`;
      }).join("");
      status.textContent = cards.length ? "" : "Ainda não há coleções disponíveis.";
    } catch {
      status.textContent = "Não foi possível carregar as coleções. Podes pesquisar directamente na cartela de cores.";
    }
  }

  async function loadColorCard() {
    const input = document.querySelector("#q");
    const status = document.querySelector("#color-status");
    const result = document.querySelector("#color-result");
    const query = new URLSearchParams(location.search).get("q")?.trim();
    if (!query) {
      status.textContent = "Encontra a referência na página da coleção ou na etiqueta da cortina.";
      return;
    }
    input.value = query;
    status.textContent = "A procurar a cartela…";
    try {
      const card = await request("get_public_color_card", { query });
      if (!card) {
        status.textContent = "Não encontrámos uma cartela com essa referência. Confirma o código ou explora as coleções.";
        return;
      }
      const title = productName(card);
      const variants = card.variants || [];
      result.innerHTML = `<article class="color-result" aria-labelledby="color-result-title">
        <div class="result-summary">
          <div>
            <p class="reference">${escape(reference(card))}</p>
            <h2 id="color-result-title">${escape(title)}</h2>
            <p class="specs">${escape(facts(card) || "Medidas por confirmar")}</p>
            <p class="note">A cor pode variar com a luz e com o ecrã.</p>
          </div>
          <div class="result-media">${photo(card.image, "Cartela " + title, true, "eager")}</div>
        </div>
        ${variants.length ? `<h3 class="variants-title">Cores por referência</h3>
          <ul class="variant-grid">${variants.map((variant) => {
            const code = reference(variant);
            const name = localized(variant.color_name, "Cor " + (variant.color_code || code));
            return `<li><div class="card-media">${photo(variant.image, name, true)}</div>
              <p>${escape(name)} <span class="reference">${escape(code)}</span></p></li>`;
          }).join("")}</ul>` : ""}
      </article>`;
      document.querySelector("#color-browse").hidden = true;
      status.textContent = "";
    } catch {
      status.textContent = "Não foi possível consultar a cartela agora. Tenta pesquisar novamente.";
    }
  }

  if (document.querySelector("#catalog-grid")) loadCatalog();
  if (document.querySelector("#color-search")) loadColorCard();
})();
