import { build } from 'esbuild';
import { cpSync, mkdirSync } from 'node:fs';

await build({
  entryPoints: ['src/research.js'],
  bundle: true,
  format: 'iife',
  minify: true,
  sourcemap: false,
  target: ['es2020'],
  outfile: '../site/assets/finathink-research.js',
  legalComments: 'eof',
});

// KaTeX's HTML+MathML output remains readable without JavaScript. Vendor its
// stylesheet and fonts into the same local asset tree so the CSP never needs
// a CDN or network font request.
mkdirSync('../site/assets/katex/fonts', { recursive: true });
cpSync('node_modules/katex/dist/katex.min.css', '../site/assets/katex/katex.min.css');
cpSync('node_modules/katex/dist/fonts', '../site/assets/katex/fonts', { recursive: true });
