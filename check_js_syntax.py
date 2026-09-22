import os

js_files = ['static/js/app.js', 'static/js/faculty.js', 'static/js/admin.js', 'static/js/reports.js']

for f_path in js_files:
    with open(f_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check basic bracket balance
    stack = []
    lines = content.split('\n')
    errors = []
    for line_num, line in enumerate(lines, 1):
        # strip comments
        clean_line = line.split('//')[0]
        for ch in clean_line:
            if ch in '({[':
                stack.append((ch, line_num))
            elif ch in ')}]':
                if not stack:
                    errors.append(f"Extra closing '{ch}' at line {line_num}")
                else:
                    last_open, open_line = stack.pop()
                    matching = {')': '(', '}': '{', ']': '['}
                    if matching[ch] != last_open:
                        errors.append(f"Mismatched '{ch}' at line {line_num}, expected match for '{last_open}' from line {open_line}")
                        
    if stack:
        for ch, line_num in stack:
            errors.append(f"Unclosed '{ch}' opened at line {line_num}")
            
    if errors:
        print(f"[FAIL] {f_path} HAS ERRORS:")
        for e in errors:
            print(f"   {e}")
    else:
        print(f"[OK] {f_path} syntax/brackets balanced perfectly!")
