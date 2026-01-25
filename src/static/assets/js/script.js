const modal = document.querySelector('[data-modal]');
const modalCloseBtn = document.querySelector('[data-modal-close]');
const modalCloseOverlay = document.querySelector('[data-modal-overlay]');

const modalCloseFunc = function () { modal.classList.add('closed') }

// modal eventListener
modalCloseOverlay.addEventListener('click', modalCloseFunc);
modalCloseBtn.addEventListener('click', modalCloseFunc);

const mobileMenuOpenBtn = document.querySelectorAll('[data-mobile-menu-open-btn]');
const mobileMenu = document.querySelectorAll('[data-mobile-menu]');
const mobileMenuCloseBtn = document.querySelectorAll('[data-mobile-menu-close-btn]');
const overlay = document.querySelector('[data-overlay]');

const desktopCurrencySelector = document.getElementById('desktop-currency-selector');
if (desktopCurrencySelector) {

  desktopCurrencySelector.addEventListener('change', function() {
    const selectedCurrency = this.value;
    if (typeof window.switchCurrency === 'function') {
      window.switchCurrency(selectedCurrency);
    }
  });
}

for (let i = 0; i < mobileMenuOpenBtn.length; i++) {
  // guard missing elements
  if (!mobileMenu[i] || !mobileMenuOpenBtn[i]) continue;
  const mobileMenuCloseFunc = function () {
    if (mobileMenu[i]) mobileMenu[i].classList.remove('active');
    if (overlay) overlay.classList.remove('active');
  }

  mobileMenuOpenBtn[i].addEventListener('click', function () {
    if (mobileMenu[i]) mobileMenu[i].classList.add('active');
    if (overlay) overlay.classList.add('active');
  });

  if (mobileMenuCloseBtn[i]) mobileMenuCloseBtn[i].addEventListener('click', mobileMenuCloseFunc);
  if (overlay) overlay.addEventListener('click', mobileMenuCloseFunc);

}
const accordionBtn = document.querySelectorAll('[data-accordion-btn]');
const accordion = document.querySelectorAll('[data-accordion]');

for (let i = 0; i < accordionBtn.length; i++) {
  if (!accordionBtn[i]) continue;

  accordionBtn[i].addEventListener('click', function () {
    const panel = this.nextElementSibling;
    if (!panel) return;

    const clickedOpen = panel.classList.contains('active');

    for (let j = 0; j < accordion.length; j++) {
      if (clickedOpen) break;
      if (accordion[j].classList.contains('active')) {
        accordion[j].classList.remove('active');
        if (accordionBtn[j]) accordionBtn[j].classList.remove('active');
      }
    }

    panel.classList.toggle('active');
    this.classList.toggle('active');
  });
}

(function initInfiniteSlider() {
  try {
    const slider = document.querySelector('.slider-container');
    if (!slider) return;

    let items = Array.from(slider.querySelectorAll('.slider-item'));
    if (items.length < 2) return;

    const interval = 6000;
    let timer;
    let index = 1;

    // 1. Clone first & last for seamless loop
    const firstClone = items[0].cloneNode(true);
    const lastClone = items[items.length - 1].cloneNode(true);

    slider.appendChild(firstClone);
    slider.insertBefore(lastClone, items[0]);

    // Re-fetch items after cloning
    let allItems = slider.querySelectorAll('.slider-item');

    function scrollToIndex(i, smooth = true) {
      // refresh allItems in case layout changed
      allItems = slider.querySelectorAll('.slider-item');
      const target = allItems[i];
      if (!target) return;
      const targetLeft = target.offsetLeft;
      slider.scrollTo({ left: targetLeft, behavior: smooth ? 'smooth' : 'auto' });
    }

    function next() {
      if (!slider) return;

      // Move by one viewport width instead of relying on offsetLeft
      slider.scrollBy({ left: slider.clientWidth, behavior: 'smooth' });
      index++;
      console.debug('Slider next()', { index, allItemsLen: allItems.length, scrollLeft: slider.scrollLeft, clientWidth: slider.clientWidth });

      // Seamless jump when we've moved past the last real slide
      setTimeout(() => {
        allItems = slider.querySelectorAll('.slider-item');
        if (index >= allItems.length - 1) {
          index = 1;
          // Jump back instantly to the first real slide
          slider.scrollTo({ left: slider.clientWidth, behavior: 'auto' });
          console.debug('Slider jumped to start', { index });
        }
      }, 650);
    }

    function start() { stop(); timer = setInterval(next, interval); console.debug('Slider started'); }
    function stop() { if (timer) { clearInterval(timer); timer = null; console.debug('Slider stopped'); } }

    slider.addEventListener('mouseenter', stop);
    slider.addEventListener('mouseleave', start);
    slider.addEventListener('touchstart', stop, {passive:true});
    slider.addEventListener('touchend', start, {passive:true});

    window.addEventListener('resize', () => { scrollToIndex(index, false); });

    // Wait for images to load to compute offsets correctly
    function initPositionAndStart(){
      // re-calc sizing
      allItems = slider.querySelectorAll('.slider-item');
      index = 1;
      // Jump to the first real slide using client width to compute position
      slider.scrollTo({ left: slider.clientWidth, behavior: 'auto' });
      console.debug('Slider init', { items: allItems.length, clientWidth: slider.clientWidth, scrollWidth: slider.scrollWidth });
      // slight delay to allow layout
      setTimeout(() => { start(); }, 50);
    }

    if (document.readyState === 'complete') {
      initPositionAndStart();
    } else {
      window.addEventListener('load', initPositionAndStart);
    }

  } catch (err) {
    console.error('Slider init error:', err);
  }
})();

// Initialize scroll buttons for has-scrollbar elements
(function initScrollButtons() {
  try {
    const scrollableElements = document.querySelectorAll('.has-scrollbar');
    
    scrollableElements.forEach(element => {
      // Skip slider-container as it has its own auto-scroll logic
      if (element.classList.contains('slider-container')) return;
      
      // Create scroll buttons
      const leftBtn = document.createElement('button');
      leftBtn.className = 'scroll-button left';
      leftBtn.innerHTML = '‹';
      leftBtn.setAttribute('aria-label', 'Scroll left');
      
      const rightBtn = document.createElement('button');
      rightBtn.className = 'scroll-button right';
      rightBtn.innerHTML = '›';
      rightBtn.setAttribute('aria-label', 'Scroll right');
      
      element.appendChild(leftBtn);
      element.appendChild(rightBtn);
      
      // Function to update button visibility
      function updateButtonVisibility() {
        const scrollLeft = element.scrollLeft;
        const scrollWidth = element.scrollWidth;
        const clientWidth = element.clientWidth;
        
        console.debug('Scroll state:', { scrollLeft, scrollWidth, clientWidth });
        
        // Hide left button when at the beginning
        if (scrollLeft <= 0) {
          leftBtn.classList.add('hidden');
        } else {
          leftBtn.classList.remove('hidden');
        }
        
        // Hide right button when at the end
        if (scrollLeft >= scrollWidth - clientWidth - 5) {
          rightBtn.classList.add('hidden');
        } else {
          rightBtn.classList.remove('hidden');
        }
      }
      
      // Scroll left
      leftBtn.addEventListener('click', () => {
        element.scrollBy({ left: -300, behavior: 'smooth' });
      });
      
      // Scroll right
      rightBtn.addEventListener('click', () => {
        element.scrollBy({ left: 300, behavior: 'smooth' });
      });
      
      // Update button visibility on scroll
      element.addEventListener('scroll', updateButtonVisibility);
      
      // Update on resize
      window.addEventListener('resize', () => {
        updateButtonVisibility();
      });
      
      // Initial check - wait for images to load
      setTimeout(() => updateButtonVisibility(), 500);
    });
  } catch (err) {
    console.error('Scroll buttons init error:', err);
  }
})();

  
// Attach currency option clicks (works with switchCurrency defined in base.html)
document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.mobile-currency-option').forEach(function(el){
    el.addEventListener('click', function(e){
      e.preventDefault();
      var code = el.getAttribute('data-currency');
      if (typeof window.switchCurrency === 'function') {
        window.switchCurrency(code);
      }

    });
  });
});