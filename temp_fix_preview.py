import re

with open('app/plugins-barcode/advanced_barcode/split_logic.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复预览函数中的文件命名：为每个条码值独立计数
# 修复 preview_first_page_rule
content = re.sub(
    r'(def preview_first_page_rule.*?preview_groups = \[\]\n\s*file_index = 0)',
    r'\1\n        barcode_file_counts = {}',
    content,
    flags=re.DOTALL
)

# 替换 preview_first_page_rule 中的命名逻辑
content = re.sub(
    r'(            if barcode_value:\n\s*)formatted_index = f"\{file_index \+ 1:03d\}"\n\s*filename = f"\{clean_barcode\}_\{formatted_index\}\.pdf"\n\s*\n)',
    r'\1if barcode_value:\n                # 每个条码值从1开始独立计数\n                if barcode_value not in barcode_file_counts:\n                    barcode_file_counts[barcode_value] = 0\n                barcode_file_counts[barcode_value] += 1\n                file_count = barcode_file_counts[barcode_value]\n                filename = f"{clean_barcode}_{file_count:03d}.pdf"\n\n',
    content,
    flags=re.DOTALL
)

# 修复 preview_last_page_rule
content = re.sub(
    r'(def preview_last_page_rule.*?preview_groups = \[\]\n\s*file_index = 0)',
    r'\1\n        barcode_file_counts = {}',
    content,
    flags=re.DOTALL
)

# 替换 preview_last_page_rule 中的命名逻辑
content = re.sub(
    r'(\n\s*for group in groups:.*?pages = group\[.pages.\].*?barcode_value = group\[.barcode.\].*?clean_barcode = .*?\n\s*)formatted_index = f"\{file_index \+ 1:03d\}"\n\s*filename = f"\{clean_barcode\}_\{formatted_index\}\.pdf"',
    r'\1if barcode_value:\n                # 每个条码值从1开始独立计数\n                if barcode_value not in barcode_file_counts:\n                    barcode_file_counts[barcode_value] = 0\n                barcode_file_counts[barcode_value] += 1\n                file_count = barcode_file_counts[barcode_value]\n                filename = f"{clean_barcode}_{file_count:03d}.pdf"',
    content,
    flags=re.DOTALL
)

# 修复 preview_separator_page_rule
content = re.sub(
    r'(def preview_separator_page_rule.*?preview_groups = \[\]\n\s*file_index = 0)',
    r'\1\n        barcode_file_counts = {}',
    content,
    flags=re.DOTALL
)

# 替换 preview_separator_page_rule 中的命名逻辑
content = re.sub(
    r'(\n\s*for group in groups:.*?pages = group\[.pages.\].*?barcode_value = group\[.barcode.\].*?clean_barcode = .*?\n\s*)formatted_index = f"\{file_index \+ 1:03d\}"\n\s*filename = f"\{clean_barcode\}_\{formatted_index\}\.pdf"',
    r'\1if barcode_value:\n                # 每个条码值从1开始独立计数\n                if barcode_value not in barcode_file_counts:\n                    barcode_file_counts[barcode_value] = 0\n                barcode_file_counts[barcode_value] += 1\n                file_count = barcode_file_counts[barcode_value]\n                filename = f"{clean_barcode}_{file_count:03d}.pdf"',
    content,
    flags=re.DOTALL
)

with open('app/plugins-barcode/advanced_barcode/split_logic.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('预览函数修复完成')
