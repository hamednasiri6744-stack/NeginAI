/* Tool panels close explicitly, so scrollbar/focus events cannot dismiss a review. */
(() => {
  const editor = document.getElementById('checkbarDialog');
  if (!editor) return;
  const openedTools = () => [...editor.querySelectorAll('.checkbar-toolsbar > details[open]')];
  // Native <details> summaries (and the shared details name) handle toggling.
  // Scrollbars can target the dialog rather than the panel in desktop WebView2.
  editor.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const panels = openedTools();
    if (!panels.length) return;
    event.preventDefault();
    event.stopPropagation();
    panels.forEach(panel => { panel.open = false; });
    panels[0].querySelector('summary').focus();
  });
})();
