---
name: csl-xiaopiu-design-draft-capture
description: 将 xiaopiu（小PIU）原型项目的全部或指定页面导出为本地完整设计稿截图（每页一张、无接缝、含页面树 manifest），供设计稿走查与 UI 审查子智能体按图识读。Use when the user asks to 导出原型截图/设计稿截图/导出设计稿/走查设计稿/原型页面拍照, or before dispatching csl-ui-design-reviewer for a xiaopiu prototype, or when a xiaopiu URL needs to be turned into per-page PNG files with a manifest.
---

# Xiaopiu Design Draft Capture

Export all (or selected) pages of a xiaopiu prototype project to local PNG files — one image per page, full canvas, no stitching seams — plus a `manifest.json` that maps each file to its page tree identity. The output is the standard input for design-draft review (识图型审查员按图提取规格).

Scope: xiaopiu only (`www.xiaopiu.com/web/byId?type=project&id=<projectId>`). Generic web-page screenshots are out of scope.

## Hard-won constraints (read first — every one was learned by breaking it)

Xiaopiu preview is a virtualized SPA that actively resists naive capture. These facts are non-negotiable:

1. **URL `activePage` does not drive the SPA.** Changing the query param does not switch pages. The only reliable switch is clicking the tree node: `li[data-key="<pageId>"]` → click its first child `div`. The URL staying unchanged after a successful click is normal — judge success by the canvas re-render, not the URL.
2. **Do not scroll to capture.** Window scrolling triggers xiaopiu's virtual-scroll countermeasures: the canvas repositions itself (`page.top` is rewritten), producing duplicated/overlapping content. Any capture plan that involves `window.scrollTo` or segment stitching WILL corrupt long pages. Use the canvas-flattening approach below instead — one screenshot per page, zero scrolling.
3. **The canvas is clamped by an inline `max-height` and `transform: scale(...)`** on `.pageContainer` (e.g. 73%/90% zoom, `max-height: 1419px`). Inline styles beat plain CSS, so the flattening CSS must use `!important` and must be re-applied after every page switch and viewport change (the app rewrites/re-creates things on those events).
4. **Sibling page copies exist.** `.pageContainer` also holds `.page.prev` / `.page.next` clones and a `.page-mask`; if left visible they bleed into the flattened document flow and duplicate content. Hide them.
5. **Fixed chrome overlays the top of the canvas** (header bar, side panels). Hide them for clean output; remember they exist because `.page.current` computes its position from them (y-offset 45px in default layout).
6. **IAB viewport limits**: width ≤ 3840, height ≤ 2160. Tall pages (3000px+) must be scaled to fit in ONE viewport — never scrolled.
7. **The tree is itself virtualized/folded**: folders (class `folder-layer`) may be collapsed after re-layout; before clicking a page node, re-expand folders whose class lost `unfold`, and verify `li[data-key="<id>"]` exists before clicking.
8. **Screenshots occasionally time out** (`browser 命令 screenshot 超时`): the render surface is busy. Wait ~2s and retry the same shot once; persistent failure → report the page as failed, never fabricate.
9. **State hygiene**: all capture CSS lives in injected `<style id="__capture_mode__">` / `<style id="__capture_scale__">` tags. Remove both and restore the viewport when done, so the user's browser tab returns to a usable state.
10. **Browser tooling**: all browser work goes through the `browser-use:control-browser` skill + `mcp__node_repl__js` (bootstrap every call — fresh kernel per call; recover the tab via `browser.tabs.list()` + verified id; never trust bindings from a previous call).

## Workflow

### 0. Bootstrap (every JS call)

Load `browser-use:control-browser` first. In every `mcp__node_repl__js` call: resolve the plugin root from `process.env.ZCODE_PLUGIN_ROOT` (fallback `CLAUDE_PLUGIN_ROOT`), import `<root>/scripts/browser-client.mjs`, `setupBrowserRuntime({globals: globalThis})`, then `agent.browsers.getForUrl("https://www.xiaopiu.com")` and recover the working tab from `browser.tabs.list()` (create one with `browser.tabs.new()` + `goto` on first run; set viewport 1920×1080).

### 1. Enumerate the page tree

Navigate to the project URL. The tree lives in the left panel:

```js
// expand all folders, then list pages
await tab.playwright.evaluate(() => {
  for (const k of ['1','7','16','17','18','19','20','11']) { // folder ids are project-specific; generic loop below also works
    const li = document.querySelector(`li[data-key="${k}"]`);
    if (li && li.className.includes('folder-layer') && !li.className.includes('unfold')) (li.querySelector('div')||li).click();
  }
});
// wait ~1500ms, then:
const tree = await tab.playwright.evaluate(() =>
  Array.from(document.querySelectorAll('li[data-key]'))
    .filter(l => l.className.includes('page-layer'))
    .map(l => ({ id: l.dataset.key, name: l.textContent.trim() }))
);
```

Cross-check `tree.length` against the panel's "N页" counter. If short, some folders are still folded — expand any `li.folder-layer:not(.unfold)` and re-list.

### 2. Capture one page (v7 single-shot recipe)

For each page: clear capture styles → ensure tree expanded → click the tree node → wait ~2000ms → apply flattening CSS → measure → fit-to-viewport scale → resize viewport → re-apply CSS → verify position → one clipped screenshot.

```js
const setStyleV7 = () => tab.playwright.evaluate(() => {
  let st = document.getElementById('__capture_mode__');
  if (!st) { st = document.createElement('style'); st.id = '__capture_mode__'; document.head.appendChild(st); }
  st.textContent = `
    header, .preview-lr-panel, .preview-page-panel, .preview-note-panel { display: none !important; }
    html, body { overflow: visible !important; height: auto !important; }
    .body-wrapper { margin-left: 0 !important; overflow: visible !important; height: auto !important; }
    .webpage-wrapper { overflow: visible !important; height: auto !important; }
    .pageContainer { transform: none !important; max-height: none !important; height: auto !important; overflow: visible !important; }
    .pageContainer .page.current { position: static !important; top: 0 !important; left: 0 !important; }
    .pageContainer .page:not(.current) { display: none !important; }
    .page-mask { display: none !important; }
  `;
});
const clearStyle = () => tab.playwright.evaluate(() => {
  document.getElementById('__capture_mode__')?.remove();
  document.getElementById('__capture_scale__')?.remove();
});

async function capturePage(tab, key, name, outDir, fs) {
  await clearStyle();
  await expandAllFolders(tab);            // see step 1
  await tab.playwright.waitForTimeout(400);
  await tab.playwright.evaluate((k) => {
    const li = document.querySelector(`li[data-key="${k}"]`);
    if (!li) throw new Error('node ' + k + ' not found');
    (li.querySelector('div') || li).click();
  }, String(key));
  await tab.playwright.waitForTimeout(2000);
  await setStyleV7();

  const m = await tab.playwright.evaluate(() => {
    const p = document.querySelector('.pageContainer .page.current');
    const r = p.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
  });

  // fit whole canvas into ONE viewport (no scrolling, ever)
  const s = Math.min(1, 2100 / m.h, 3800 / m.w);
  if (s < 1) {
    await tab.playwright.evaluate((sc) => {
      let st = document.getElementById('__capture_scale__');
      if (!st) { st = document.createElement('style'); st.id = '__capture_scale__'; document.head.appendChild(st); }
      st.textContent = `.pageContainer .page.current { transform: scale(${sc}) !important; transform-origin: top left !important; }`;
    }, s);
  }
  await tab.setViewportSize({
    width: Math.min(3840, Math.ceil(m.w * s) + 80),
    height: Math.min(2160, Math.ceil(m.h * s) + 40),
  });
  await tab.playwright.waitForTimeout(1200);
  await setStyleV7();                     // app rewrites styles on resize — re-apply
  await tab.playwright.waitForTimeout(600);

  const m2 = await tab.playwright.evaluate(() => {
    const p = document.querySelector('.pageContainer .page.current');
    const r = p.getBoundingClientRect();
    return { x: Math.round(r.x + scrollX), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) };
  });
  const bytes = await tab.screenshot({ clip: { x: m2.x, y: m2.y, width: m2.w, height: m2.h } });
  const out = `${outDir}/p${key}-${name}.png`;   // name: sanitize '/' → '_'
  fs.writeFileSync(out, Buffer.from(bytes));
  return { id: String(key), name, file: out, width: m2.w, height: m2.h, scale: +s.toFixed(3) };
}
```

Batching discipline: run pages in batches of ≤ 18 per `js` call (the 120s call limit allows ~5-6s/page); keep the capture function fully inline per call — global bindings do not survive across calls.

### 3. Emit manifest

Write `manifest.json` next to the images:

```json
{
  "source": { "platform": "xiaopiu", "projectId": "6a5ed463beff98027f24d64e", "urlTemplate": "https://www.xiaopiu.com/web/byId?type=project&id=6a5ed463beff98027f24d64e" },
  "capturedAt": "2026-10-10",
  "pages": [
    { "id": "149", "name": "入职办理-新增1", "file": "p149-入职办理-新增1.png", "width": 1281, "height": 2100, "scale": 0.667 }
  ]
}
```

`id` is the tree node key — it is also the navigation key an interactive reviewer needs to jump back to this exact page in the live prototype.

### 4. Selective export & completion

- Subset export: accept page ids/names or a whole folder branch; still enumerate the full tree first, then filter.
- Already-exported images: if the user points at an existing directory with a manifest, skip capture and hand it over as-is.
- On finish: `clearStyle()`, remove `__capture_scale__`, restore viewport (e.g. 1920×1080), and report the table of exported pages + any failed pages (with the error verbatim). Never silently drop a failed page.

## Quality bar

- One page = one PNG, full canvas visible, no duplicated bands, no chrome remnants, no stitched seams. If a stitch or scroll was involved anywhere, the output is wrong by definition.
- manifest must account for every page listed in the tree ("N页" counter). Missing pages are failures, not omissions.
- Never modify the prototype, the tree, or any page content — read-only capture.
