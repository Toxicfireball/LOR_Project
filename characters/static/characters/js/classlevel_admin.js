document.addEventListener('DOMContentLoaded', function() {
  const sel = document.getElementById('id_character_class');
  if (!sel) return;

  // OPTION A: compare against initial <select> value
  const initial = sel.value;

  sel.addEventListener('change', function() {
    const picked = this.value;
    // only reload if truly different from initial
    if (picked === initial) return;

    const params = new URLSearchParams(window.location.search);
    params.set('character_class', picked);
    window.location.search = params.toString();
  });
});
