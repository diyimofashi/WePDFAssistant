# LLM 工具使用场景完整文档

## 概述

本文档详细列出了所有 LLM 可用的工具及其使用场景、参数要求和执行流程。

---

## 工具分类

### 1. 文件操作工具
- `open_pdf` - 打开 PDF 文档
- `save_pdf` - 保存 PDF 文档
- `download_file` - 下载文件
- `upload_file` - 上传文件

### 2. 导航工具
- `navigate_pdf` - PDF 页面导航

### 3. 文本工具
- `get_page_text` - 获取页面文本（支持 OCR）
- `search_text` - 在 PDF 中搜索文本

### 4. 编辑工具
- `insert_blank_page` - 插入空白页
- `delete_pages` - 删除页面
- `rotate_page` - 旋转页面
- `extract_pages` - 提取页面
- `insert_pdf_page` - 插入 PDF 页面
- `insert_image_page` - 插入图片页面

### 5. 合并拆分工具
- `split_pdf` - 拆分 PDF
- `merge_pdf` - 合并 PDF

### 6. OCR 工具
- `ocr_like_page` - 对指定页面执行 OCR
- `create_searchable_pdf` - 创建可搜索 PDF

### 7. 加密工具
- `encrypt_pdf` - 加密 PDF

### 8. 条码工具
- `barcode_split` - 按条码拆分 PDF

### 9. 系统工具
- `clear_cache` - 清理缓存
- `undo_operation` - 撤销操作
- `redo_operation` - 重做操作
- `show_thumbnail` - 显示缩略图

### 10. 交互工具
- `file_chooser` - 文件选择器
- `confirm` - 确认对话框
- `user_input` - 用户输入
- `show_message` - 显示消息

---

## 完整使用场景

---

## 场景 1: 打开 PDF 文档

**用户输入**: "打开文档"

### 执行流程

```
1. 用户输入："打开文档"
   ↓
2. _send_message() → _start_generation()
   ↓
3. LLM 分析意图，决定调用 open_pdf
   ↓
4. LLM 返回 tool_calls: [
     {"name": "open_pdf", "arguments": '{}'}
   ]
   ↓
5. _handle_tool_calls() 解析参数
   ↓
6. 检查参数完整性 → file_path 缺失
   ↓
7. 显示 file_chooser action bubble
   ↓
8. return，停止工具执行循环
   ↓
9. 用户选择文件：D:/Documents/test.pdf
   ↓
10. _on_action_completed("file_chooser", {"file_path": "D:/Documents/test.pdf"})
    ↓
11. 使用选择的文件路径重新执行 open_pdf
    ↓
12. 打开 PDF 文档成功
    ↓
13. _continue_after_action() → _start_generation()
    ↓
14. LLM 接收工具结果，生成响应："已为您打开文档：test.pdf"
    ↓
15. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `open_pdf`
- **必需参数**: `file_path` (string) - PDF 文件路径
- **参数来源**: 用户通过 file_chooser 选择
- **返回值**: `{"success": True, "file_path": "...", "page_count": 14}`

---

## 场景 2: PDF 页面导航

**用户输入**: "跳到最后一页" / "下一页" / "返回第一页"

### 执行流程

```
1. 用户输入："跳到最后一页"
   ↓
2. _send_message() → _start_generation()
   ↓
3. LLM 返回 tool_calls: [
     {"name": "navigate_pdf", "arguments": '{"action": "last_page"}'}
   ]
   ↓
4. _handle_tool_calls() 检查参数 → action = "last_page" (完整)
   ↓
5. 执行 navigate_pdf 工具
   ↓
6. PDF 导航到最后一页 (第 14 页)
   ↓
7. 结果添加到消息历史
   ↓
8. _start_generation()
   ↓
9. LLM 生成响应："已跳转到最后一页 (第 14 页)"
    ↓
10. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `navigate_pdf`
- **必需参数**: `action` (string) - 导航动作
- **可选参数**:
  - `action`: "next_page", "prev_page", "first_page", "last_page", "goto_page"
  - `page_num`: 目标页码 (仅 goto_page 时需要)
- **返回值**: `{"success": True, "current_page": 14, "message": "PDF导航: 最后一页(第14页)"}`

---

## 场景 3: 提取页面文本（含 OCR）

**用户输入**: "提取最后一页的文本"

### 执行流程

```
1. 用户输入："提取最后一页的文本"
   ↓
2. _send_message() → _start_generation()
   ↓
3. 系统自动添加文档上下文到 System Prompt：
   - 总页数: 14
   - 当前页: 1
   - 缩放比例: 1.50x
   - 文档名: test.pdf
   ↓
4. LLM 基于上下文返回 tool_calls: [
     {"name": "navigate_pdf", "arguments": '{"action": "last_page"}'},
     {"name": "get_page_text", "arguments": '{"page_number": 14}'}
   ]
   ↓
5. _handle_tool_calls() 执行第一个工具 navigate_pdf
   ↓
6. 导航到最后一页成功
   ↓
7. _handle_tool_calls() 执行第二个工具 get_page_text
   ↓
8. GetPageTextTool 检查是否有 OCR 数据 → 无
   ↓
9. 尝试提取 PDF 原生文本 → 无
   ↓
10. 调用 perform_ocr(page_index=13) 执行 OCR（使用与右键菜单相同的流程）
    ↓
11. OCR 识别成功，弹出对话框显示识别结果
    ↓
12. 用户关闭对话框,返回: {"success": True, "page_number": 14, "message": "第14页OCR识别完成"}
    ↓
13. 结果添加到消息历史
    ↓
14. _start_generation()
    ↓
15. LLM 基于工具结果生成响应："第14页OCR识别已完成"
    ↓
16. 创建 assistant bubble，显示响应
```

### 关键改进

**文档上下文带来的优势**：
- LLM 知道文档共14页，直接使用 page_number=14，而不是 -1
- 无需先查询总页数，提高效率
- 用户体验更流畅，响应更快

**OCR 流程统一**：
- `get_page_text` 工具使用 `main_window.perform_ocr()` 方法
- 与右键菜单"提取文本"使用完全相同的 OCR 流程
- 确保一致性：相同的插件、相同的识别方法、相同的结果格式

**OCR 识别结果显示**：
- OCR 识别成功后,弹出对话框显示识别结果
- 对话框与右键菜单的 OCR 结果对话框完全一致
- 工具只返回成功/失败状态,不返回 OCR 文本(用户已通过对话框看到)
- 如果是原生文本或缓存的 OCR 文本,工具会返回文本内容

### 工具信息

- **工具名称**: `get_page_text`
- **必需参数**: `page_number` (integer) - 页码
  - `1` = 第一页
  - `0` = 当前页
  - `-1` = 最后一页
- **自动 OCR**: 如果页面无文本，自动执行 OCR 并显示结果对话框
- **返回值**:
  - 原生文本: `{"success": True, "page_text": "...", "text_length": 58, "message": "..."}`
  - 新 OCR 识别: `{"success": True, "page_number": 14, "message": "第14页OCR识别完成"}`
  - 缓存的 OCR 文本: `{"success": True, "page_text": "...", "text_length": 58, "message": "..."}`

---

## 场景 4: 保存 PDF 文档

**用户输入**: "保存文档" / "另存为"

### 执行流程

```
1. 用户输入："另存为"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "save_pdf", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → output_path 缺失
   ↓
4. 显示 file_chooser action bubble (save_mode=True)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择保存路径：D:/Documents/saved.pdf
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/saved.pdf"})
    ↓
8. 使用选择的路径重新执行 save_pdf
    ↓
9. PDF 保存成功
    ↓
10. _continue_after_action() → _start_generation()
    ↓
11. LLM 生成响应："文档已保存到：saved.pdf"
    ↓
12. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `save_pdf`
- **必需参数**: `output_path` (string) - 保存路径
- **参数来源**: 用户通过 file_chooser 选择
- **返回值**: `{"success": True, "output_path": "...", "message": "PDF文档已保存"}`

---

## 场景 5: 删除页面

**用户输入**: "删除第 2 页" / "删除第 3-5 页"

### 执行流程

```
1. 用户输入："删除第 2 页"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "delete_pages", "arguments": '{"page_numbers": [2]}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → page_numbers = [2] (完整)
   ↓
4. 执行 delete_pages 工具
   ↓
5. 删除第 2 页成功
   ↓
6. 结果添加到消息历史
   ↓
7. _start_generation()
   ↓
8. LLM 生成响应："已删除第 2 页"
    ↓
9. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `delete_pages`
- **必需参数**: `page_numbers` (array) - 页码列表 (1-based)
- **示例**: `[1, 2]` 删除第 1-2 页，`[3]` 删除第 3 页
- **返回值**: `{"success": True, "deleted_count": 1, "remaining_pages": 13}`

---

## 场景 6: 旋转页面

**用户输入**: "把第 3 页旋转 90 度"

### 执行流程

```
1. 用户输入："把第 3 页旋转 90 度"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "rotate_page", "arguments": '{"page_number": 3, "angle": 90}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → page_number=3, angle=90 (完整)
   ↓
4. 执行 rotate_page 工具
   ↓
5. 第 3 页旋转 90 度成功
   ↓
6. 结果添加到消息历史
   ↓
7. _start_generation()
   ↓
8. LLM 生成响应："第 3 页已顺时针旋转 90 度"
    ↓
9. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `rotate_page`
- **必需参数**:
  - `page_number` (integer) - 页码 (1-based)
  - `angle` (integer) - 旋转角度 (90, 180, 270)
- **返回值**: `{"success": True, "page_number": 3, "angle": 90}`

---

## 场景 7: 插入图片页面

**用户输入**: "在第 5 页后面插入一张图片"

### 执行流程

```
1. 用户输入："在第 5 页后面插入一张图片"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "insert_image_page", "arguments": '{"page_number": 5}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → image_path 缺失
   ↓
4. 显示 file_chooser action bubble
   ↓
5. return，停止工具执行
   ↓
6. 用户选择图片：D:/Pictures/logo.png
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Pictures/logo.png"})
    ↓
8. 重新执行 insert_image_page(page_number=5, image_path="D:/Pictures/logo.png")
    ↓
9. 图片插入成功
    ↓
10. _continue_after_action() → _start_generation()
    ↓
11. LLM 生成响应："已在第 5 页后面插入图片：logo.png"
    ↓
12. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `insert_image_page`
- **必需参数**:
  - `page_number` (integer) - 在哪一页后面插入 (1-based)
  - `image_path` (string) - 图片路径
- **参数来源**: page_number 来自用户输入，image_path 通过 file_chooser 选择
- **返回值**: `{"success": True, "page_number": 5, "image_path": "..."}`

---

## 场景 8: 插入 PDF 页面

**用户输入**: "在当前页插入另一个 PDF 的第 3 页"

### 执行流程

```
1. 用户输入："在当前页插入另一个 PDF 的第 3 页"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "insert_pdf_page", "arguments": '{"page_number": 0}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → pdf_path 缺失
   ↓
4. 显示 file_chooser action bubble
   ↓
5. return，停止工具执行
   ↓
6. 用户选择 PDF：D:/Documents/other.pdf
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/other.pdf"})
    ↓
8. LLM 重新调用，明确指定要插入的页码：[
     {"name": "insert_pdf_page", "arguments": '{"page_number": 0, "pdf_path": "D:/Documents/other.pdf", "source_page": 3}'}
   ]
   ↓
9. 执行 insert_pdf_page 工具
    ↓
10. PDF 页面插入成功
    ↓
11. _start_generation()
    ↓
12. LLM 生成响应："已将 other.pdf 的第 3 页插入到当前文档"
    ↓
13. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `insert_pdf_page`
- **必需参数**:
  - `page_number` (integer) - 在哪一页后面插入 (1-based)
  - `pdf_path` (string) - 源 PDF 路径
  - `source_page` (integer) - 源 PDF 的页码 (1-based)
- **参数来源**: page_number 和 source_page 来自用户输入，pdf_path 通过 file_chooser 选择
- **返回值**: `{"success": True, "page_number": 3, "source_path": "..."}`

---

## 场景 9: 提取页面

**用户输入**: "提取第 2-5 页保存为单独的 PDF"

### 执行流程

```
1. 用户输入："提取第 2-5 页保存为单独的 PDF"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "extract_pages", "arguments": '{"page_numbers": [2, 3, 4, 5]}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → page_numbers 完整，output_path 缺失
   ↓
4. 显示 file_chooser action bubble (save_mode=True)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择保存路径：D:/Documents/extracted.pdf
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/extracted.pdf"})
    ↓
8. 重新执行 extract_pages(page_numbers=[2,3,4,5], output_path="D:/Documents/extracted.pdf")
    ↓
9. 页面提取成功
    ↓
10. _continue_after_action() → _start_generation()
    ↓
11. LLM 生成响应："已提取第 2-5 页，保存到：extracted.pdf"
    ↓
12. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `extract_pages`
- **必需参数**:
  - `page_numbers` (array) - 要提取的页码列表 (1-based)
  - `output_path` (string) - 保存路径
- **参数来源**: page_numbers 来自用户输入，output_path 通过 file_chooser 选择
- **返回值**: `{"success": True, "extracted_count": 4, "output_path": "..."}`

---

## 场景 10: 合并 PDF

**用户输入**: "把这两个 PDF 合并成一个" / "合并当前文档和另一个 PDF"

### 执行流程

```
1. 用户输入："把这两个 PDF 合并成一个"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "merge_pdf", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 source_paths 和 output_path
   ↓
4. 显示 file_chooser action bubble (save_mode=False)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择第一个 PDF：D:/Documents/doc1.pdf
   ↓
7. _on_action_completed() 提示继续选择第二个 PDF
   ↓
8. LLM 再次调用，包含第一个 PDF：[
     {"name": "merge_pdf", "arguments": '{"source_paths": ["D:/Documents/doc1.pdf"]}'}
   ]
   ↓
9. _handle_tool_calls() 检查参数 → 仍然缺少第二个 PDF 和 output_path
    ↓
10. 显示 file_chooser 选择第二个 PDF
    ↓
11. 用户选择：D:/Documents/doc2.pdf
    ↓
12. LLM 再次调用：[
     {"name": "merge_pdf", "arguments": '{"source_paths": ["doc1.pdf", "doc2.pdf"]}'}
   ]
    ↓
13. _handle_tool_calls() 检查参数 → 仍然缺少 output_path
    ↓
14. 显示 file_chooser (save_mode=True) 选择保存位置
    ↓
15. 用户选择：D:/Documents/merged.pdf
    ↓
16. 执行 merge_pdf 工具
    ↓
17. PDF 合并成功
    ↓
18. _start_generation()
    ↓
19. LLM 生成响应："已成功合并 doc1.pdf 和 doc2.pdf，保存到：merged.pdf"
    ↓
20. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `merge_pdf`
- **必需参数**:
  - `source_paths` (array) - 要合并的 PDF 路径列表
  - `output_path` (string) - 合并后的保存路径
- **参数来源**: 通过多次 file_chooser 选择
- **返回值**: `{"success": True, "merged_count": 2, "output_path": "..."}`

---

## 场景 11: 拆分 PDF

**用户输入**: "把这个 PDF 按页拆分成单独的文件" / "每 3 页拆分一次"

### 执行流程

```
1. 用户输入："把这个 PDF 按页拆分成单独的文件"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "split_pdf", "arguments": '{"split_mode": "all"}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 output_path
   ↓
4. 显示 file_chooser action bubble (选择输出目录)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择目录：D:/Documents/output/
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/output/"})
    ↓
8. 重新执行 split_pdf(split_mode="all", output_path="D:/Documents/output/")
    ↓
9. PDF 拆分成功
    ↓
10. _continue_after_action() → _start_generation()
    ↓
11. LLM 生成响应："已将 PDF 拆分为 14 个单独文件，保存到：output/"
    ↓
12. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `split_pdf`
- **必需参数**:
  - `split_mode` (string) - 拆分模式 ("all", "range", "interval")
  - `output_path` (string) - 输出目录路径
- **可选参数**:
  - `page_range`: 页面范围 (range 模式) [start, end]
  - `interval`: 间隔页数 (interval 模式)
- **参数来源**: split_mode 来自用户输入，output_path 通过 file_chooser 选择
- **返回值**: `{"success": True, "split_count": 14, "output_path": "..."}`

---

## 场景 12: 加密 PDF

**用户输入**: "加密这个 PDF" / "给文档设置密码"

### 执行流程

```
1. 用户输入："给文档设置密码"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "encrypt_pdf", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 password 和 output_path
   ↓
4. 显示 password action bubble
   ↓
5. return，停止工具执行
   ↓
6. 用户输入密码：123456
   ↓
7. _on_action_completed("password", {"password": "123456"})
    ↓
8. LLM 再次调用，包含密码：[
     {"name": "encrypt_pdf", "arguments": '{"password": "123456"}'}
   ]
   ↓
9. _handle_tool_calls() 检查参数 → 缺少 output_path
    ↓
10. 显示 file_chooser (save_mode=True)
    ↓
11. 用户选择：D:/Documents/encrypted.pdf
    ↓
12. 执行 encrypt_pdf(password="123456", output_path="D:/Documents/encrypted.pdf")
    ↓
13. PDF 加密成功
    ↓
14. _start_generation()
    ↓
15. LLM 生成响应："文档已加密，密码：123456，保存到：encrypted.pdf"
    ↓
16. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `encrypt_pdf`
- **必需参数**:
  - `password` (string) - 加密密码
  - `output_path` (string) - 加密后的保存路径
- **参数来源**: password 通过 password bubble 输入，output_path 通过 file_chooser 选择
- **返回值**: `{"success": True, "output_path": "...", "message": "PDF文档已加密"}`

---

## 场景 13: 搜索文本

**用户输入**: "搜索 '发票'" / "查找关键词"

### 执行流程

```
1. 用户输入："搜索 '发票'"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "search_text", "arguments": '{"query": "发票"}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → query="发票" (完整)
   ↓
4. 执行 search_text 工具
   ↓
5. 在整个 PDF 中搜索"发票"
   ↓
6. 找到 3 个匹配项
   ↓
7. 结果添加到消息历史
   ↓
8. _start_generation()
   ↓
9. LLM 生成响应："在文档中找到 3 个'发票'，分别在：第 2 页、第 5 页、第 8 页"
    ↓
10. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `search_text`
- **必需参数**:
  - `query` (string) - 搜索文本
- **可选参数**:
  - `case_sensitive` (boolean) - 是否区分大小写
  - `whole_word` (boolean) - 是否全词匹配
- **返回值**: `{"success": True, "matches": [...], "total_count": 3}`

---

## 场景 14: 执行 OCR

**用户输入**: "对第 3 页进行 OCR 识别" / "OCR 识别当前页"

### 执行流程

```
1. 用户输入："对第 3 页进行 OCR 识别"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "ocr_like_page", "arguments": '{"page_number": 3}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → page_number=3 (完整)
   ↓
4. 执行 ocr_like_page 工具
   ↓
5. OCR 识别开始...
   ↓
6. OCR 识别完成，提取文本
   ↓
7. 结果添加到消息历史
   ↓
8. _start_generation()
   ↓
9. LLM 生成响应："第 3 页 OCR 识别完成，提取到 156 个字符"
    ↓
10. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `ocr_like_page`
- **必需参数**: `page_number` (integer) - 页码 (1-based)
- **返回值**: `{"success": True, "text": "...", "text_length": 156}`

---

## 场景 15: 创建可搜索 PDF

**用户输入**: "创建可搜索 PDF" / "让 PDF 支持文本搜索"

### 执行流程

```
1. 用户输入："创建可搜索 PDF"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "create_searchable_pdf", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 output_path
   ↓
4. 显示 file_chooser action bubble (save_mode=True)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择保存路径：D:/Documents/searchable.pdf
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/searchable.pdf"})
    ↓
8. 重新执行 create_searchable_pdf(output_path="D:/Documents/searchable.pdf")
    ↓
9. 对所有页面执行 OCR
    ↓
10. 创建可搜索 PDF 成功
    ↓
11. _continue_after_action() → _start_generation()
    ↓
12. LLM 生成响应："已创建可搜索 PDF，保存到：searchable.pdf"
    ↓
13. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `create_searchable_pdf`
- **必需参数**: `output_path` (string) - 可搜索 PDF 的保存路径
- **参数来源**: 通过 file_chooser 选择
- **返回值**: `{"success": True, "output_path": "...", "ocr_pages": 14}`

---

## 场景 16: 显示/隐藏缩略图

**用户输入**: "显示缩略图" / "隐藏缩略图"

### 执行流程

```
1. 用户输入："显示缩略图"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "show_thumbnail", "arguments": '{"show": true}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → show=True (完整)
   ↓
4. 执行 show_thumbnail 工具
   ↓
5. 缩略图面板显示
   ↓
6. 结果添加到消息历史
   ↓
7. _start_generation()
   ↓
8. LLM 生成响应："缩略图面板已显示"
    ↓
9. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `show_thumbnail`
- **必需参数**: `show` (boolean) - true=显示, false=隐藏
- **返回值**: `{"success": True, "message": "缩略图面板已显示"}`

---

## 场景 17: 撤销/重做操作

**用户输入**: "撤销" / "重做" / "Ctrl+Z"

### 执行流程

```
1. 用户输入："撤销"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "undo_operation", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 无需参数 (完整)
   ↓
4. 执行 undo_operation 工具
   ↓
5. 操作撤销成功
   ↓
6. 结果添加到消息历史
   ↓
7. _start_generation()
   ↓
8. LLM 生成响应："已撤销上一步操作"
    ↓
9. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `undo_operation` / `redo_operation`
- **必需参数**: 无
- **返回值**: `{"success": True, "message": "操作已撤销"}`

---

## 场景 18: 清理缓存

**用户输入**: "清理缓存" / "释放内存"

### 执行流程

```
1. 用户输入："清理缓存"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "clear_cache", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 无需参数 (完整)
   ↓
4. 执行 clear_cache 工具
   ↓
5. 缓存清理成功，释放内存
   ↓
6. 结果添加到消息历史
   ↓
7. _start_generation()
   ↓
8. LLM 生成响应："缓存已清理，释放 125 MB 内存"
    ↓
9. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `clear_cache`
- **必需参数**: 无
- **返回值**: `{"success": True, "freed_memory": 125, "message": "缓存已清理"}`

---

## 场景 19: 条码拆分

**用户输入**: "按条码拆分文档"

### 执行流程

```
1. 用户输入："按条码拆分文档"
   ↓
2. LLM 返回 tool_calls: [
     {"name": "barcode_split", "arguments": '{}'}
   ]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 output_path
   ↓
4. 显示 file_chooser action bubble (选择输出目录)
   ↓
5. return，停止工具执行
   ↓
6. 用户选择目录：D:/Documents/barcode_output/
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/barcode_output/"})
    ↓
8. 重新执行 barcode_split(output_path="D:/Documents/barcode_output/")
    ↓
9. 条码检测和拆分开始...
   ↓
10. 检测到 5 个条码，拆分为 6 个文档
    ↓
11. _continue_after_action() → _start_generation()
    ↓
12. LLM 生成响应："按条码拆分完成，共拆分为 6 个文档，保存到：barcode_output/"
    ↓
13. 创建 assistant bubble，显示响应
```

### 工具信息

- **工具名称**: `barcode_split`
- **必需参数**: `output_path` (string) - 输出目录路径
- **参数来源**: 通过 file_chooser 选择
- **返回值**: `{"success": True, "split_count": 6, "barcodes_detected": 5, "output_path": "..."}`

---

## 参数处理策略总结

### 需要用户交互的参数

| 参数类型 | Action Bubble | 示例工具 |
|---------|--------------|----------|
| 文件路径 (打开) | `file_chooser` (save_mode=False) | `open_pdf`, `insert_pdf_page`, `insert_image_page` |
| 文件路径 (保存) | `file_chooser` (save_mode=True) | `save_pdf`, `extract_pages`, `merge_pdf`, `create_searchable_pdf` |
| 密码 | `password` | `encrypt_pdf` |
| 用户输入 | `input` | `confirm`, `user_input` |

### 参数处理流程

```
1. LLM 返回工具调用
   ↓
2. 检查参数完整性
   ↓
3. 如果参数不完整：
   a. 显示对应的 action bubble
   b. return 停止工具执行
   c. 等待用户完成交互
   d. 用户完成后重新执行工具
   ↓
4. 如果参数完整：
   a. 直接执行工具
   b. 结果添加到消息历史
   c. 继续下一个工具（如果有的话）
```

---

## 多工具执行模式

### 当前实现：批量执行

```
LLM 返回 [工具A, 工具B, 工具C]
   ↓
执行工具 A → 结果添加到历史
   ↓
执行工具 B → 结果添加到历史
   ↓
执行工具 C → 结果添加到历史
   ↓
_start_generation()
   ↓
LLM 基于所有结果生成最终响应
```

**适用场景**：
- 工具之间没有依赖关系
- LLM 能提前规划好所有需要的工具

**示例**：
- 导航 + 提取文本（navigate_pdf + get_page_text）
- 多个页面操作（rotate_page + rotate_page）

---

## 迭代式执行（未来可考虑）

```
LLM 返回 [工具A]
   ↓
执行工具 A → 结果添加到历史
   ↓
_start_generation()
   ↓
LLM 基于结果决定：是否需要工具B
   ↓
如果需要，LLM 返回 [工具B]
   ↓
执行工具 B → 结果添加到历史
   ↓
_start_generation()
   ↓
LLM 基于结果决定：是否需要工具C
```

**适用场景**：
- 工具之间有依赖关系
- 需要基于前一个工具的结果决定后续操作

**示例**：
- 提取文本 + 翻译（需要先提取文本才能翻译）
- OCR + 分析（需要先 OCR 才能分析）

---

## 总结

本文档涵盖了 19 个主要场景，包括：
- ✅ 文件操作（打开、保存、上传、下载）
- ✅ 导航（页面跳转）
- ✅ 文本处理（提取、搜索、OCR）
- ✅ 页面编辑（插入、删除、旋转、提取）
- ✅ 文档处理（合并、拆分）
- ✅ 安全（加密）
- ✅ 高级功能（条码拆分、可搜索 PDF）
- ✅ 系统操作（撤销、重做、清理缓存）

每个场景都包含完整的执行流程，从用户输入到最终响应，便于理解和调试。
