# WEEKLY V0.3 — Editorial feed engine

V0.3 convierte el lector en un primer **editor automático**, todavía sin IA externa.

### Nuevo

- RSS/Atom real mediante GitHub Actions.
- Extracción de imágenes desde RSS/Atom cuando el feed las expone.
- Normalización y deduplicación.
- Puntuación editorial heurística.
- Agrupación básica de historias relacionadas.
- Selección de hasta 24 historias.
- Diversidad por categoría.
- Revista que utiliza títulos, descripciones, imágenes y fuentes reales.
- Lector con enlace a la fuente original.

### Flujo

Feeds → GitHub Action → `articles.json` → ranking → clusters → selección → WEEKLY.

### Cómo actualizar

Reemplaza tu V0.2 por estos archivos en el mismo repositorio y haz push.

Después:
GitHub → Actions → **Update WEEKLY feeds and editorial selection** → **Run workflow**.

La Action también corre diariamente.

### Limitación deliberada

El "editor" de V0.3 es heurístico, no un modelo de IA. Esto permite probar el producto sin API keys ni costes.

El siguiente paso recomendado es V0.4:
- conectar un modelo de IA para resumir;
- detectar mejor que varias noticias hablan del mismo acontecimiento;
- generar un titular editorial;
- decidir el tipo de página/layout;
- generar una edición semanal real.
