import re

# Read the file
cards_py = open('/home/clawdbot/.openclaw/workspace/product-card-generator/backend/app/api/v1/cards.py', 'r', encoding='utf-8').read()

# Fix the return statement - ensure proper closure
# Find the return block and fix closure
start = cards_py.find('return {')
if start > 0:
    # Find the end of the return block - look for closing  after start
    depth = 0
    end = -1
    for i in range(start, len(cards_py)):
        if cards_py[i] == '{':
            depth += 1
        elif cards_py[i] == '':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    
    if end > 0:
        # Replace the return block
        fixed = cards_py[:start] + '    return {\n        "image": base64.b64encode(result_bytes).decode(),\\n        "debug": debug_data\\n    ' + cards_py[end:]
    else:
        # No closing  found - just add closing
        fixed = cards_py[:start] + '    return {\n        "image": base64.b64encode(result_bytes).decode(),\\n        "debug": debug_data\\n    ' + cards_py[start+len('return {'):]
else:
    fixed = cards_py

# Write back
open('/home/clawdbot/.openclaw/workspace/product-card-generator/backend/app/api/v1/cards.py', 'w', encoding='utf-8').write(fixed)
print('Fixed return statement')