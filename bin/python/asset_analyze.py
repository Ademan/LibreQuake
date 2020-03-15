'''
A script that analyzes the LibreQuake asset list etherpad
Lists out what assets still are unaccounted for, what assets are
accounted for, and who has claimed them.
Then prints out the ratio of claimed assets to total assets.
Script written by ZungryWare
'''
import sys
import argparse
import traceback

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen

def fetch_to(f, url):
    resp = urlopen(url)
    for chunk in iter(lambda: resp.read(4096), ''):
        f.write(resp)

try:
    import html
    escape = html.escape
except ImportError:
    import cgi
    def escape(s):
        return cgi.escape(s, quote=True)

class TextFormatter(object):
    def __init__(self, f, console):
        self.f = f
        self.console = console

        if console:
            #Green text
            self.col = '\033[92m'
            self.end = '\033[0m'
        else:
            self.col = "**"
            self.end = "**"

    def print(self, s="", bold=False, end="\n"):
        if bold:
            self.f.write(self.col)
            self.f.write(str(s))
            self.f.write(self.end)
        else:
            self.f.write(str(s))

        if end:
            self.f.write(end)

class Asset(object):
    def __init__(self, name, authors, complete=False):
        self.name = name
        self.authors = authors
        self.complete = complete

    @classmethod
    def parse(cls, line):
        line = line.strip()
        if line[:3] != "pak" and line[:3] != "mus":
            raise ValueError("invalid asset line")

        tup = line.split(" - ", 1) 
        if len(tup) == 1:
            return cls(tup[0], "", False)
        elif len(tup) == 2:
            authors = tup[1].split(" & ")
            return cls(tup[0], authors, True)
        else:
            raise ValueError("invalid asset tuple")

class AssetList(object):
    def __init__(self, assets, complete_count):
        self.assets = assets
        self.complete_count = complete_count

    @classmethod
    def parse(cls, f):
        assets = []
        complete_count = 0
        lineno = 1
        for line in f:
            if line.startswith("//") or line.strip() == "":
                lineno += 1
                continue

            try:
                asset = Asset.parse(line)
                if asset.complete:
                    complete_count += 1
                assets.append(asset)
            except ValueError as e:
                sys.stderr.write("E: Line {}: {}\n".format(lineno, e))
            lineno += 1

        return cls(assets, complete_count)

    def complete_ratio(self):
        return float(self.complete_count) / len(self.assets)

def text_report(formatter, asset_list):
    formatter.print("LibreQuake Asset report:", bold=True)

    formatter.print()
    formatter.print("Items that are complete or in progress:", bold=True)
    for asset in asset_list.assets:
        if asset.complete:
            formatter.print(asset.name, bold=True, end=False)
            formatter.print(" is being accounted for by ", end=False)
            formatter.print(" & ".join(asset.authors), bold=True)

    #Go through the file, listing incomplete items
    formatter.print()
    formatter.print("Items that still need to be accounted for:", bold=True)
    for asset in asset_list.assets:
        if not asset.complete:
            formatter.print(asset.name, bold=True)

    #Go through the file again, listing complete items
    formatter.print()
    formatter.print("Items accounted for: ", end=False)
    formatter.print(asset_list.complete_count, end=False)
    formatter.print("/", end=False)
    formatter.print(len(asset_list.assets))

    percent = asset_list.complete_ratio() * 100
    percent_truncate = int(percent * 1000) / 1000.0

    formatter.print("We're ", end=False)
    formatter.print(percent_truncate, bold=True, end=False)
    formatter.print("%", bold=True, end=False)
    formatter.print(" of the way there!")

def html_report(f, asset_list):
    f.write("<style type=\"text/css\">"
            "tr.complete   { background-color: LightGreen ; }\n"
            "tr.incomplete { background-color: LightCoral ; }\n"
            "</style>")
    f.write("<table>"
            "<thead>"
            "<tr><td>Asset</td><td>Authors</td><td>Completed</td></tr>"
            "</thead>"
            "<tbody>")
    for asset in asset_list.assets:
        asset_class = "complete" if asset.complete else "incomplete"
        f.write("<tr class=\"{}\">".format(asset_class))
        f.write("<td>{}</td><td>{}</td><td>{}</td>".format(
            escape(asset.name),
            escape(" & ".join(asset.authors)),
            asset.complete
            ))
        f.write("</tr>")
    f.write("</tbody>")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="Output file (default stdout)")
    parser.add_argument("-a", "--assets", default="assets.txt", help="assets.txt file")
    parser.add_argument("-u", "--update", action="store_true", help="First update assets.txt")
    parser.add_argument("--update-url", default="https://scalar.vector.im/etherpad/p/r.81747c6955399b833c97b865e845cbed",)
    output_format = parser.add_mutually_exclusive_group()
    output_format.add_argument("-t", "--text-summary", default=True, action="store_true", help="Output text summary")
    output_format.add_argument("-g", "--github-table", default=False, action="store_true", help="Output github compatible markdown table summary")

    args = parser.parse_args()

    if args.update:
        if args.assets:
            with open(args.assets, "w") as f:
                fetch_to(f, args.update_url)
        else:
            fetch_to(sys.stdout, args.update_url)
            sys.stdout.flush()

    if args.assets == "-":
        asset_list = AssetList.parse(sys.stdin)
    else:
        with open(args.assets, "r") as f:
            asset_list = AssetList.parse(f)

    if args.github_table:
        if args.output is None:
            html_report(sys.stdout, asset_list)
            sys.stdout.flush()
        else:
            with open(args.output, "w") as f:
                html_report(f, asset_list)

    elif args.text_summary:
        if args.output is None:
            formatter = TextFormatter(sys.stdout, console=True)
            text_report(formatter, asset_list)
            sys.stdout.flush()
        else:
            with open(args.output, "w") as f:
                formatter = TextFormatter(f)
                text_report(formatter, asset_list)

if __name__ == "__main__":
    main()
