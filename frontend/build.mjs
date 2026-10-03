import { build } from 'esbuild';

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
