// characters/static/characters/js/classsubclass_admin.js
window.addEventListener("DOMContentLoaded", () => {
    const base = document.getElementById("id_base_class");
    if (!base) return;
    base.addEventListener("change", function(){
      const url = new URL(window.location.href);
      url.searchParams.set("base_class", this.value);
      url.searchParams.delete("p");  // drop pagination
      window.location.href = url.toString();
    });
  });
  