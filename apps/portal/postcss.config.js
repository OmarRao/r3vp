/*
 * PostCSS config so Next.js runs Tailwind (and autoprefixer) over globals.css.
 * Without this file Next.js does not process the @tailwind directives, so no
 * utility classes are generated and the semantic-token utilities used across
 * the app resolve to nothing. All required deps (tailwindcss, autoprefixer,
 * postcss) are already in package.json; only this config file was missing.
 */
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
