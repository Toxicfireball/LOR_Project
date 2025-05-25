document.addEventListener('DOMContentLoaded', function() {
  // find the CharacterClass <select>
  var sel = document.getElementById('id_character_class');
var sel = document.getElementById('id_character_class');
if (sel) {
  sel.addEventListener('change', function() {
    // when you pick a class, rebuild the URL to include ?character_class=<id>
    var cls = encodeURIComponent(this.value);
    var url = window.location.pathname + '?character_class=' + cls;
    window.location.href = url;
  });
}
});
// static/characters/js/classlevel_admin.js

