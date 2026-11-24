"""Build the site: put the atlas metadata into the page template and copy the atlas next to index.html.
Run render_all.py first (it writes out/atlas.png and out/atlas.json)."""
import json, os, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, 'out')
tpl = open(os.path.join(ROOT, 'source', 'template.html')).read()
meta = json.load(open(os.path.join(OUT, 'atlas.json')))
assert tpl.count('__ATLAS__') == 1
html = tpl.replace('__ATLAS__', json.dumps(meta, separators=(',', ':')))
open(os.path.join(ROOT, 'index.html'), 'w').write(html)
shutil.copyfile(os.path.join(OUT, 'atlas.png'), os.path.join(ROOT, 'atlas.png'))
print('index.html', len(html), 'bytes; atlas.png copied')
