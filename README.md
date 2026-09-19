# WEEKLY v0.9.22 — Editorial PDF

WEEKLY Personal Edition. Esta versión mantiene la base estable de v0.9.21 y mejora la salida PDF para que siga el mismo lenguaje editorial que el Reader web.

## Novedades
- PDF con portada, editorial, aperturas de sección, layouts editoriales de artículos, noticias breves y cierre.
- Una columna de lectura para el cuerpo de los artículos: párrafos completos y continuidad entre páginas.
- Jerarquía tipográfica, fondos claro/oscuro, etiquetas, numeración, running heads y bloques de OTRAS FUENTES.
- La portada fallback se dibuja directamente en PDF si no existe una imagen raster disponible.
- El PDF sigue asociado al issue cerrado y se genera una sola vez por edición.
- Interfaz de WEEKLY permanece en español; el contenido de las fuentes conserva su idioma original.

## Generación
El workflow instala `reportlab` y `pillow`, ejecuta `scripts_build_pdf.py` y publica `data/issues/issue-N.pdf` junto al snapshot del issue.
