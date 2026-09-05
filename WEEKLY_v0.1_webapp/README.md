# WEEKLY V0.1

Web app estática para experimentar con el concepto de una revista semanal de noticias, tecnología y videojuegos.

## Qué incluye

- Dashboard
- Gestión local de fuentes simuladas
- Selección de artículos
- Generación de una portada
- Lector de revista con doble página
- Navegación con botones y flechas del teclado
- Archivo de ediciones de ejemplo
- Diseño responsive para escritorio y móvil

## Ejecutar

No necesita servidor. Abre `index.html` directamente en el navegador.

Para publicarla en GitHub Pages:

1. Crea un repositorio.
2. Sube `index.html`, `style.css` y `app.js`.
3. En Settings → Pages, selecciona la rama principal y `/root`.
4. GitHub generará una URL pública.

## Próximo paso: RSS real

La V0.1 usa datos simulados deliberadamente. Para conectar feeds RSS reales conviene añadir un pequeño backend/serverless porque muchos feeds no permiten ser consultados directamente desde el navegador por CORS.

Arquitectura propuesta:

Browser → API/serverless → RSS/Atom → normalización → base de datos → editor → revista

Después podemos añadir:
- RSS/Atom real
- URLs concretas
- deduplicación de noticias
- extracción de imágenes
- resúmenes
- ranking editorial
- generación automática cada domingo
- archivo persistente de revistas
- Supabase para fuentes, artículos y ediciones
