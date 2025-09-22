// static/characters/js/racialfeature_admin.js
(function () {
  function onReady(fn){ document.readyState !== "loading" ? fn() : document.addEventListener("DOMContentLoaded", fn); }
  onReady(function () {
    var race = document.getElementById("id_race");
    if (!race) return;

    race.addEventListener("change", function () {
      var val = race.value || "";
      var url = new URL(window.location.href);
      if (val) url.searchParams.set("race", val);
      else url.searchParams.delete("race");

      // Clear any stale subrace in the querystring
      url.searchParams.delete("subrace");
      // Avoid admin junk leaking into the URL
      url.searchParams.delete("_changelist_filters");

      // Reload so the server gives us the filtered Subrace queryset
      window.location.assign(url.toString());
    });
  });
})();
