# LLM 工具执行流程文档

## 概述

本文档详细描述了 LLM Chat Widget 中工具的完整执行流程，包括工具调用、执行、结果显示和对话继续等各个环节。

---

## 1. 工具调用触发流程

### 1.1 用户发送消息
```
用户输入消息 → 点击发送按钮 → _send_message() 被调用
```

### 1.2 准备生成
在 `_start_generation()` 方法中：
1. 设置生成状态：`self._is_generating = True`
2. 禁用发送按钮
3. **不预先创建 Assistant 气泡**：`self._current_assistant_bubble = None`
4. 准备发送给 LLM 的消息列表

**重要特性：自动添加文档上下文**

在发送给 LLM 的消息中，系统会自动添加当前文档的状态信息作为 System Prompt 的一部分：

```python
def _get_document_context(self) -> str:
    """获取当前文档的上下文信息"""
    # 获取总页数
    # 获取当前页码
    # 获取缩放比例
    # 获取文档名称
    # 获取是否加密
    # 获取文档加载状态
```

**文档上下文示例**：
```
总页数: 14
当前页: 1
缩放比例: 1.50x
文档名: test.pdf
是否加密: 否
文档状态: 已加载
```

**优势**：
- LLM 可以根据文档状态做出更准确的决策
- 例如：用户说"跳转到最后一页"，LLM 知道文档共14页，可以直接返回 page_number=14
- 无需先查询总页数再跳转，提高效率

### 1.3 发送消息到 LLM
- 将用户消息添加到 `self._messages`
- 调用 LLM API（如 OpenAI）
- 启动流式响应

**重要**：Assistant 气泡只在 LLM 返回有效内容时才创建，避免创建空气泡。

---

## 2. LLM 响应处理流程

### 2.1 流式响应回调 `_on_response()`

当 LLM 返回流式响应时，`_on_response()` 会被多次调用，每次收到部分内容。

**关键参数**：
- `content`: LLM 返回的文本内容
- `metadata`: 包含工具调用信息
- `is_complete`: 是否是最后一块响应

**处理逻辑**：
```python
def _on_response(self, content, metadata, is_complete):
    if metadata_has_tool_calls:
        # 处理工具调用
        self._handle_tool_calls(tool_calls)
    elif content and content.strip():
        # 正常文本内容，更新 assistant bubble
        self._current_assistant_bubble.update_content(...)
    
    if is_complete:
        # 响应完成，处理清理工作
        self._is_generating = False
        # 保存消息到历史
        # 如果内容为空，删除空白气泡
```

### 2.2 工具调用检测

检测 metadata 中的 `tool_calls` 字段：
```python
metadata_has_tool_calls = (
    metadata is not None and
    isinstance(metadata, dict) and
    metadata.get("tool_calls") is not None
)
```

---

## 3. 工具调用处理流程 `_handle_tool_calls()`

### 3.1 多工具执行策略

**当前实现：顺序执行所有工具**

当 LLM 同时返回多个工具调用时，系统会：
1. **遍历所有工具调用**（在 `for tool_call in tool_calls:` 循环中）
2. **逐个检查参数完整性**
3. **逐个执行工具**（所有工具都执行完成后再继续）
4. **将所有结果添加到消息历史**
5. **调用 `_start_generation()` 让 LLM 基于所有结果生成响应**

```python
def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]):
    # 遍历所有工具调用
    for tool_call in tool_calls:
        # 1. 解析工具名称和参数
        tool_name = tool_call.get("name")
        arguments = json.loads(tool_call.get("arguments", "{}"))

        # 2. 检查参数完整性
        complete, missing_params = tool.check_parameters_complete(arguments)

        if not complete:
            # 参数不完整，需要用户补充
            # 添加 action bubble 收集用户输入
            return  # 等待用户输入，停止执行后续工具

        # 3. 执行工具
        result = await self._execute_tool(tool_name, arguments)

        # 4. 将结果添加到消息历史
        self._messages.append(LLMMessage(
            role="user",
            content=f"工具 {tool_name} 执行结果: {json.dumps(result)}"
        ))

    # 所有工具执行完成后，继续对话
    self._start_generation()
```

### 3.2 工具执行顺序

**场景示例**：用户说"提取最后一页的文本"

```
LLM 返回：[
  {"name": "navigate_pdf", "arguments": '{"action": "last_page"}'},
  {"name": "get_page_text", "arguments": '{"page_number": -1}'}
]

执行顺序：
1. 执行 navigate_pdf → 返回 {"success": True, "current_page": 14}
2. 执行 get_page_text → 返回 {"success": True, "page_text": "...", "text_length": 58}

结果都添加到消息历史，LLM 基于结果生成最终响应。
```

### 3.3 参数不完整处理

当工具参数不完整时，根据缺失参数类型显示不同的 action bubble：

| 参数类型 | Action Type | 示例 |
|---------|-------------|------|
| 文件路径 | `file_chooser` | 选择 PDF 文件 |
| 密码 | `password` | 输入密码 |
| 用户输入 | `input` | 输入内容 |

**重要**：添加 action bubble 后，使用 `return` 停止工具执行循环，等待用户完成操作。

### 3.2 参数不完整处理

当工具参数不完整时，根据缺失参数类型显示不同的 action bubble：

| 参数类型 | Action Type | 示例 |
|---------|-------------|------|
| 文件路径 | `file_chooser` | 选择 PDF 文件 |
| 密码 | `password` | 输入密码 |
| 用户输入 | `input` | 输入内容 |

**重要**：添加 action bubble 后，使用 `return` 停止工具执行循环，等待用户完成操作。

### 3.3 用户操作完成回调 `_on_action_completed()`

当用户在 action bubble 中完成操作后：

```python
def _on_action_completed(self, action_type, result):
    if action_type == "file_chooser" and result.get('file_path'):
        # 使用选择的文件路径重新执行工具
        self._execute_tool_with_file_path(...)
    elif action_type == "password":
        # 使用密码重新执行工具
        self._execute_tool_with_password(...)
    else:
        # 其他操作，继续对话
        self._continue_after_action(action_type, result)
```

### 3.4 工具执行 `_execute_tool()`

```python
async def _execute_tool(self, tool_name: str, arguments: Dict):
    # 1. 获取工具实例
    tool = self._tool_manager.get_tool_registry().get_tool(tool_name)
    
    # 2. 检查是否需要在主线程执行
    if tool.requires_main_thread():
        # 在主线程同步执行
        result = tool.execute(arguments)
    else:
        # 异步执行
        result = await asyncio.to_thread(tool.execute, arguments)
    
    return result
```

---

## 4. 工具执行完成后流程

### 4.1 工具调用循环结束

所有工具调用完成后（`_handle_tool_calls` 的 for 循环结束）：

```python
# 所有工具调用执行完成后，继续对话让LLM生成响应
logger.debug("All tool calls completed, continuing conversation")
self._start_generation()
```

**重要**：
- **当前策略**：所有工具都执行完成后，才调用 `_start_generation()`
- 这样 LLM 可以基于所有工具的结果生成综合响应
- 适用于相互独立的工具（如导航+提取文本）

### 4.2 LLM 迭代式工具调用

**OpenAI 标准 Tool Calling 模式**：

理论上，LLM 的工具调用应该是迭代式的：
1. LLM 返回工具调用 A → 执行 A → 返回结果给 LLM
2. LLM 基于结果决定是否需要调用工具 B
3. 如果需要，返回工具调用 B → 执行 B → 返回结果给 LLM
4. 重复直到 LLM 决定不需要更多工具

**当前实现的简化**：

当前代码实现的是批量执行模式（一次性执行所有工具），这适用于：
- 工具之间没有依赖关系
- LLM 能提前规划好所有需要的工具

如果需要实现迭代式调用，需要修改为：
```python
# 只执行第一个工具
for i, tool_call in enumerate(tool_calls):
    if i == 0:
        result = await self._execute_tool(...)
        self._messages.append(...)
    else:
        # 后续工具不执行，让 LLM 决定是否需要
        break

# 让 LLM 基于第一个工具的结果决定下一步
self._start_generation()
```

### 4.3 重新启动生成

调用 `_start_generation()` 后：
1. 创建新的 Assistant Bubble
2. 将包含工具结果的消息发送给 LLM
3. LLM 基于工具结果生成最终响应

### 4.3 LLM 最终响应

LLM 收到工具结果后，会生成自然的文本响应，例如：
- **提取文本**：返回提取的文本内容
- **导航**：确认导航操作
- **操作完成**：总结操作结果

---

## 5. 特殊工具示例

### 5.1 GetPageTextTool

**流程**：
```
用户请求 → LLM 调用 get_page_text
         ↓
    检查页面是否有 OCR 数据
         ↓
    尝试提取 PDF 原生文本
         ↓
    如果没有文本，执行 OCR
         ↓
    返回: {"success": True, "page_text": "...", "text_length": 58, ...}
         ↓
    结果添加到消息历史
         ↓
    调用 _start_generation()
         ↓
    LLM 基于结果生成响应，返回提取的文本
```

**返回值结构**：
```python
{
    "success": True,
    "page_number": 14,
    "page_text": "提取的文本内容...",
    "text_length": 58,
    "is_ocr": True
}
```

### 5.2 NavigatePdfTool

**参数**：
- `action`: 操作类型（"next_page", "prev_page", "first_page", "last_page", "goto_page"）
- `page_num`: 目标页码（仅 goto_page 时使用）

**返回值**：
```python
{
    "success": True,
    "message": "PDF导航: 最后一页(第14页)",
    "current_page": 14
}
```

### 5.3 OpenPdfTool

**流程**：
```
用户请求打开 PDF → LLM 调用 open_pdf
             ↓
         检查参数 file_path
             ↓
    如果没有 file_path → 显示 file_chooser action bubble
             ↓
    用户选择文件 → 重新执行 open_pdf(file_path="D:/path/to/file.pdf")
             ↓
    打开 PDF 文档
             ↓
    返回成功结果
             ↓
    LLM 确认文档已打开
```

---

## 6. 消息历史管理

### 6.1 消息类型

| 角色 | 说明 | 示例 |
|-----|------|------|
| `user` | 用户输入 | "打开最后一页的文档" |
| `assistant` | LLM 响应 | "已为您打开第 14 页..." |
| `system` | 系统提示 | 工具使用说明 |

### 6.2 消息添加时机

1. **用户消息**：点击发送按钮时
2. **工具调用**：LLM 返回 tool_calls 时
3. **工具结果**：工具执行完成后
4. **LLM 响应**：流式响应完成后
5. **错误消息**：发生错误时

### 6.3 消息保存

通过 `SessionManager` 保存到会话：

```python
def _save_current_message(self, message: LLMMessage):
    if self._session_manager:
        self._session_manager.add_message(
            session_id=self._current_session_id,
            message=message
        )
```

---

## 7. 错误处理

### 7.1 工具执行错误

```python
try:
    result = await self._execute_tool(tool_name, arguments)
except Exception as e:
    error_msg = f"❌ 工具执行错误: {str(e)}"
    self._add_message_bubble("assistant", error_msg)
    self._save_current_message(LLMMessage(role="assistant", content=error_msg))
```

### 7.2 参数解析错误

```python
try:
    arguments = json.loads(arguments_str)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse arguments: {arguments_str}")
    arguments = {}  # 使用空参数
```

### 7.3 Assistant Bubble 为 None 错误

在访问 `_current_assistant_bubble` 之前检查：

```python
if self._current_assistant_bubble is not None:
    current_text = self._current_assistant_bubble._text_edit.toPlainText()
```

---

## 8. 界面更新规则

### 8.1 工具执行结果显示

**显示规则**：
- ❌ 不显示用户操作结果（如文件选择）
- ❌ 不显示工具名称（如 "✅ 工具 [navigate_pdf]"）
- ❌ 不显示成功消息（如 "执行完成"）
- ✅ 只在失败时显示错误信息
- ✅ LLM 最终响应包含实际内容

### 8.2 消息气泡样式

| 角色 | 位置 | 样式 |
|-----|------|------|
| `user` | 右侧 | 蓝色背景，自动换行 |
| `assistant` | 左侧 | 白色背景，自动换行 |
| `action` | 中间 | 特殊交互组件 |

---

## 9. 性能优化

### 9.1 工具执行超时

```python
result = asyncio.run_coroutine_threadsafe(
    self._execute_tool(tool_name, arguments), loop
).result(timeout=120)  # 耗时工具延长超时到2分钟
```

### 9.2 异步执行

- 非主线程工具：使用 `asyncio.to_thread` 异步执行
- 主线程工具：使用 `run_coroutine_threadsafe` 在主线程执行

### 9.3 消息去重

避免重复添加相同的工具调用到消息历史。

---

## 10. 关键代码文件

| 文件 | 说明 |
|-----|------|
| `app/ui/llm_chat_widget.py` | 主要 UI 和流程控制 |
| `app/managers/llm_tool_manager.py` | 工具注册和管理 |
| `app/core/llm/tools/base_tool.py` | 工具基类 |
| `app/core/llm/tools/system_tools.py` | 系统工具实现 |
| `app/managers/session_manager.py` | 会话管理 |
| `app/core/llm/llm_plugin_interface.py` | LLM 接口定义 |

---

## 11. 示例：完整对话流程

### 场景：用户要求"提取最后一页的文本"

```
1. 用户输入："提取最后一页的文本"
   ↓
2. _send_message() 创建 user message，调用 _start_generation()
   ↓
3. _start_generation() 不创建 bubble，等待 LLM 响应
   ↓
4. LLM 接收消息，决定调用工具
   ↓
5. LLM 返回 tool_calls: [
     {"name": "navigate_pdf", "arguments": '{"action": "last_page"}'},
     {"name": "get_page_text", "arguments": '{"page_number": -1}'}
   ]
   ↓
6. _on_response() 检测到 tool_calls，调用 _handle_tool_calls()
   ↓
7. _handle_tool_calls() 执行 navigate_pdf → 成功
   ↓
8. _handle_tool_calls() 执行 get_page_text
   ↓
   - 检查 OCR 数据 → 无
   - 提取原生文本 → 无
   - 执行 OCR → 成功，提取 58 字符
   - 返回: {"success": True, "page_text": "...", ...}
   ↓
9. 两个工具的结果都添加到消息历史
   ↓
10. 所有工具执行完成，调用 _start_generation()
    ↓
11. _start_generation() 不创建 bubble，等待 LLM 响应
    ↓
12. LLM 接收包含工具结果的上下文
    ↓
13. LLM 生成响应："第 14 页的文本内容如下：\n\n[提取的文本内容]"
    ↓
14. _on_response() 检测到 content，创建 assistant bubble
    ↓
15. _on_response() 更新 bubble 内容，显示 LLM 的最终响应
    ↓
16. 对话完成
```

### 场景：用户要求"打开文档"

```
1. 用户输入："打开文档"
   ↓
2. LLM 返回 tool_calls: [{"name": "open_pdf", "arguments": '{}'}]
   ↓
3. _handle_tool_calls() 检查参数 → 缺少 file_path
   ↓
4. 显示 file_chooser action bubble
   ↓
5. return，停止工具执行
   ↓
6. 用户选择文件：D:/Documents/test.pdf
   ↓
7. _on_action_completed("file_chooser", {"file_path": "D:/Documents/test.pdf"})
   ↓
8. 使用选择文件重新执行 open_pdf
   ↓
9. _continue_after_action() 调用 _start_generation()
   ↓
10. LLM 接收工具结果，生成响应："已为您打开文档：test.pdf"
    ↓
11. 创建 assistant bubble，显示响应
```

### 场景：LLM 同时返回多个依赖工具

假设未来实现迭代式调用：

```
1. 用户输入："提取文本并翻译成英文"
   ↓
2. LLM 返回: [{"name": "get_page_text", ...}]
   ↓
3. 执行 get_page_text
   ↓
4. 结果添加到历史，调用 _start_generation()
   ↓
5. LLM 基于文本结果，决定需要翻译
   ↓
6. LLM 返回: [{"name": "translate_text", "arguments": '{"text": "..."}'}]
   ↓
7. 执行 translate_text
   ↓
8. 结果添加到历史，调用 _start_generation()
   ↓
9. LLM 生成最终响应："文本翻译结果：..."
```

这种模式下，每次只执行一个工具，让 LLM 逐步决策。

---

## 12. 注意事项

### 12.1 禁止的操作

- ❌ 不要在工具执行中直接更新 UI（主线程工具除外）
- ❌ 不要在消息中显示工具名称
- ❌ 不要显示无意义的"执行完成"消息
- ❌ 不要在用户操作（如文件选择）后显示消息

### 12.2 推荐的做法

- ✅ 所有工具结果都通过 LLM 转换为自然语言
- ✅ 错误信息要清晰明确
- ✅ 工具执行要有超时保护
- ✅ 异步执行耗时操作
- ✅ 完善的错误处理和日志记录

---

## 13. 调试技巧

### 13.1 日志级别

```python
logger.debug() - 详细的调试信息
logger.info() - 一般操作信息
logger.warning() - 警告信息
logger.error() - 错误信息
```

### 13.2 关键日志点

1. 工具调用开始：`Processing tool_call: {...}`
2. 工具执行结果：`Retrieved text from page 14, length: 58`
3. 对话流程：`_on_response called: is_error=False, content_len=...`
4. 工具调用完成：`All tool calls completed, continuing conversation`

---

## 版本历史

- **v1.0** - 初始版本，完整描述工具执行流程
- **v1.1** - 添加 OCR 流程说明和错误处理章节
- **v1.2** - 添加示例和调试技巧
