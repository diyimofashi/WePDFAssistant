# LLM工具系统实现总结

## 概述

本次更新将极灵PDF项目的所有功能封装成了LLM工具,用户可以通过自然语言对话的方式使用所有PDF处理功能。

## 实现的功能

### 1. PDF文件操作工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `open_pdf` | 打开PDF文档 | file_path(可选,通过UI选择) |
| `save_pdf` | 保存PDF文档 | file_path(可选,通过UI选择) |

### 2. PDF编辑操作工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `insert_blank_page` | 插入空白页 | page_num(必填) |
| `delete_pages` | 删除页面 | page_nums(必填) |
| `rotate_page` | 旋转页面 | page_num(必填), rotation(必填) |
| `extract_pages` | 提取页面到新文件 | page_nums(必填), output_path(可选,通过UI选择) |
| `insert_pdf_page` | 从其他PDF插入页面 | page_num(必填), pdf_path(可选,通过UI选择) |
| `insert_image_page` | 插入图片页面 | page_num(必填), image_path(可选,通过UI选择) |

### 3. PDF批量操作工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `split_pdf` | 拆分PDF文档 | split_mode(可选), pages_per_file(可选), output_dir(可选,通过UI选择) |
| `merge_pdf` | 合并PDF文档 | input_files(必填), output_path(可选,通过UI选择) |

### 4. OCR功能工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `ocr_page` | OCR识别页面 | page_nums(可选), language(可选) |

### 5. 安全功能工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `encrypt_pdf` | 加密PDF文档 | password(必填), output_path(可选,通过UI选择) |

### 6. UI工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `show_message` | 显示消息通知 | message(必填), level(可选), title(可选) |
| `toggle_thumbnails` | 显示/隐藏缩略图 | show(可选) |
| `navigate_pdf` | 导航PDF文档 | action(必填), page_num(可选), zoom_level(可选) |

### 7. 系统工具

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `clear_cache` | 清理缓存 | 无 |
| `undo_operation` | 撤销操作 | 无 |
| `redo_operation` | 重做操作 | 无 |
| `search_text` | 搜索文本 | text(必填), case_sensitive(可选) |

## 核心设计特点

### 1. 所有参数定义为非必填

根据用户需求,所有工具的参数都定义为非必填(除了少数确实必需的参数):
- `required` 列表为空或只包含真正必须的参数
- 大多数文件路径参数通过UI选择器提供,用户无需手动输入

### 2. 智能参数验证

当LLM调用工具但缺少必需参数时:
- 系统会自动检测缺失的参数
- 根据参数类型自动弹出相应的Action Bubble:
  - 文件路径参数 → 文件选择器
  - 密码参数 → 密码输入框
  - 其他参数 → 通用输入框
- 用户完成输入后,自动继续执行工具

### 3. 空消息不显示

- 只有非空的内容才会在对话框中显示
- 参数收集等内部操作不会产生可见的消息
- 只有工具执行结果或错误信息才会显示给用户

### 4. 优雅的用户交互

- 所有文件选择使用统一的FileChooserWidget
- 保存操作和打开操作自动区分模式
- 用户友好的提示信息和错误处理

## 使用示例

### 示例1: 打开PDF文档

**用户输入**: "帮我打开一个PDF文档"

**系统行为**:
1. LLM决定调用 `open_pdf` 工具
2. 检测到缺少 `file_path` 参数
3. 弹出文件选择器让用户选择文件
4. 用户选择文件后,自动执行打开操作
5. 显示成功消息

### 示例2: 提取页面

**用户输入**: "把第1-3页提取出来"

**系统行为**:
1. LLM决定调用 `extract_pages` 工具,参数 `page_nums=[1,2,3]`
2. 检测到缺少 `output_path` 参数
3. 弹出文件选择器(保存模式)让用户选择输出位置
4. 用户选择路径后,自动执行提取操作
5. 显示成功消息

### 示例3: 合并PDF

**用户输入**: "合并这些PDF文件"

**系统行为**:
1. LLM识别需要 `input_files` 参数
2. 由于LLM无法知道具体文件,会提示用户提供更多信息
3. 或者用户可以先说"合并A.pdf和B.pdf",LLM可以处理

## 文件结构

```
app/core/llm/tools/
├── base_tool.py                    # 工具基类
├── tool_registry.py                # 工具注册中心
├── complete_pdf_tools.py           # 完整的PDF工具集(新增)
├── pdf_tools.py                    # 原有PDF工具
├── ui_tools.py                     # UI工具
├── ocr_tools.py                   # OCR工具
├── barcode_tools.py                # 条码工具
├── download_tools.py               # 下载工具
├── upload_tools.py                 # 上传工具
└── file_chooser_tool.py           # 文件选择工具

app/core/llm/tool_interactions/
├── interaction_handler.py          # 交互处理器
├── file_chooser.py                # 文件选择组件
└── config_dialog.py               # 参数配置对话框

app/managers/
└── llm_tool_manager.py            # 工具管理器(已更新)

app/ui/
├── llm_chat_widget.py              # LLM聊天组件(已更新)
└── chat_components/
    ├── action_bubble.py            # Action气泡组件
    └── message_bubble.py           # 消息气泡组件
```

## 技术实现细节

### 1. 工具注册

在 `llm_tool_manager.py` 中注册所有工具:

```python
def _register_default_tools(self):
    tools = [
        OpenPDFTool(),
        SavePDFTool(),
        InsertBlankPageTool(),
        # ... 更多工具
    ]
    for tool in tools:
        self._tool_registry.register_tool(tool)
```

### 2. 参数验证

工具基类提供参数完整性检查:

```python
def check_parameters_complete(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    schema = self.get_parameters_schema()
    required = schema.get("required", [])
    missing = []
    for param_name in required:
        if param_name not in params or not params[param_name]:
            missing.append(param_name)
    return len(missing) == 0, missing
```

### 3. Action Bubble处理

在 `_handle_tool_calls` 中检测缺失参数并弹出相应的UI:

```python
# 检查参数是否完整
complete, missing_params = tool.check_parameters_complete(arguments)
if not complete:
    # 为缺失的参数创建action bubble
    if 'path' in param_name or 'file' in param_name:
        self._add_action_bubble("file_chooser", {...})
    else:
        self._add_action_bubble("input", {...})
```

### 4. 空消息过滤

在 `_on_response` 中过滤空消息:

```python
elif content and content.strip():  # 只处理非空内容
    # 处理内容
```

在 `_on_action_completed` 中过滤参数补充消息:

```python
# 对于非必需参数的补充,不显示消息,直接继续
if result.get('success', True) and not result.get('error'):
    self._continue_after_action(action_type, result)
    return
```

## 测试建议

1. **基础功能测试**:
   - 测试打开、保存PDF
   - 测试导航功能(翻页、缩放)
   - 测试搜索功能

2. **编辑功能测试**:
   - 测试插入、删除页面
   - 测试旋转页面
   - 测试提取页面

3. **批量操作测试**:
   - 测试PDF拆分
   - 测试PDF合并

4. **OCR功能测试**:
   - 测试单页OCR
   - 测试多页OCR
   - 测试不同语言OCR

5. **参数验证测试**:
   - 测试缺少必需参数时的UI提示
   - 测试文件选择功能
   - 测试密码输入功能

6. **空消息测试**:
   - 验证空消息不在对话框显示
   - 验证参数收集过程静默进行

## 后续优化建议

1. **工具扩展**:
   - 可以继续添加更多PDF操作工具
   - 支持批量操作优化
   - 添加更多自定义参数选项

2. **用户体验**:
   - 添加工具执行进度显示
   - 优化错误提示信息
   - 添加工具使用历史记录

3. **性能优化**:
   - 优化工具调用响应速度
   - 添加缓存机制
   - 优化大文件处理

## 总结

本次实现完成了以下目标:

✅ 将所有PDF功能封装成LLM工具
✅ 所有参数定义为非必填(除少数必需参数)
✅ 实现智能参数验证和Action Bubble提示
✅ 实现空消息不显示
✅ 保持代码质量和可维护性

用户现在可以通过自然语言对话的方式使用极灵PDF的所有功能,大大降低了使用门槛,提升了用户体验。
