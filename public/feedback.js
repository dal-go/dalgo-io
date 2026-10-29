// Keep feedback independent from analytics consent and page content.
(() => {
  const button = document.querySelector('[data-feedback-launcher]');
  const embed = document.getElementById('site-feedback-widget');
  const ready = () => { if (button && typeof window.ImproveIt?.open === 'function') button.hidden = false; };
  embed?.addEventListener('load', ready, {once: true});
  ready();
  // Reserve the banner's measured footprint without reading or changing consent.
  const section = document.querySelector('.site-feedback');
  let banner;
  const measure = () => section?.style.setProperty('--feedback-overlay-h', `${banner?.getBoundingClientRect().height || 0}px`);
  const resize = new ResizeObserver(measure);
  const watchBanner = () => {
    const current = document.getElementById('ga-consent-banner');
    if (current === banner) return;
    if (banner) resize.unobserve(banner);
    banner = current;
    if (banner) resize.observe(banner);
    measure();
  };
  new MutationObserver(watchBanner).observe(document.body, {childList: true});
  watchBanner();
  button?.addEventListener('click', () => window.ImproveIt?.open());
})();
