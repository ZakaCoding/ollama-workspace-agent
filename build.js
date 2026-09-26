const buildSection = document.querySelector('.build-section');
const replayButton = document.querySelector('.build-replay');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

if (buildSection && replayButton && !reduceMotion.matches) {
  document.documentElement.classList.add('motion-ready');

  const startBuild = () => {
    buildSection.classList.add('is-active');
  };

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        startBuild();
        observer.disconnect();
      }
    }, { threshold: 0.22 });
    observer.observe(buildSection);
  } else {
    startBuild();
  }

  replayButton.addEventListener('click', () => {
    buildSection.classList.remove('is-active');
    void buildSection.offsetWidth;
    startBuild();
  });
}
