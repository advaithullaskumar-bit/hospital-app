import os

path = r'hospital_app/backend_app/templates/backend_app/public_index.html'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_label = '<label style="display: block; margin-bottom: 0.5rem; font-weight: 700; color: #718096;">'
new_label = '<label style="display: block; margin-bottom: 0.5rem; font-weight: 700; color: #718096; text-align: center;">'

text = text.replace(old_label, new_label)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
