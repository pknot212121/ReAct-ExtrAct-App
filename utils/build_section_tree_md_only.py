import os
import re
import json
import argparse
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict

@dataclass
class HeadingNode:
    title: str
    level: int
    page: Optional[int]
    children: List['HeadingNode'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Rekurencyjna konwersja do słownika dla JSON."""
        return {
            'title': self.title,
            'level': self.level,
            'page': self.page,
            'children': [child.to_dict() for child in self.children]
        }

def parse_markdown_headings(md_text: str) -> List[HeadingNode]:
    """
    Ekstrahuje nagłówki Markdown, ignorując te zawarte w blokach kodu.
    Obsługuje znaczniki stron <!--PAGE:n-->.
    """
    page: Optional[int] = None
    headings: List[HeadingNode] = []

    # Regexy bardziej odporne na białe znaki
    page_rx = re.compile(r'^\s*<!--PAGE:\s*(\d+)\s*-->\s*$')
    header_rx = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
    code_block_rx = re.compile(r'^\s*(`{3,}|~{3,})')  # Wykrywa ``` lub ~~~

    in_code_block = False

    for line in md_text.splitlines():
        if code_block_rx.match(line):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        stripped = line.strip()
        if not stripped:
            continue

        mpage = page_rx.match(stripped)
        if mpage:
            try:
                page = int(mpage.group(1))
            except ValueError:
                pass
            continue

        mh = header_rx.match(line)
        if mh:
            level = len(mh.group(1))
            title = mh.group(2).strip()
            headings.append(HeadingNode(title=title, level=level, page=page))

    return headings


def build_tree_markdown_levels(headings: List[HeadingNode]) -> Dict[str, Any]:
    """
    Buduje drzewo z płaskiej listy nagłówków.
    """
    root = HeadingNode(title='ROOT', level=0, page=None)
    stack: List[HeadingNode] = []

    for h in headings:
        while stack and stack[-1].level >= h.level:
            stack.pop()

        parent = stack[-1] if stack else root
        parent.children.append(h)
        stack.append(h)

    return root.to_dict()


def write_json_tree(root_dict: Dict[str, Any], out_path: str) -> None:
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(root_dict, f, ensure_ascii=False, indent=2)
        print(f"Pomyślnie zapisano: {out_path}")
    except OSError as e:
        print(f"Błąd zapisu pliku: {e}")


def main():
    parser = argparse.ArgumentParser(description="Tworzy drzewo JSON z nagłówków pliku Markdown.")
    parser.add_argument("input_file", help="Ścieżka do pliku Markdown (.md)")
    parser.add_argument("-o", "--output", help="Opcjonalna ścieżka wyjściowa (domyślnie: obok pliku wejściowego)")
    parser.add_argument("--basename", help="Opcjonalna nazwa bazowa do struktury folderów (legacy mode)", default=None)

    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Błąd: Plik nie istnieje -> {input_path}")
        exit(1)

    # Wczytanie
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except Exception as e:
        print(f"Błąd odczytu pliku: {e}")
        exit(1)

    # Przetwarzanie
    headings = parse_markdown_headings(md_text)
    tree = build_tree_markdown_levels(headings)

    # Ustalanie ścieżki wyjściowej
    if args.output:
        out_path = args.output
    elif args.basename:
        # Tryb zgodności ze starym skryptem (hardcoded path)
        out_dir = os.path.join('storage', 'openrouter', f"{args.basename}_vector_index")
        out_path = os.path.join(out_dir, 'section_tree_md_only.json')
    else:
        # Domyślnie: zmień rozszerzenie pliku wejściowego na .json
        base, _ = os.path.splitext(input_path)
        out_path = base + "_tree.json"

    # Zapis
    write_json_tree(tree, out_path)
    print(f"Znaleziono nagłówków: {len(headings)}")


if __name__ == '__main__':
    main()

