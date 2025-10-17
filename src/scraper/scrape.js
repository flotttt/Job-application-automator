require('dotenv').config({ path: require('path').join(__dirname, '../../.env') });
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const { parse } = require('json2csv');
const cliProgress = require('cli-progress');
const colors = require('colors');

puppeteer.use(StealthPlugin());

const CONFIG = {
  browserExecutable: process.env.BROWSER_EXECUTABLE,
  baseUrl: process.env.SITE_BASE_URL,
  searchPath: process.env.SITE_SEARCH_PATH,
  searchQuery: process.env.TYPE_OFFRE,
  location: process.env.LOCALISATION,
  outputPath: process.env.CSV_OUTPUT,
  progressFile: 'data/.scraper_progress.json',
  logFile: 'data/scraper.log',
  headless: process.env.HEADLESS === 'true',
  parallelTabs: parseInt(process.env.PARALLEL_TABS) || 2,
  maxPages: parseInt(process.env.MAX_PAGES) || 10,
  delays: {
    min: 3000,
    max: 6000,
    betweenJobs: 2000,
    betweenPages: 5000,
    afterCaptcha: 10000,
    scroll: 1000
  }
};

class Logger {
  constructor(logFile) {
    this.logFile = logFile;
    const dir = logFile.split('/').slice(0, -1).join('/');
    if (dir) fs.mkdirSync(dir, { recursive: true });
  }

  log(level, message) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level}] ${message}\n`;
    fs.appendFileSync(this.logFile, logEntry);
  }

  info(message) { this.log('INFO', message); }
  error(message) { this.log('ERROR', message); }
  success(message) { this.log('SUCCESS', message); }
}

const logger = new Logger(CONFIG.logFile);

class ProgressManager {
  constructor(progressFile) {
    this.progressFile = progressFile;
    this.data = this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.progressFile)) {
        return JSON.parse(fs.readFileSync(this.progressFile, 'utf8'));
      }
    } catch (error) {
      logger.error(`Erreur chargement progression: ${error.message}`);
    }
    return {
      lastPage: 0,
      scrapedUrls: [],
      jobOffers: [],
      startTime: Date.now(),
      captchaCount: 0
    };
  }

  save() {
    const dir = this.progressFile.split('/').slice(0, -1).join('/');
    if (dir) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(this.progressFile, JSON.stringify(this.data, null, 2));
  }

  reset() {
    this.data = {
      lastPage: 0,
      scrapedUrls: [],
      jobOffers: [],
      startTime: Date.now(),
      captchaCount: 0
    };
    this.save();
  }

  addJob(job) {
    if (!this.data.scrapedUrls.includes(job.url)) {
      this.data.jobOffers.push(job);
      this.data.scrapedUrls.push(job.url);
      this.save();
      this.saveToCSV();
    }
  }

  saveToCSV() {
    if (this.data.jobOffers.length === 0) return;

    try {
      const csvContent = parse(this.data.jobOffers, {
        fields: ['title', 'company', 'location', 'salary', 'contract', 'remote', 'publishedDate', 'description', 'url']
      });

      const directory = CONFIG.outputPath.split('/').slice(0, -1).join('/');
      if (directory) fs.mkdirSync(directory, { recursive: true });

      fs.writeFileSync(CONFIG.outputPath, csvContent);
      logger.success(`CSV mis à jour: ${this.data.jobOffers.length} offres`);
    } catch (error) {
      logger.error(`Erreur sauvegarde CSV: ${error.message}`);
    }
  }

  setLastPage(pageNumber) {
    this.data.lastPage = pageNumber;
    this.save();
  }

  incrementCaptcha() {
    this.data.captchaCount++;
    this.save();
  }
}

const randomDelay = (minDelay = CONFIG.delays.min, maxDelay = CONFIG.delays.max) =>
  new Promise(resolve => setTimeout(resolve, Math.random() * (maxDelay - minDelay) + minDelay));

async function humanScroll(page) {
  const scrolls = Math.floor(Math.random() * 2) + 1;
  for (let i = 0; i < scrolls; i++) {
    await page.evaluate(() => {
      window.scrollBy({
        top: Math.random() * 400 + 200,
        behavior: 'smooth'
      });
    });
    await randomDelay(CONFIG.delays.scroll, CONFIG.delays.scroll + 300);
  }
}

async function connectBrowser() {
  console.log(colors.cyan(`🚀 Lancement du navigateur ${CONFIG.headless ? '(headless)' : '(visible)'}...`));
  return await puppeteer.launch({
    headless: CONFIG.headless,
    executablePath: CONFIG.browserExecutable,
    defaultViewport: { width: 1280, height: 720 },
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-features=IsolateOrigins,site-per-process',
      '--disable-web-security'
    ]
  });
}

async function acceptCookies(page) {
  try {
    await page.waitForSelector('button[aria-label="Accepter les cookies"]', { timeout: 5000 });
    await randomDelay(500, 1000);
    await page.click('button[aria-label="Accepter les cookies"]');
    await randomDelay(1000, 1500);
  } catch {}
}

async function hasCaptcha(page) {
  try {
    const captchaSelectors = [
      'iframe[src*="recaptcha"]',
      'iframe[src*="captcha"]',
      'iframe[title*="reCAPTCHA"]',
      '#captcha-form',
      '.g-recaptcha',
      '[data-callback*="captcha"]'
    ];

    for (const selector of captchaSelectors) {
      const captchaElement = await page.$(selector);
      if (captchaElement) {
        const isVisible = await captchaElement.isVisible();
        if (isVisible) return true;
      }
    }

    const bodyText = await page.evaluate(() => document.body?.innerText || '');
    if (/vérifiez que vous êtes humain|prouvez que vous êtes|verify you are human/gi.test(bodyText)) {
      return true;
    }

    return false;
  } catch {
    return false;
  }
}

async function handleCaptchaIfNeeded(page, progressManager) {
  if (await hasCaptcha(page)) {
    progressManager.incrementCaptcha();
    progressManager.save();
    progressManager.saveToCSV();

    console.log(colors.bold.red('\n\n🤖 ═══════════════════════════════════════'));
    console.log(colors.bold.red('   CAPTCHA DÉTECTÉ - ARRÊT DU SCRIPT'));
    console.log(colors.bold.red('═══════════════════════════════════════\n'));

    console.log(colors.yellow(`📊 Progression actuelle :`));
    console.log(colors.white(`   • Offres scrappées : ${progressManager.data.jobOffers.length}`));
    console.log(colors.white(`   • Dernière page : ${progressManager.data.lastPage}`));
    console.log(colors.white(`   • Captchas rencontrés : ${progressManager.data.captchaCount}`));

    console.log(colors.cyan('\n📝 Instructions :'));
    console.log(colors.white('   1. Résous le captcha dans le navigateur'));
    console.log(colors.white('   2. Attends 2-3 minutes'));
    console.log(colors.white('   3. Relance le script'));
    console.log(colors.white('   4. Le scraping reprendra automatiquement\n'));

    console.log(colors.green(`💾 Données sauvegardées dans : ${CONFIG.outputPath}\n`));

    process.exit(0);
  }
  return false;
}

async function isPage404(page) {
  try {
    const content = await page.content();
    const title = await page.title();

    if (/404|not found|page introuvable|n'existe plus/gi.test(title)) {
      return true;
    }

    if (/cette offre n'est plus disponible|job.*no longer available/gi.test(content)) {
      return true;
    }

    return false;
  } catch {
    return false;
  }
}

async function extractJobDetails(jobTab, jobUrl) {
  try {
    const hasDescription = await jobTab.waitForSelector('#jobDescriptionText', { timeout: 8000 })
      .then(() => true)
      .catch(() => false);

    if (!hasDescription) {
      if (await isPage404(jobTab)) {
        logger.info(`Page 404 skippée: ${jobUrl}`);
        return null;
      }
      throw new Error('Description non trouvée');
    }

    await humanScroll(jobTab);
    await randomDelay(800, 1200);

    const jobDetails = await jobTab.evaluate(() => {
      const titleElement =
        document.querySelector('.jobsearch-JobInfoHeader-title') ||
        document.querySelector('h1') ||
        document.querySelector('[data-testid="jobsearch-JobInfoHeader-title"]');

      const companySelectors = [
        '.jobsearch-CompanyInfoContainer a',
        '[data-testid="inlineHeader-companyName"]',
        '[data-company-name]',
        '.jobsearch-CompanyInfoWithoutHeaderImage a',
        'div[data-testid="inlineHeader-companyName"] span'
      ];

      let companyElement = null;
      for (const selector of companySelectors) {
        companyElement = document.querySelector(selector);
        if (companyElement && companyElement.innerText.trim()) break;
      }

      const locationElement = document.querySelector('[data-testid="inlineHeader-companyLocation"]') ||
                             document.querySelector('.jobsearch-JobInfoHeader-subtitle div');

      const salaryElement = document.querySelector('.jobsearch-JobMetadataHeader-item') ||
                           document.querySelector('[data-testid="attribute_snippet_testid"]');

      const dateElement = document.querySelector('.jobsearch-JobMetadataFooter > div');

      const descriptionElement = document.querySelector('#jobDescriptionText');
      const fullDescription = descriptionElement?.innerText.trim() || '';

      let contractType = 'Non précisé';
      const contractMatch = fullDescription.match(/alternance|stage|CDI|CDD|freelance/gi);
      if (contractMatch) contractType = contractMatch[0];

      const isRemote = /télétravail|remote|distanciel|100% remote/gi.test(fullDescription);

      return {
        title: titleElement ? titleElement.innerText.trim() : '(titre absent)',
        company: companyElement ? companyElement.innerText.trim() : '(entreprise absente)',
        location: locationElement ? locationElement.innerText.trim() : 'Non précisé',
        salary: salaryElement ? salaryElement.innerText.trim() : 'Non précisé',
        contract: contractType,
        remote: isRemote ? 'Oui' : 'Non',
        publishedDate: dateElement ? dateElement.innerText.trim() : 'Non précisé',
        description: fullDescription
      };
    });

    jobDetails.url = jobUrl;
    return jobDetails;
  } catch (error) {
    logger.error(`Extraction échouée pour ${jobUrl}: ${error.message}`);
    return null;
  }
}

async function scrapeJob(browser, jobUrl, progressManager, progressBar) {
  if (progressManager.data.scrapedUrls.includes(jobUrl)) {
    return null;
  }

  const jobTab = await browser.newPage();

  try {
    const response = await jobTab.goto(jobUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 25000
    });

    if (!response || response.status() === 404) {
      logger.info(`404 détecté: ${jobUrl}`);
      await jobTab.close();
      progressBar.increment();
      return null;
    }

    await randomDelay(CONFIG.delays.betweenJobs, CONFIG.delays.betweenJobs + 1000);

    const currentUrl = jobTab.url();
    const siteDomain = new URL(CONFIG.baseUrl).hostname;

    if (!currentUrl.includes(siteDomain)) {
      await jobTab.close();
      progressBar.increment();
      return null;
    }

    const jobDetails = await extractJobDetails(jobTab, jobUrl);

    if (jobDetails) {
      progressManager.addJob(jobDetails);
      progressBar.increment();
      logger.success(`Scrappé: ${jobDetails.title} chez ${jobDetails.company}`);
    } else {
      progressBar.increment();
    }

    await jobTab.close();
    return jobDetails;

  } catch (error) {
    if (error.message.includes('Navigation timeout')) {
      logger.info(`Timeout sur ${jobUrl} - skip`);
    } else {
      logger.error(`Erreur scraping ${jobUrl}: ${error.message}`);
    }
    await jobTab.close();
    progressBar.increment();
    return null;
  }
}

async function scrapeJobsParallel(browser, jobLinks, progressManager, progressBar) {
  const results = [];

  for (let i = 0; i < jobLinks.length; i += CONFIG.parallelTabs) {
    const batch = jobLinks.slice(i, i + CONFIG.parallelTabs);

    const batchPromises = batch.map(jobUrl =>
      scrapeJob(browser, jobUrl, progressManager, progressBar)
    );

    const batchResults = await Promise.all(batchPromises);
    results.push(...batchResults.filter(job => job !== null));

    await randomDelay(2000, 3000);
  }

  return results;
}

async function scrapeCurrentPage(browser, page, progressManager, progressBar) {
  await humanScroll(page);
  await randomDelay(1500, 2000);

  if (await hasCaptcha(page)) {
    progressBar.stop();
    await handleCaptchaIfNeeded(page, progressManager);
    return false;
  }

  try {
    await page.waitForSelector('.job_seen_beacon h2 a', { timeout: 15000 });
  } catch {
    progressBar.stop();
    console.log(colors.yellow('⚠️  Aucune offre détectée sur cette page'));
    return false;
  }

  const jobLinks = await page.evaluate(() =>
    [...document.querySelectorAll('.job_seen_beacon h2 a')].map(link => link.href)
  );

  const newJobLinks = jobLinks.filter(url => !progressManager.data.scrapedUrls.includes(url));

  console.log(colors.cyan(`\n🔍 ${jobLinks.length} offres sur la page | ${newJobLinks.length} nouvelles à scraper`));

  if (newJobLinks.length > 0) {
    progressBar.setTotal(progressBar.getTotal() + newJobLinks.length);
    await scrapeJobsParallel(browser, newJobLinks, progressManager, progressBar);
  }

  return true;
}

async function goToNextPage(page) {
  const nextButton = await page.$('a[data-testid="pagination-page-next"]');
  if (!nextButton) return false;

  try {
    await humanScroll(page);
    await randomDelay(1500, 2000);

    await Promise.all([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 30000 }),
      nextButton.click()
    ]);

    await randomDelay(CONFIG.delays.betweenPages, CONFIG.delays.betweenPages + 2000);
    return true;
  } catch (error) {
    logger.error(`Navigation page suivante échouée: ${error.message}`);
    return false;
  }
}

async function main() {
  let browser = null;
  const progressManager = new ProgressManager(CONFIG.progressFile);

  console.log(colors.bold.cyan('\n🚀 SCRAPER D\'OFFRES D\'EMPLOI\n'));
  console.log(colors.gray('━'.repeat(50)));
  console.log(colors.white(`📍 Recherche: "${CONFIG.searchQuery}" à "${CONFIG.location}"`));
  console.log(colors.white(`🌐 Site: ${CONFIG.baseUrl}`));
  console.log(colors.white(`🔧 Config: ${CONFIG.parallelTabs} onglets | Max ${CONFIG.maxPages} pages`));
  console.log(colors.white(`💾 Sauvegarde automatique`));
  console.log(colors.gray('━'.repeat(50)));

  if (progressManager.data.jobOffers.length > 0) {
    console.log(colors.yellow(`\n⚠️  Progression: ${progressManager.data.jobOffers.length} offres | Page ${progressManager.data.lastPage}`));
    console.log(colors.yellow('Appuie sur ENTRÉE pour CONTINUER ou tape "reset" pour RECOMMENCER\n'));

    const choice = await new Promise(resolve => {
      process.stdin.once('data', data => resolve(data.toString().trim().toLowerCase()));
    });

    if (choice === 'reset') {
      progressManager.reset();
      console.log(colors.green('✅ Progression réinitialisée\n'));
    } else {
      console.log(colors.green('✅ Reprise du scraping...\n'));
    }
  }

  const progressBar = new cliProgress.SingleBar({
    format: colors.cyan('{bar}') + ' | {percentage}% | {value}/{total} offres | ETA: {eta}s',
    barCompleteChar: '█',
    barIncompleteChar: '░',
    hideCursor: true
  });

  progressBar.start(progressManager.data.jobOffers.length, progressManager.data.jobOffers.length);

  try {
    browser = await connectBrowser();
    const page = await browser.newPage();

    const searchUrl = `${CONFIG.baseUrl}${CONFIG.searchPath}?q=${encodeURIComponent(CONFIG.searchQuery)}&l=${encodeURIComponent(CONFIG.location)}`;
    await page.goto(searchUrl, { waitUntil: 'domcontentloaded' });

    await randomDelay(2000, 3000);
    await acceptCookies(page);

    if (await hasCaptcha(page)) {
      await handleCaptchaIfNeeded(page, progressManager);
    }

    let pageNumber = progressManager.data.lastPage + 1;

    for (let i = 1; i < pageNumber; i++) {
      const hasNext = await goToNextPage(page);
      if (!hasNext) break;
    }

    while (pageNumber <= CONFIG.maxPages) {
      console.log(colors.bold.cyan(`\n${'─'.repeat(50)}`));
      console.log(colors.bold.white(`📄 PAGE ${pageNumber}/${CONFIG.maxPages}`));
      console.log(colors.gray(`Offres totales: ${progressManager.data.jobOffers.length}`));
      console.log(colors.bold.cyan(`${'─'.repeat(50)}`));

      const shouldContinue = await scrapeCurrentPage(browser, page, progressManager, progressBar);
      if (!shouldContinue) break;

      progressManager.setLastPage(pageNumber);

      if (pageNumber < CONFIG.maxPages) {
        console.log(colors.yellow('\n⏳ Navigation vers la page suivante...'));
        const hasNextPage = await goToNextPage(page);
        if (!hasNextPage) {
          console.log(colors.yellow('⚠️  Pas de page suivante'));
          break;
        }
      }

      pageNumber++;
    }

    progressBar.stop();

    console.log(colors.bold.green('\n\n✅ SCRAPING TERMINÉ !\n'));
    console.log(colors.gray('━'.repeat(50)));
    console.log(colors.white(`📊 Statistiques:`));
    console.log(colors.white(`   • Offres trouvées: ${progressManager.data.jobOffers.length}`));
    console.log(colors.white(`   • Pages scrapées: ${pageNumber - 1}`));
    console.log(colors.white(`   • Captchas résolus: ${progressManager.data.captchaCount}`));
    console.log(colors.white(`   • Temps total: ${Math.round((Date.now() - progressManager.data.startTime) / 1000)}s`));
    console.log(colors.white(`   • Fichier: ${CONFIG.outputPath}`));
    console.log(colors.gray('━'.repeat(50)));

    if (fs.existsSync(CONFIG.progressFile)) {
      fs.unlinkSync(CONFIG.progressFile);
    }

  } catch (error) {
    progressBar.stop();
    logger.error(`Erreur fatale: ${error.message}`);
    console.log(colors.red(`\n❌ Erreur: ${error.message}`));
    console.log(colors.yellow(`💾 ${progressManager.data.jobOffers.length} offres sauvegardées dans ${CONFIG.outputPath}`));
    console.log(colors.cyan('👉 Relance le script pour continuer.\n'));
  } finally {
    if (browser) await browser.close();
  }
}

let gracefulShutdown = false;

process.on('SIGINT', async () => {
  if (gracefulShutdown) {
    console.log(colors.red('\n⚠️  Arrêt forcé !'));
    process.exit(1);
  }

  gracefulShutdown = true;

  console.log(colors.yellow('\n\n⚠️  ═══════════════════════════════════════'));
  console.log(colors.yellow('   ARRÊT EN COURS... (Ctrl+C pour forcer)'));
  console.log(colors.yellow('═══════════════════════════════════════\n'));

  console.log(colors.cyan('💾 Sauvegarde...'));

  const progressManager = new ProgressManager(CONFIG.progressFile);
  progressManager.saveToCSV();

  console.log(colors.bold.green('\n✅ DONNÉES SAUVEGARDÉES !\n'));
  console.log(colors.gray('━'.repeat(50)));
  console.log(colors.white(`📊 Statistiques:`));
  console.log(colors.white(`   • Offres: ${progressManager.data.jobOffers.length}`));
  console.log(colors.white(`   • Fichier: ${CONFIG.outputPath}`));
  console.log(colors.gray('━'.repeat(50)));
  console.log(colors.cyan('\n👉 Relance pour continuer!\n'));

  process.exit(0);
});

main();