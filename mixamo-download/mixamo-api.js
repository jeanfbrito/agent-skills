// Mixamo web-app API helpers. Execute this whole file with the Claude in
// Chrome javascript_tool inside a logged-in https://www.mixamo.com tab; it
// defines window.mixamo for later javascript_tool calls in the same tab
// (re-run it after any navigation or reload).
//
// Reverse-engineered from the Mixamo web app, not a public API. The bearer
// token comes from the page's own session (localStorage.access_token); nothing
// is typed or stored. Auth + search verified 2026-09-24. If export/monitor
// fail, capture the web app's own requests (read_network_requests while the
// user clicks Download once) and update this file.
window.mixamo = (() => {
  const headers = () => {
    const token = localStorage.access_token;
    if (!token) throw new Error("Not logged in to Mixamo (no localStorage.access_token)");
    return {
      Authorization: "Bearer " + token,
      "X-Api-Key": "mixamo2",
      Accept: "application/json",
      "Content-Type": "application/json",
    };
  };
  const api = async (path, init = {}) => {
    const response = await fetch("/api/v1" + path, { ...init, headers: headers() });
    if (!response.ok) throw new Error(`${init.method || "GET"} ${path} -> ${response.status}`);
    return response.json();
  };

  return {
    // The rig every export is retargeted onto (the character selected in the UI).
    async character() {
      const c = await api("/characters/primary");
      return { id: c.primary_character_id, name: c.primary_character_name };
    },

    // Names repeat across variants; the description is the distinguishing field.
    async search(query, page = 1) {
      const j = await api(`/products?page=${page}&limit=96&type=Motion&query=${encodeURIComponent(query)}`);
      return {
        total: j.pagination && j.pagination.num_results,
        items: j.results.map((x, i) => ({ i, id: x.id, name: x.name, description: x.description })),
      };
    },

    // Queue one export. Mixamo runs one export per character at a time, so
    // poll status() until it completes before starting the next.
    async startExport(productId, characterId, preferences = {}) {
      const product = await api(`/products/${productId}?similar=0&character_id=${characterId}`);
      const gms = product.details.gms_hash;
      // Bake every slider at its default value, as the UI does untouched.
      const params = (gms.params || []).map((p) => p[1]).join(",");
      await api("/animations/export", {
        method: "POST",
        body: JSON.stringify({
          character_id: characterId,
          product_name: product.name,
          type: "Motion",
          preferences: { format: "fbx7", skin: "false", fps: "30", reducekf: "0", ...preferences },
          gms_hash: [{ ...gms, params }],
        }),
      });
      return { name: product.name, description: product.description };
    },

    // { status: "processing" | "completed" | "failed", job_result: url when completed }
    async status(characterId) {
      return api(`/characters/${characterId}/monitor`);
    },

    // Save a completed export under a chosen name. A blob keeps the filename;
    // if the CDN blocks CORS, fall back to a plain link (server-chosen name).
    async download(url, filename) {
      let href = url;
      let blobUrl = null;
      try {
        const blob = await (await fetch(url)).blob();
        href = blobUrl = URL.createObjectURL(blob);
      } catch (error) {
        console.log("mixamo download: CORS fallback", error);
      }
      const a = document.createElement("a");
      a.href = href;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      if (blobUrl) setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
      return { filename, viaBlob: Boolean(blobUrl) };
    },
  };
})();
"mixamo helpers ready";
