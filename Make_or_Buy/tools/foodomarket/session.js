/**
 * Amorce de session Foodomarket — profil Chrome persistant.
 *
 * L'operateur se connecte A LA MAIN dans la fenetre qui s'ouvre. Aucun identifiant ne
 * transite par ce script. Le profil vit hors du depot; ne jamais le committer.
 *
 *   node tools/foodomarket/session.js
 *
 * Une fois la session etablie, les passes suivantes reutilisent le profil sans fenetre
 * de connexion. Relancer ce script quand la session expire.
 */
const { chromium } = require('playwright');
const os = require('os');

const PROFIL = process.env.FOODO_PROFILE || os.homedir() + '/.cache/foodomarket-profile';
const DEPART = 'https://shop.foodomarket.com/v/login';
const ATTENTE_MAX_MS = 5 * 60 * 1000;

async function ouvrir({ headless = false } = {}) {
  // channel 'chrome' et non le Chromium du module: la revision telechargee ne
  // correspondait pas a celle installee, et un vrai Chrome passe mieux sur la marketplace.
  return chromium.launchPersistentContext(PROFIL, {
    headless, channel: 'chrome',
    viewport: { width: 1500, height: 1100 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
}

/** Vrai si un cookie de session existe. Ne lit jamais sa valeur. */
async function sessionEtablie(ctx, page) {
  const cookies = await ctx.cookies();
  const aSession = cookies.some(c => /session|token|auth|sid/i.test(c.name) && c.value);
  return aSession && !/\/login|\/registration/.test(page.url());
}

async function main() {
  const ctx = await ouvrir();
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto(DEPART, { waitUntil: 'domcontentloaded' });
  console.log('Connecte-toi dans la fenetre. Profil :', PROFIL);

  const echeance = Date.now() + ATTENTE_MAX_MS;
  let ok = false;
  while (Date.now() < echeance) {
    await page.waitForTimeout(3000);
    if (await sessionEtablie(ctx, page)) { ok = true; break; }
  }
  console.log(ok ? 'ETAT: session etablie' : 'ETAT: pas de session detectee');
  await ctx.close();
  process.exit(ok ? 0 : 1);
}

module.exports = { ouvrir, sessionEtablie, PROFIL };
if (require.main === module) main().catch(e => { console.error('ERREUR:', e.message); process.exit(1); });
