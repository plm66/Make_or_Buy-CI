/**
 * Extraction d'une page de catalogue Foodomarket — noyau eprouve.
 *
 * Ce module ne sait PAS enumerer le catalogue: c'est le travail restant, decrit dans
 * docs/research/FOODOMARKET_CATALOGUE_SWEEP.md. Il sait lire une page deja affichee.
 */

/** Cartes produit visibles sur la page courante. */
async function cartes(page) {
  return page.evaluate(() => [...document.querySelectorAll('[id^="product-card-"]')].map(c => ({
    marketplace_product_ref: c.dataset.id,
    marketplace_supplier_ref: c.dataset.supplierId,
    lignes: c.innerText.split('\n').map(s => s.trim()).filter(Boolean),
  })));
}

const PRIX = /^([\d\s  ]*\d,\d+)\s*€\/(kg|l|pc|pi[eè]ce|colis)$/i;

function euros(s) {
  return parseFloat(s.replace(/[\s  ]/g, '').replace(',', '.'));
}

/**
 * Decoupe une carte en champs. Forme observee:
 *   [Promo] nom | fournisseur | origine+colisage | prix colis | prix unitaire
 * Les lignes de prix sont reconnues par leur forme, pas par leur position: certaines
 * cartes n'ont qu'un prix, d'autres deux, et "Promo" decale tout.
 */
function champs(carte) {
  const lignes = carte.lignes.filter(l => l.toLowerCase() !== 'promo');
  const prix = {};
  const texte = [];
  for (const l of lignes) {
    const m = PRIX.exec(l);
    if (!m) { texte.push(l); continue; }
    const u = m[2].toLowerCase().startsWith('pi') ? 'pc' : m[2].toLowerCase();
    prix[u] = euros(m[1]);
  }
  const unite = ['kg', 'l', 'pc'].find(u => u in prix) || null;
  return {
    marketplace_product_ref: carte.marketplace_product_ref,
    marketplace_supplier_ref: carte.marketplace_supplier_ref,
    product_name: texte[0] ?? null,
    marketplace_supplier_name: texte[1] ?? null,
    pack_raw: texte[2] ?? null,
    case_price_eur: prix.colis ?? null,
    unit_price_eur: unite ? prix[unite] : null,
    unit: unite,
    tax_basis: 'UNKNOWN',          // aucune page ne l'indique: ne jamais deduire
  };
}

/**
 * Controle d'arithmetique du colis. Ne corrige rien: signale.
 * "Never trust a displayed unit-price label when case arithmetic produces a different
 * delivered unit cost" — agents/price_capture_policy.json
 */
function ecartArithmetique(p) {
  if (p.case_price_eur == null || p.unit_price_eur == null || !p.pack_raw) return null;
  const m = /(\d+)\s*X\s*([\d.]+)\s*(KG|L)/i.exec(p.pack_raw);
  if (!m) return null;
  const quantite = parseInt(m[1], 10) * parseFloat(m[2]);
  if (!quantite) return null;
  const calcule = p.case_price_eur / quantite;
  return Math.abs(calcule - p.unit_price_eur) > 1e-3
    ? { annonce: p.unit_price_eur, calcule: Math.round(calcule * 1e4) / 1e4 }
    : null;
}

/** Defile jusqu'a ce que le nombre de cartes cesse d'augmenter. */
async function chargerTout(page, { pasMax = 20, pause = 1800 } = {}) {
  let avant = -1, liste = [];
  for (let i = 0; i < pasMax; i++) {
    liste = await cartes(page);
    if (liste.length === avant) break;
    avant = liste.length;
    await page.mouse.wheel(0, 4000);
    await page.waitForTimeout(pause);
  }
  return liste;
}

module.exports = { cartes, champs, ecartArithmetique, chargerTout };
