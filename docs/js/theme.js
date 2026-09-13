(function() {
  const toggleBtn = document.getElementById('theme-toggle');
  const htmlElement = document.documentElement;

  const savedTheme = localStorage.getItem('theme') || 'light';
  htmlElement.setAttribute('data-theme', savedTheme);
  updateButton(savedTheme);

  toggleBtn.addEventListener('click', () => {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    htmlElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateButton(newTheme);
  });

  function updateButton(theme) {
    const isDark = theme === 'dark';
    toggleBtn.setAttribute('aria-pressed', isDark);
    toggleBtn.textContent = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
  }
})();
