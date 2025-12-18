import os
import subprocess
import re

files = os.listdir()

# make html dir if does not exist
if not os.path.isdir('./html'):
    os.system('mkdir html')

# symlink fonts and images
if not os.path.isdir('./html/fonts'):
    os.system('cd html; ln -s ../fonts fonts; cd ../')
if not os.path.isdir('./html/images') and os.path.isdir('./images'):
    os.system('cd html; ln -s ../images images; cd ../')

# find all html files
nochange = {f for f in files if f[-5:]=='.html' or f[-4:]=='.css'}
templates = ['base-template.html']
nochange = nochange.difference(set(templates))

for f in nochange:
    os.system(f'cp {f} ./html/{f}')

# file names to convert to html
md = [f for f in files if f[-3:]=='.md']

with open(templates[0]) as f:
    template = f.read()

for f in md:
    #os.system(f'pandoc {f} -f markdown -t html -p -o ./html/{f[:-3]}.html')
    fragment = subprocess.check_output(['pandoc', f, '-f', 'markdown', '-t', 'html']).decode("utf-8")
    html = re.sub(r'<!-- replace here -->', fragment, template)
    with open(f'./html/{f[:-3]}.html', 'w') as outf:
        outf.write(html) 
