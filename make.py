# nobody can force me to write good code for my own bullshit, don't look at this
# all bugs 100% human generated

from ast import literal_eval
import os
import subprocess
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)


def dict_fill(txt: str, meta: dict) -> str:
    for k in meta:
        # filter out list elements, have to handle those differently if ever needed
        if not isinstance(meta[k], list):
            txt = re.sub("<!-- " + k + " -->", str(meta[k]), txt.strip())

    return txt


class Site:
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
        pd = p.glob("*")
        allfiles = [f for f in pd if f.is_file()]

        for d in self.incldirs:
            dp = p / d
            allfiles += [f for f in dp.glob("**/*") if f.is_file()]

        nochangeext = [".css", ".xml", ".ico", ".png", ".cur"]
        nochange = {f for f in allfiles if f.suffix in nochangeext}
        htmls = {f for f in allfiles if f.suffix == ".html"}
        templates_f = {Path(f) for f in htmls if "template" in str(f)}
        htmls = htmls.difference(templates_f)

        # print(f"nochange: {nochange}")
        # print(f"templates_f: {templates_f}")

        mdfiles = [Path(f) for f in allfiles if f.suffix == ".md"]
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
        if not os.path.isdir("./html"):
            os.system("mkdir html")
        for d in self.incldirs:
            d = Path(d)
            (Path("html") / d).mkdir()
            for path in d.glob("**/*"):
                target = Path("html") / path
                if path.is_dir():
                    target.mkdir()

        # symlink fonts and images
        if not os.path.isdir("./html/fonts"):
            os.system("cd html; ln -s ../fonts fonts; cd ../")
        if not os.path.isdir("./html/images") and os.path.isdir("./images"):
            os.system("cd html; ln -s ../images images; cd ../")

        for f in self.nochange:
            os.system(f"cp {f} ./html/{f}")

    def add_page(self, path):
        if isinstance(path, str):
            path = Path(path)

        self.pages.append(Page(path))

    def add_md(self, path, templates):
        if isinstance(path, str):
            path = Path(path)

        p = mdPage(path)

        if Path(str(path.parent) + "/" + p.meta["template"] + ".html") in templates:
            t = self.templates[
                Path(str(path.parent) + "/" + p.meta["template"] + ".html")
            ]
        elif Path(p.meta["template"] + ".html") in templates:
            t = self.templates[Path(p.meta["template"] + ".html")]
        else:
            raise KeyError(
                f"cannot find template file {p.meta['template'] + '.html'} specified in {path}"
            )

        p.build(t)

        self.pages.append(p)

    def build(self):
        self.make_output_structure()

        for page in self.pages:
            page.write(Path("./html/"))

        # process agg/gallery pages (just notes rn)
        notes_p = sorted(
            [p for p in self.pages if "notes" in str(p.path.parent)],
            key=lambda p: p.meta["date"],
            reverse=True,
        )
        # print([f"{p.meta['date']}: {p.meta['title']}" for p in notes_p])
        notesdiv = ""
        snip_template = Path("./notes/post-snip-template.html")
        for p in notes_p:
            # don't add to notes aggregate page if no-agg in meta
            if not "no-agg" in p.meta:
                notesdiv += dict_fill(self.templates[snip_template], p.meta)

        with open(f"./html/notes.html", "r+") as f:
            notes_html = f.read()
            notes_html = re.sub(r"<!-- postcards -->", notesdiv, notes_html)
            f.seek(0)
            f.write(notes_html)
            f.truncate()


class Page:
    def __init__(self, path):
        if isinstance(path, str):
            path = Path(path)
        self.path = path
        self.type = self.path.suffix
        self.name = self.path.stem
        self.original = self.path.read_text()
        self.meta = self.get_metadata()

    def __str__(self):
        return self.name

    def get_html(self):
        return self.original

    def write(self, build_p):
        out_p = Path(str(build_p / self.path.parent / self.path.stem) + ".html")
        out_p.write_text(self.get_html())

        # print(f"wrote {self.path} -> {out_p}")

    def get_metadata(self):
        meta = dict()

        # get anyting inside of meta tags
        p = re.compile(
            r"<meta name\s?=\s?[\'\"](.*)[\'\"]\s+content\s?=\s?[\'\"](.*)[\'\"]\s*/>",
            re.MULTILINE,
        )
        matches = re.finditer(p, self.original)
        for m in matches:
            # check to see if meta element is a list
            if m.group(2)[0] == "[" and m.group(2)[-1] == "]":
                meta[m.group(1)] = m.group(2).split(", ")
            else:
                # if not list, just shove the entire thing into the dict
                meta[m.group(1)] = m.group(2)

        # add path to meta
        meta["path"] = "./" + str(self.path)

        # if no date, give default
        if "date" not in meta and not "published" in meta:
            meta["date"] = "2000-01-01"
        elif "date" not in meta and "published" in meta:
            meta["date"] = meta["published"]

        # try to get title from title tag, otherwise use file name
        try:
            meta["title"] = re.search(
                r"<title>\s*(.*)\s*<\/title>", self.original
            ).group(1)
        except Exception as e:
            print(
                f"cannot pull title from {self.path}, setting title to '{self.path.stem}'"
            )
            meta["title"] = str(self.path.stem)

        return meta


class mdPage(Page):
    def __init__(self, path):
        Page.__init__(self, path)
        self.built_html = None

    def get_html(self):
        return self.built_html

    def build(self, template):
        self.template = template
        # pandoc
        fragment = subprocess.check_output(
            ["pandoc", self.path, "-f", "markdown", "-t", "html"]
        ).decode("utf-8")
        html = re.sub(r"<!-- replace here -->", fragment, template)

        # subsitute out other things in metadata
        html = dict_fill(html, self.meta)

        self.built_html = html

    def get_metadata(self):
        txt = self.path.read_text()

        # SHOULD only be one match, assume that's true
        m = re.findall(r"^---\n([\s\S]*)\n---\s", txt)[0]

        if not m:
            return None

        meta = dict()
        # pull all values in form key: value
        for v in re.findall(r"^(.*):(?!\s*\n)\s*(.*$)", m, re.MULTILINE):
            meta[v[0]] = v[1]

        # pull all values in key: list form
        p = re.compile(r"^(.*)[:]\s*\n(?:\s*- .+\n)+", re.MULTILINE)
        l = re.finditer(p, m)
        for a in l:
            # remove the key line, rejoin together
            li = "\n".join(a.group(0).split("\n")[1:])

            # get list of anything after a dash on a line
            meta[a.group(1)] = re.findall(r"\s*-\s(.*)\n", li)

        # if no date, give default
        if "date" not in meta and not "published" in meta:
            meta["date"] = "2000-01-01"
        elif "date" not in meta and "published" in meta:
            meta["date"] = meta["published"]

        meta["path"] = re.sub(".md", ".html", "./" + str(self.path))

        return meta


if __name__ == "__main__":

    site = Site(".", ["notes"])
    # for p in site.pages:
    #     print(str(p))
    site.build()
