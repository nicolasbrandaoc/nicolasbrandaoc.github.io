import re, os, glob, unicodedata
from datetime import datetime, timedelta

TRACKS = ['ccna', 'ccnp', 'ccie']
START = datetime(2026, 6, 27, 0, 0, 0)   # logo depois do ultimo post existente (2026-06-26)
STEP  = timedelta(hours=1)

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return re.sub(r'-+', '-', s)

items = []   # (track, domain_title, num, heading, path, raw_line)
for track in TRACKS:
    for path in sorted(glob.glob(f'_{track}/*.md')):
        src = open(path).read()
        fm = re.match(r'^---\n(.*?)\n---\n', src, re.S).group(1)
        dom = re.search(r'^title:\s*(.+)$', fm, re.M).group(1).strip().strip('"')
        for line in src.splitlines():
            m = re.match(r'^## (\d+\.\d+)\s+(.+)$', line)
            if m:
                items.append((track, dom, m.group(1), m.group(2).strip(), path, line))

print(f"Topicos encontrados: {len(items)}")
for t in TRACKS:
    print(f"  {t.upper()}: {sum(1 for i in items if i[0]==t)}")

# 1) gerar os posts
os.makedirs('_posts', exist_ok=True)
link_map = {}
for idx, (track, dom, num, head, path, raw) in enumerate(items):
    dt = START + idx * STEP
    slug = slugify(f"{track} {num} {head}")
    fname = f"_posts/{dt.strftime('%Y-%m-%d')}-{slug}.md"
    title = f"{track.upper()} {num} {head}"
    body = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {dt.strftime('%Y-%m-%d %H:%M:%S')} -0300\n"
        f"categories: [{track.upper()}, {dom}]\n"
        f"tags: [{track}]\n"
        "---\n"
    )
    open(fname, 'w').write(body)
    link_map[(path, raw)] = (f"/posts/{slug}/", num, head)

# 2) transformar os titulos das paginas de dominio em links
touched = set()
for (path, raw), (url, num, head) in link_map.items():
    src = open(path).read()
    new = f"## [{num} {head}]({{{{ '{url}' | relative_url }}}})"
    assert raw in src, f"nao achei: {raw}"
    src = src.replace(raw, new, 1)
    open(path, 'w').write(src)
    touched.add(path)

print(f"Posts criados: {len(link_map)}")
print(f"Paginas de dominio atualizadas: {len(touched)}")
print(f"Janela de datas: {START:%Y-%m-%d %H:%M} -> {(START + (len(items)-1)*STEP):%Y-%m-%d %H:%M}")
