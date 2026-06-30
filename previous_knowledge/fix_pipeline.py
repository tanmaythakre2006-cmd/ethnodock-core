import re

with open("core/pipeline.py", "r") as f:
    code = f.read()

# Make sure it doesn't inject fake text in pipeline.py
code = re.sub(
r'''    has_trusted = any\(r\.get\("is_trusted"\).*?if not has_trusted:.*?\}\)''',
'''    ''', code, flags=re.DOTALL)

with open("core/pipeline.py", "w") as f:
    f.write(code)
