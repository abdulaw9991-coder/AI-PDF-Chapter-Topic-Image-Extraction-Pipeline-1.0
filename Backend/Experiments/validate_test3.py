from pathlib import Path
import json
import os
from dotenv import load_dotenv
import fitz

repo_root = Path.cwd()
while not (repo_root / '.git').exists() and repo_root != repo_root.parent:
    repo_root = repo_root.parent

load_dotenv(repo_root / '.env')
pdf_path = os.getenv('PDF_PATH')
print('PDF_PATH from .env:', pdf_path)
if not pdf_path:
    raise ValueError('PDF_PATH must be set in .env')
pdf_path = Path(pdf_path)
if not pdf_path.is_absolute():
    pdf_path = repo_root / pdf_path
print('Resolved PDF path:', pdf_path)
print('PDF exists:', pdf_path.exists())

doc = fitz.open(str(pdf_path))
print('Total pages:', len(doc))

output_dir = repo_root / 'Backend' / 'Experiments' / 'test3_output'
output_dir.mkdir(parents=True, exist_ok=True)
pages_dir = output_dir / 'pages'
pages_dir.mkdir(parents=True, exist_ok=True)

schema_path = output_dir / 'page_text_schema.json'
markdown_path = output_dir / 'page_markdown.json'
headings_path = output_dir / 'heading_candidates.json'
docling_path = output_dir / 'book_docling.md'

page_documents = []
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    text = page.get_text('text')
    page_documents.append({'page': page_num + 1, 'text': text})
    (pages_dir / f'page_{page_num + 1}.md').write_text(f'# Page {page_num + 1}\n\n{text}', encoding='utf-8')

with open(schema_path, 'w', encoding='utf-8') as f:
    json.dump({'pdf_path': str(pdf_path), 'total_pages': len(doc), 'pages': page_documents}, f, indent=2, ensure_ascii=False)
with open(markdown_path, 'w', encoding='utf-8') as f:
    json.dump({'pdf_path': str(pdf_path), 'pages': [{'page': p['page'], 'markdown': f'# Page {p["page"]}\n\n{p["text"]}'} for p in page_documents]}, f, indent=2, ensure_ascii=False)
print('Stage 1 complete: schema and markdown files written')

try:
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    markdown = result.document.export_to_markdown()
    docling_path.write_text(markdown, encoding='utf-8')
    print('Stage 2 complete: Docling markdown saved')
except ImportError:
    print('Stage 2 skipped: Docling not installed')
except Exception as exc:
    print('Stage 2 failed:', exc)

heading_candidates = []
for page_num in range(len(doc)):
    page = doc.load_page(page_num)
    page_dict = page.get_text('dict')
    for block in page_dict.get('blocks', []):
        if 'lines' not in block:
            continue
        for line in block['lines']:
            line_text = ''.join(span.get('text', '') for span in line.get('spans', [])).strip()
            if not line_text:
                continue
            sizes = [span.get('size', 0) for span in line.get('spans', []) if span.get('text', '').strip()]
            if not sizes:
                continue
            max_size = max(sizes)
            if max_size >= 20:
                level = 'chapter'
            elif max_size >= 16:
                level = 'topic'
            elif max_size >= 12:
                level = 'subtopic'
            else:
                continue
            heading_candidates.append({'page': page_num + 1, 'text': line_text, 'level': level, 'max_font_size': max_size})

with open(headings_path, 'w', encoding='utf-8') as f:
    json.dump({'pdf_path': str(pdf_path), 'total_pages': len(doc), 'heading_candidates': heading_candidates}, f, indent=2, ensure_ascii=False)
print('Stage 3 complete: heading candidates written', len(heading_candidates))
print('Output files:')
print(' schema:', schema_path)
print(' markdown:', markdown_path)
print(' headings:', headings_path)
print(' docling:', docling_path)
print(' pages count:', len(list(pages_dir.glob('page_*.md'))))
