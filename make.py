# nobody can force me to write good code for my own bullshit, don't look at this
# all bugs 100% human generated

import os
import subprocess
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)

def dict_fill(txt:str, meta:dict) -> str:
    for k in meta:
        txt = re.sub('<!-- ' + k + ' -->', meta[k], txt.strip())

    return txt

class Site():
    def __init__(self, homedir, incldirs):
        self.homedir = homedir
        self.incldirs = incldirs
        
        # get relevant file paths
        self.nochange, htmls, template_f, self.mdfiles = self.get_files()
        # print(self.nochange)

        # read in templates
        self.templates = self.read_templates(template_f)
                
        # process markdown files
        self.pages = []
        for p in htmls:
            self.add_page(p)

        for p in self.mdfiles:
            self.add_md(p, self.templates) 


    def get_files(self):
        p = Path(self.homedir)
        pd = p.glob('*')
        allfiles = [f for f in pd if f.is_file()]
        
        for d in self.incldirs:
            dp = p / d
            allfiles += [f for f in dp.glob('**/*') if f.is_file()]

        nochangeext = ['.css', '.xml', '.ico', '.png', '.cur']
        nochange = {f for f in allfiles if f.suffix in nochangeext}
        htmls = {f for f in allfiles if f.suffix == '.html'}
        templates_f = {Path(f) for f in htmls if 'template' in str(f)}
        htmls = htmls.difference(templates_f)
        
        # print(f"nochange: {nochange}")
        print(f"templates_f: {templates_f}")
        
        mdfiles = [Path(f) for f in allfiles if f.suffix =='.md']
        mdfiles.sort()

        return nochange, htmls, templates_f, mdfiles
    
    def read_templates(self, t_paths):
        templates = dict()
        for t in t_paths:
            if t in templates:
                logger.warning(f"overwriting template: {t}")
            templates[Path(t.name)] = t.read_text() 
            templates[t] = t.read_text()

        return templates
    
    def make_output_structure(self):
        if not os.path.isdir('./html'):
            os.system('mkdir html')
        for d in self.incldirs:
            d = Path(d)
            (Path('html') / d).mkdir()
            for path in d.glob("**/*"):
                target = Path('html') / path
                if path.is_dir():
                    target.mkdir()
        
        # symlink fonts and images
        if not os.path.isdir('./html/fonts'):
            os.system('cd html; ln -s ../fonts fonts; cd ../')
        if not os.path.isdir('./html/images') and os.path.isdir('./images'):
            os.system('cd html; ln -s ../images images; cd ../')
        
        for f in self.nochange:
            os.system(f'cp {f} ./html/{f}')

        
    def add_page(self, path):
        if isinstance(path, str):
            path = Path(path)

        self.pages.append(Page(path))

    def add_md(self, path, templates):
        if isinstance(path, str):
            path = Path(path)
        
        p = mdPage(path)

        if Path(str(path.parent) +  '/' + p.meta['template'] + '.html') in templates:
            t = self.templates[Path(str(path.parent) +  '/' + p.meta['template'] + '.html')]
        elif Path(p.meta['template'] + '.html') in templates:
            t = self.templates[Path(p.meta['template'] + '.html')]
        else:
            raise KeyError(f"cannot find template file {p.meta['template'] + '.html'} specified in {path}")

        p.build(t)

        self.pages.append(p)

    def build(self):
        self.make_output_structure()
        
        for page in self.pages:
            page.write(Path('./html/'))

        # process agg/gallery pages
        notes_p = [p for p in self.pages if str(p.path.parent) == 'notes']
        notesdiv = ''
        snip_template = Path('./notes/post-snip-template.html')
        for p in notes_p:
            notesdiv += dict_fill(self.templates[snip_template], p.meta)
        
        with open(f'./html/notes.html', 'r+') as f:
            notes_html = f.read()
            notes_html = re.sub(r'<!-- postcards -->', notesdiv, notes_html)
            f.seek(0)
            f.write(notes_html)
            f.truncate()

        

class Page():
    def __init__(self, path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path
        self.type = self.path.suffix
        self.name = self.path.stem
        self.original = self.path.read_text()

    def __str__(self):
        return self.name
        
    def get_html(self):
        return self.original

    def write(self, build_p):
        out_p = Path(str(build_p / self.path.parent / self.path.stem) + '.html')
        out_p.write_text(self.get_html())

        # print(f"wrote {self.path} -> {out_p}")

class mdPage(Page):
    def __init__(self, path):
        Page.__init__(self, path)
        self.built_html = None
        self.meta = self.get_metadata()

    def get_html(self):
        return self.built_html
        
    def build(self, template):
        self.template = template
        # pandoc
        fragment = subprocess.check_output(['pandoc', self.path, '-f', 'markdown', '-t', 'html']).decode("utf-8")
        html = re.sub(r'<!-- replace here -->', fragment, template)

        # subsitute out other things in metadata
        html = dict_fill(html, self.meta)

        self.built_html = html

    def get_metadata(self):
        txt = self.path.read_text()
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
        
        meta['path'] = re.sub('.md', '.html', './' + str(self.path))

        return meta


if __name__ == "__main__":

    site = Site('.', ['notes'])
    # for p in site.pages:
    #     print(str(p))
    site.build()
