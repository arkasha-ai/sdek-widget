#!/usr/bin/env python3
import re, sys, html as html_mod

def escape(text):
    return html_mod.escape(text)

def inline(text):
    """Process inline markdown: bold, italic, code, links"""
    # code
    text = re.sub(r'`([^`]+)`', lambda m: f'<code>{escape(m.group(1))}</code>', text)
    # bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # italic
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    # links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text

def parse_table(lines):
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    
    if len(rows) < 2:
        return ''
    
    header = rows[0]
    # rows[1] is separator
    body = rows[2:] if len(rows) > 2 else []
    
    html = '<div class="table-wrap"><table>\n<thead><tr>'
    for cell in header:
        html += f'<th>{inline(cell)}</th>'
    html += '</tr></thead>\n<tbody>\n'
    for row in body:
        html += '<tr>'
        for cell in row:
            html += f'<td>{inline(cell)}</td>'
        html += '</tr>\n'
    html += '</tbody></table></div>\n'
    return html

def convert(md_text):
    lines = md_text.split('\n')
    html_parts = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Code block
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_content = '\n'.join(code_lines)
            is_ascii = any(c in code_content for c in '┌─┐│└┘├┤┬┴┼╔╗╚╝║═')
            escaped = escape(code_content)
            lang_class = f' class="language-{lang}"' if lang else ''
            html_parts.append(f'<pre><code{lang_class}>{escaped}</code></pre>\n')
            continue
        
        # Horizontal rule
        if re.match(r'^---+\s*$', line) or re.match(r'^===+\s*$', line):
            html_parts.append('<hr>\n')
            i += 1
            continue
        
        # Headers
        m = re.match(r'^(#{1,4})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            html_parts.append(f'<h{level}>{text}</h{level}>\n')
            i += 1
            continue
        
        # Table detection
        if '|' in line and line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            html_parts.append(parse_table(table_lines))
            continue
        
        # Blockquote
        if line.startswith('>'):
            bq_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                bq_lines.append(lines[i][1:].strip())
                i += 1
            content = '<br>'.join(inline(l) for l in bq_lines)
            html_parts.append(f'<blockquote>{content}</blockquote>\n')
            continue
        
        # Unordered list
        if re.match(r'^(\s*)[-*+]\s+', line):
            indent_level = len(re.match(r'^(\s*)', line).group(1)) // 2
            html_parts.append('<ul>\n')
            while i < len(lines) and re.match(r'^(\s*)[-*+]\s+', lines[i]):
                item_line = lines[i]
                text = re.sub(r'^\s*[-*+]\s+', '', item_line)
                html_parts.append(f'<li>{inline(text)}</li>\n')
                i += 1
            html_parts.append('</ul>\n')
            continue
        
        # Ordered list
        if re.match(r'^\d+\.\s+', line):
            html_parts.append('<ol>\n')
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                text = re.sub(r'^\d+\.\s+', '', lines[i])
                html_parts.append(f'<li>{inline(text)}</li>\n')
                i += 1
            html_parts.append('</ol>\n')
            continue
        
        # Empty line
        if line.strip() == '':
            html_parts.append('<div class="spacer"></div>\n')
            i += 1
            continue
        
        # Regular paragraph
        html_parts.append(f'<p>{inline(line)}</p>\n')
        i += 1
    
    return ''.join(html_parts)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13.5px;
    line-height: 1.7;
    color: #1a1a2e;
    background: #fff;
}

.content {
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 50px;
}

h1 {
    font-size: 24px;
    font-weight: 700;
    color: #6366f1;
    margin: 32px 0 12px;
    break-inside: avoid;
    break-after: avoid;
}

h2 {
    font-size: 18px;
    font-weight: 600;
    color: #1a1a2e;
    border-bottom: 2px solid #6366f1;
    padding-bottom: 6px;
    margin: 28px 0 10px;
    break-inside: avoid;
    break-after: avoid;
}

h3 {
    font-size: 15px;
    font-weight: 600;
    color: #2d2d5e;
    margin: 20px 0 8px;
    break-inside: avoid;
    break-after: avoid;
}

h4 {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6366f1;
    margin: 16px 0 6px;
    break-inside: avoid;
    break-after: avoid;
}

p {
    margin: 4px 0;
    color: #2d2d40;
}

a {
    color: #6366f1;
    text-decoration: none;
}

a:hover { text-decoration: underline; }

strong { font-weight: 600; color: #1a1a2e; }
em { font-style: italic; }

code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 11px;
    background: #f4f4f5;
    padding: 2px 5px;
    border-radius: 4px;
    color: #3730a3;
}

pre {
    background: #f4f4f5;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 10px 0;
    overflow-x: auto;
    break-inside: avoid;
    white-space: pre;
}

pre code {
    background: none;
    padding: 0;
    border-radius: 0;
    font-size: 11px;
    color: #1e1b4b;
    white-space: pre;
    word-wrap: normal;
}

ul, ol {
    padding-left: 22px;
    margin: 6px 0 6px 4px;
}

li {
    margin: 2px 0;
    color: #2d2d40;
}

li code { font-size: 11px; }

blockquote {
    border-left: 3px solid #6366f1;
    padding: 8px 16px;
    margin: 10px 0;
    background: #f5f3ff;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #4338ca;
}

.table-wrap {
    overflow-x: auto;
    margin: 12px 0;
    break-inside: avoid;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 12.5px;
    break-inside: avoid;
}

thead { background: #6366f1; color: white; }

th {
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
}

td {
    padding: 7px 12px;
    border-bottom: 1px solid #e4e4e7;
    vertical-align: top;
}

tbody tr:nth-child(even) { background: #fafafa; }
tbody tr:hover { background: #f0f0ff; }

hr {
    border: none;
    border-top: 1px solid #e4e4e7;
    margin: 20px 0;
}

.spacer { height: 2px; }

@media print {
    @page { margin: 15mm 18mm; }
    body { font-size: 12px; }
    .content { padding: 0; max-width: 100%; }
    h1 { font-size: 20px; }
    h2 { font-size: 16px; }
    a { color: #6366f1; }
    pre { font-size: 10px; }
    
    /* no header/footer */
    header, footer { display: none !important; }
}
"""

def main(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        md = f.read()
    
    body = convert(md)
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Архитектура: Портфолио-сайт</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="content">
{body}
</div>
</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML written to {output_path}")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
