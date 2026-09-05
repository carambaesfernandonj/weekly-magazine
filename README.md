# WEEKLY V0.2 — real RSS/Atom feeds

Esta versión mantiene la interfaz de V0.1, pero añade una primera capa de feeds reales.

## Cómo funciona

GitHub Pages no es un backend y muchos sitios bloquean las peticiones RSS directas desde el navegador por CORS. Por eso V0.2 usa GitHub Actions:

1. `data/feeds.json` contiene las fuentes.
2. Una GitHub Action ejecuta `scripts_fetch_rss.py`.
3. El script descarga RSS/Atom, normaliza artículos y escribe `data/articles.json`.
4. La Action hace commit del JSON.
5. GitHub Pages lee ese JSON y la revista muestra los artículos reales.

La Action corre diariamente y también puede ejecutarse manualmente desde GitHub → Actions.

## Fuentes iniciales

- The Verge — Atom
- IGN Games — RSS
- Ars Technica — RSS
- Wired — RSS

Puedes editar `data/feeds.json` para añadir tus propias fuentes.

## Importante

Esta versión todavía NO:
- agrupa noticias repetidas mediante IA;
- genera resúmenes;
- extrae imágenes automáticamente;
- genera una edición semanal de forma editorial;
- guarda fuentes añadidas desde la interfaz.

Eso será la siguiente capa. Para que el botón `+ Add Source` modifique fuentes persistentes desde la web necesitaremos una base de datos/backend, probablemente Supabase.

## Activar

Sube estos archivos al mismo repositorio de GitHub:

- `index.html`
- `style.css`
- `app.js`
- `data/feeds.json`
- `data/articles.json`
- `scripts_fetch_rss.py`
- `.github/workflows/update-feeds.yml`

Después entra en GitHub → Actions → **Update WEEKLY feeds** → **Run workflow**.

Cuando termine, GitHub Pages debería mostrar los artículos reales.

