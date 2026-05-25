# nobody can force me to write good code for my own bullshit, don't look at this
# all bugs 100% human generated

import os
import subprocess
import re
from pathlib import Path

def get_meta(f:Path) -> str:
    txt = f.read_text()
    p = re.compile(r"^---\n([\s\S]*)\n---")
    m = p.search(txt)
    
    if not m:
        return None
    
    # SHOULD only be one match, assume that's true
    meta = dict()
    for l in m.group(1).split('\n'):
        try: 
            # print(l.split(r': '))
            meta[l.split(': ')[0]] = l.split(': ')[1]
        except IndexError as e:
            pass
    
    meta['path'] = re.sub('.md', '.html', './' + str(f))

    return meta

def fill_with_meta(txt:str, meta:dict) -> str:
    for k in meta:
        txt = re.sub('<!-- ' + k + ' -->', meta[k], txt.strip())

    return txt

cwd = Path.cwd()

include_subdirs = ['notes']

p = Path('.')
pd = p.glob('*')
files = [str(f) for f in pd if f.is_file()]

for d in include_subdirs:
    dp = p / d
    files += [str(f) for f in dp.glob('*')]

# make html dir structure if does not exist
if not os.path.isdir('./html'):
    os.system('mkdir html')
for d in include_subdirs:
    if not os.path.isdir('./html/' + d):
        os.system('mkdir html/' + d)

# symlink fonts and images
if not os.path.isdir('./html/fonts'):
    os.system('cd html; ln -s ../fonts fonts; cd ../')
if not os.path.isdir('./html/images') and os.path.isdir('./images'):
    os.system('cd html; ln -s ../images images; cd ../')

# find all html files
nochangeext = ['html', 'css', 'xml']
nochange = {f for f in files if f.split('.')[-1] in nochangeext}
templates_f = {Path(f) for f in nochange if 'template' in f}
nochange = nochange.difference(set(templates_f))

for f in nochange:
    os.system(f'cp {f} ./html/{f}')

# file names to convert to html
md = [Path(f) for f in files if f[-3:]=='.md']
md.sort()

# print(md)

# load templates
templates = dict()
for t in templates_f:
    templates[t] = t.read_text()

notesdiv = ''

for f in md:
    print(f)
    # get metadata from markdown file
    meta = get_meta(f)
    # print(meta)
    
    # pandoc, shove together
    fragment = subprocess.check_output(['pandoc', f, '-f', 'markdown', '-t', 'html']).decode("utf-8")
    html = re.sub(r'<!-- replace here -->', fragment, templates[Path(str(f.parent) +  '/' + meta['template'] + '.html')])

    # subsitute out other things in metadata
    html = fill_with_meta(html, meta)

    with open(f'./html/{f.parent / f.stem}.html', 'w') as outf:
        outf.write(html)

    # folder specific instructions
    folder = str(f).split('/')[0]

    if folder == "notes":
        # add to main notes page
       notesdiv += fill_with_meta(templates[Path('./notes/post-snip-template.html')], meta)

# finish notes page
with open(f'./html/notes.html', 'r+') as f:
    notes_html = f.read()
    notes_html = re.sub(r'<!-- postcards -->', notesdiv, notes_html)
    print(notes_html)
    f.seek(0)
    f.write(notes_html)
    f.truncate()

