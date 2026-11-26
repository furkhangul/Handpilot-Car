const labScreen = document.querySelector('.lab-screen');
const gestureButtons = [...document.querySelectorAll('.gesture-button')];
const detectedGesture = document.querySelector('#detected-gesture');
const vehicleState = document.querySelector('#vehicle-state');
const confidenceValue = document.querySelector('#confidence-value');
const menuToggle = document.querySelector('.menu-toggle');
const mobileLinks = [...document.querySelectorAll('.mobile-nav a')];
const filterChips = [...document.querySelectorAll('.filter-chip')];
const heroV2 = document.querySelector('.hero-v2');
const heroObject = document.querySelector('.hero-v2__object');
const scrollMeter = document.querySelector('.scroll-meter i');
const cursorDot = document.querySelector('.cursor-dot');
const cursorRing = document.querySelector('.cursor-ring');
const remoteFragments = [...document.querySelectorAll('.remote-fragments i')];

let driveDirection = 'idle';

const gestureStates = {
  gas: { gesture: 'GAZ / YUMRUK', state: 'DÜZ İLERLİYOR', confidence: '%96,8' },
  left: { gesture: 'SOL / BAŞPARMAK', state: 'SOLA DÖNÜYOR', confidence: '%94,1' },
  right: { gesture: 'SAĞ / BAŞPARMAK', state: 'SAĞA DÖNÜYOR', confidence: '%95,3' },
  reverse: { gesture: 'GERİ / AÇIK AVUÇ', state: 'GERİYE GİDİYOR', confidence: '%98,7' }
};

function setGesture(gesture) {
  if (!labScreen || !gestureStates[gesture]) return;

  if (gesture === 'gas') driveDirection = 'forward';
  if (gesture === 'reverse') driveDirection = 'reverse';

  const handMap = document.querySelector('.hand-map');
  if (handMap) {
    handMap.dataset.gesture = gesture;
    const handLabel = handMap.querySelector('.hand-map__label');
    if (handLabel) handLabel.textContent = gesture === 'right' ? 'SAĞ EL · ELİN DIŞI' : 'SAĞ EL · AVUÇ İÇİ';
    const poseNames = { gas: 'kapalı yumruk', reverse: 'açık avuç', left: 'dört parmak kapalı, başparmak sola açık', right: 'dört parmak kapalı, başparmak sağa açık' };
    handMap.querySelector('title').textContent = `Sağ el — ${poseNames[gesture]}`;
  }
  const view = gestureStates[gesture];
  const turning = gesture === 'left' || gesture === 'right';
  const turningWhileStopped = turning && driveDirection === 'idle';

  labScreen.dataset.state = turningWhileStopped ? 'idle' : (turning && driveDirection === 'reverse' ? 'reverse' : gesture);
  labScreen.dataset.steering = gesture === 'left' || gesture === 'right' ? gesture : 'straight';
  detectedGesture.textContent = view.gesture;
  vehicleState.textContent = turningWhileStopped ? 'DURUYOR · GAZ VEYA GERİ SEÇ'
    : turning && driveDirection === 'reverse' ? (gesture === 'left' ? 'GERİYE SOLA DÖNÜYOR' : 'GERİYE SAĞA DÖNÜYOR')
    : view.state;
  confidenceValue.textContent = view.confidence;

  gestureButtons.forEach((button) => {
    const active = button.dataset.gesture === gesture;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}

gestureButtons.forEach((button) => {
  button.setAttribute('aria-pressed', 'false');
  button.addEventListener('click', () => setGesture(button.dataset.gesture));
});

document.addEventListener('keydown', (event) => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
  const shortcuts = { '1': 'gas', '2': 'left', '3': 'right', '4': 'reverse' };
  if (shortcuts[event.key]) setGesture(shortcuts[event.key]);
});

menuToggle?.addEventListener('click', () => {
  const open = document.body.classList.toggle('menu-open');
  menuToggle.setAttribute('aria-expanded', String(open));
  menuToggle.querySelector('.sr-only').textContent = open ? 'Menüyü kapat' : 'Menüyü aç';
});

mobileLinks.forEach((link) => link.addEventListener('click', () => {
  document.body.classList.remove('menu-open');
  menuToggle?.setAttribute('aria-expanded', 'false');
}));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -5% 0px' });

document.querySelectorAll('.reveal').forEach((element, index) => {
  element.style.transitionDelay = `${Math.min((index % 4) * 70, 210)}ms`;
  revealObserver.observe(element);
});

const sectionObserver = new IntersectionObserver((entries) => {
  const visible = entries
    .filter((entry) => entry.isIntersecting)
    .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

  if (!visible) return;
  const id = visible.target.id || 'top';
  filterChips.forEach((chip) => {
    chip.classList.toggle('is-active', chip.getAttribute('href') === `#${id}`);
  });
}, { threshold: [0.15, 0.35, 0.6], rootMargin: '-18% 0px -55% 0px' });

['top', 'experience', 'gestures', 'system', 'model', 'safety'].forEach((id) => {
  const section = id === 'top' ? document.querySelector('.hero') : document.getElementById(id);
  if (section) sectionObserver.observe(section);
});

// Wait for a user command before moving the vehicle.

const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
let scrollTicking = false;

function updateScrollMotion() {
  const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1);
  const pageProgress = clamp(window.scrollY / maxScroll);
  scrollMeter?.style.setProperty('transform', `scaleY(${pageProgress})`);

  if (heroV2) {
    const rect = heroV2.getBoundingClientRect();
    const travel = Math.max(heroV2.offsetHeight - window.innerHeight, 1);
    const progress = clamp(-rect.top / travel);
    const fade = 1 - clamp((progress - 0.5) / 0.28);
    const shutter = 100 - clamp((progress - 0.84) / 0.16) * 100;
    const breakProgress = clamp((progress - 0.12) / 0.66);

    heroV2.style.setProperty('--hero-left', `${progress * -19}vw`);
    heroV2.style.setProperty('--hero-right', `${progress * 19}vw`);
    heroV2.style.setProperty('--hero-scale', String(1 + progress * 0.09));
    heroV2.style.setProperty('--hero-y', `${progress * -1.5}vh`);
    heroV2.style.setProperty('--hero-fade', String(fade));
    heroV2.style.setProperty('--hero-shutter', `${shutter}%`);
    heroObject?.style.setProperty('--break-progress', String(breakProgress));
    heroObject?.style.setProperty('--break-left-x', `${breakProgress * -22}vw`);
    heroObject?.style.setProperty('--break-left-y', `${breakProgress * -7}vh`);
    heroObject?.style.setProperty('--break-left-r', `${breakProgress * -23}deg`);
    heroObject?.style.setProperty('--break-right-x', `${breakProgress * 22}vw`);
    heroObject?.style.setProperty('--break-right-y', `${breakProgress * 6}vh`);
    heroObject?.style.setProperty('--break-right-r', `${breakProgress * 24}deg`);
    heroObject?.style.setProperty('--crack-offset', String(540 * (1 - breakProgress)));

    const fragmentVectors = [
      [-108, -138, -110], [94, -124, 96], [-142, -18, -160],
      [126, 22, 120], [-82, 126, -72], [104, 146, 148]
    ];
    remoteFragments.forEach((fragment, index) => {
      const [x, y, rotation] = fragmentVectors[index];
      fragment.style.transform = `translate(${x * breakProgress}px, ${y * breakProgress}px) rotate(${rotation * breakProgress}deg) scale(${0.35 + breakProgress * 0.65})`;
    });
  }

  scrollTicking = false;
}

window.addEventListener('scroll', () => {
  if (scrollTicking) return;
  scrollTicking = true;
  requestAnimationFrame(updateScrollMotion);
}, { passive: true });
window.addEventListener('resize', updateScrollMotion);
updateScrollMotion();

if (heroV2 && heroObject && window.matchMedia('(pointer: fine)').matches) {
  heroV2.addEventListener('pointermove', (event) => {
    const rect = heroV2.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 22;
    const y = ((event.clientY - rect.top) / Math.min(rect.height, window.innerHeight) - 0.5) * 14;
    heroV2.style.setProperty('--hero-mouse-x', `${x}px`);
    heroV2.style.setProperty('--hero-mouse-y', `${y}px`);
  });
  heroV2.addEventListener('pointerleave', () => {
    heroV2.style.setProperty('--hero-mouse-x', '0px');
    heroV2.style.setProperty('--hero-mouse-y', '0px');
  });
}

document.querySelectorAll('.gesture-card').forEach((card) => {
  card.addEventListener('pointermove', (event) => {
    const visual = card.querySelector('.gesture-card__visual');
    if (!visual) return;
    const rect = visual.getBoundingClientRect();
    visual.style.setProperty('--card-x', `${event.clientX - rect.left - rect.width / 2}px`);
    visual.style.setProperty('--card-y', `${event.clientY - rect.top - rect.height / 2}px`);
  });
  card.addEventListener('pointerleave', () => {
    const visual = card.querySelector('.gesture-card__visual');
    visual?.style.setProperty('--card-x', '0px');
    visual?.style.setProperty('--card-y', '0px');
  });
});

if (cursorDot && cursorRing && window.matchMedia('(pointer: fine)').matches) {
  let pointerX = window.innerWidth / 2;
  let pointerY = window.innerHeight / 2;
  let ringX = pointerX;
  let ringY = pointerY;

  window.addEventListener('pointermove', (event) => {
    pointerX = event.clientX;
    pointerY = event.clientY;
    cursorDot.style.transform = `translate(${pointerX - 3}px, ${pointerY - 3}px)`;
  }, { passive: true });

  document.querySelectorAll('a, button, .gesture-card').forEach((element) => {
    element.addEventListener('pointerenter', () => document.body.classList.add('cursor-active'));
    element.addEventListener('pointerleave', () => document.body.classList.remove('cursor-active'));
  });

  const animateCursor = () => {
    ringX += (pointerX - ringX) * 0.16;
    ringY += (pointerY - ringY) * 0.16;
    cursorRing.style.transform = `translate(${ringX - cursorRing.offsetWidth / 2}px, ${ringY - cursorRing.offsetHeight / 2}px)`;
    requestAnimationFrame(animateCursor);
  };
  animateCursor();
}
