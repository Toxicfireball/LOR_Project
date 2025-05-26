document.addEventListener('DOMContentLoaded', function() {
  const sel = document.getElementById('id_character_class');
  if (!sel) return;

  // capture the actual starting value
  const initial = sel.value;

  sel.addEventListener('change', function() {
    const picked = sel.value;
    // Only reload if it’s truly different
    if (picked === initial) return;

    // Build a new URL object to preserve any other params
    const url = new URL(window.location.href);
    url.searchParams.set('character_class', picked);

    // Navigate
    window.location.href = url.toString();
  });
});
