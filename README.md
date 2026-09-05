# WEEKLY V0.4 — Real AI editorial engine

Esta versión hace que WEEKLY sea realmente un producto funcional:

RSS/Atom → GitHub Actions → normalización → OpenAI → selección editorial → revista.

## 1. Configurar OpenAI

En tu repositorio de GitHub:

**Settings → Secrets and variables → Actions → New repository secret**

Nombre:

`OPENAI_API_KEY`

Valor:

tu API key de OpenAI.

La clave se usa exclusivamente dentro de GitHub Actions; NO está incluida en el frontend ni en el repositorio.

La aplicación usa la Responses API y Structured Outputs para pedir al modelo una selección JSON estructurada. OpenAI documenta la Responses API y el uso de claves mediante variables de entorno.

## 2. Ejecutar

Ve a:

GitHub → Actions → **Build WEEKLY issue → Run workflow**

El workflow:

1. descarga los feeds;
2. normaliza y deduplica;
3. extrae imágenes cuando están disponibles;
4. manda candidatos al editor IA;
5. selecciona 12–24 historias;
6. elige portada;
7. crea secciones;
8. genera `data/editorial.json`;
9. publica la edición en GitHub Pages.

También se ejecuta automáticamente cada domingo a las 08:00 UTC.

## 3. Modelo

V0.4 utiliza `gpt-5.6-luna`, orientado a cargas sensibles a coste. Puedes cambiarlo en `scripts_editor.py`.

## 4. Seguridad

Nunca pongas `OPENAI_API_KEY` en `app.js`, `index.html`, `data/*.json` ni en ningún archivo que llegue al navegador.

## 5. Qué queda para V0.5

- panel real para añadir/eliminar feeds sin editar JSON;
- Supabase para guardar configuración;
- resumen editorial de cada noticia;
- mejor clustering de noticias repetidas;
- layouts elegidos por IA;
- portada y spreads generados según contenido;
- generación automática semanal + histórico persistente.
