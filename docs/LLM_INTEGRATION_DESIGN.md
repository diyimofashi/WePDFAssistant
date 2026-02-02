# LLM 功能集成方案设计文档

**版本**: 1.0  
**日期**: 2026-02-02  
**状态**: 待实施

---

## 目录

- [一、整体架构](#一整体架构)
- [二、参数 Schema 设计](#二参数-schema-设计)
- [三、工具编排层设计](#三工具编排层设计)
- [四、UI 协调层设计](#四ui-协调层设计)
- [五、对话理解层设计](#五对话理解层设计)
- [六、会话记忆管理](#六会话记忆管理)
- [七、工具定义示例](#七工具定义示例)
- [八、完整工作流程](#八完整工作流程)
- [九、技术要点](#九技术要点)
- [十、扩展性设计](#十扩展性设计)
- [十一、UI 布局建议](#十一ui-布局建议)
- [十二、实施计划](#十二实施计划)

---

## 一、整体架构

### 1.1 三层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互界面 (UI Layer)                  │
│  • 对话输入框                                             │
│  • 对话历史显示                                            │
│  • 参数补全对话框 (通用参数表单组件)                          │
│  • 进度提示和状态反馈                                        │
└────────────────────────────┬────────────────────────────────┘
                             │ (信号槽通信)
┌────────────────────────────▼────────────────────────────────┐
│                   UI 协调层 (UI Coordinator)                 │
│  • 接收参数请求 JSON                                      │
│  • 动态渲染参数表单（基于 JSON Schema）                       │
│  • 收集用户输入并验证                                       │
│  • 返回用户输入给工具层                                      │
└────────────────────────────┬────────────────────────────────┘
                             │ (异步通信)
┌────────────────────────────▼────────────────────────────────┐
│                   工具编排层 (Tool Orchestrator)             │
│  • 工具注册表管理                                            │
│  • 工具参数 Schema 定义                                        │
│  • 参数缺失检测                                               │
│  • 构造参数请求 JSON                                         │
│  • 工具执行状态管理（后台线程）                                 │
│  • 协程暂停与恢复                                             │
└────────────────────────────┬────────────────────────────────┘
                             │ (意图解析)
┌────────────────────────────▼────────────────────────────────┐
│                  对话理解层 (Intent Parser)                 │
│  • 用户意图识别（调用 LLM）                                   │
│  • 参数提取与类型转换                                        │
│  • 多轮对话上下文管理                                        │
│  • 工具选择决策                                             │
└────────────────────────────┬────────────────────────────────┘
                             │ (API 调用)
┌────────────────────────────▼────────────────────────────────┐
│                    LLM 服务层                              │
│  • 支持多种 LLM (OpenAI/Claude/国产大模型)                   │
│  • Prompt 模板管理                                          │
│  • 响应解析与错误重试                                        │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计理念

**参数补全交互流程**：
```
工具执行中检测参数缺失
    ↓
构造参数请求 JSON (包含所有参数 Schema)
    ↓
发送到 UI 协调层（非阻塞）
    ↓
UI 层根据 JSON Schema 动态渲染参数表单
    ↓
用户填写/选择参数
    ↓
UI 层验证参数并返回值
    ↓
工具协程恢复执行
```

**关键设计原则**：
1. **工具不直接调用 UI 组件**：通过 JSON Schema 描述参数
2. **UI 层完全根据 Schema 渲染**：实现参数表单组件化
3. **所有通信都是非阻塞的**：工具在后台线程执行
4. **可暂停的协程**：支持工具中途请求用户输入

---

## 二、参数 Schema 设计

### 2.1 参数类型定义

| 类型枚举 | 说明 | UI 组件 |
|---------|------|---------|
| `TEXT` | 单行文本输入 | QLineEdit |
| `MULTILINE` | 多行文本输入 | QTextEdit |
| `NUMBER` | 数字输入 | QDoubleSpinBox |
| `INTEGER` | 整数输入 | QSpinBox |
| `BOOLEAN` | 布尔值（复选框/开关） | QCheckBox / QSwitch |
| `FILE` | 文件选择器 | QFileDialog |
| `FILE_MULTIPLE` | 多文件选择器 | QFileDialog (Multi) |
| `DIRECTORY` | 目录选择器 | QFileDialog (Directory) |
| `ENUM` | 单选枚举（下拉框） | QComboBox |
| `ENUM_MULTIPLE` | 多选枚举（复选列表） | QListWidget (Multi) |
| `DATE` | 日期选择器 | QDateEdit |
| `TIME` | 时间选择器 | QTimeEdit |
| `RANGE` | 滑块（范围选择） | QSlider |

### 2.2 参数 Schema 结构（JSON）

```json
{
  "name": "output_dir",                      // 参数名称
  "label": "输出目录",                         // 显示标签
  "type": "directory",                      // 参数类型（见上表）
  "required": true,                         // 是否必填
  "description": "选择拆分后文件的保存目录",   // 参数描述
  "defaultValue": "D:\\Documents",          // 默认值
  "value": null,                           // 当前值（用户可修改）
  
  // 枚举选项（type=ENUM/ENUM_MULTIPLE 时）
  "options": [
    {"label": "按页码拆分", "value": "page_range"},
    {"label": "按条码拆分", "value": "barcode_split"},
    {"label": "手动拆分", "value": "manual"}
  ],
  
  // 验证规则
  "minValue": 0,                           // 最小值（NUMBER/INTEGER）
  "maxValue": 100,                         // 最大值
  "minLength": 1,                          // 最小长度（TEXT）
  "maxLength": 100,                        // 最大长度
  "pattern": "^\\d+$",                     // 正则表达式
  "allowedExtensions": [".pdf"],             // 允许的文件扩展名
  
  // UI 提示
  "placeholder": "请输入...",               // 占位符
  "tooltip": "提示信息",                      // 工具提示
  
  // 高级选项（动态控制）
  "dependsOn": "split_mode",                // 依赖的参数
  "visibleWhen": {                         // 可见性条件
    "split_mode": "page_range"
  },
  "enabledWhen": {                         // 启用条件
    "split_mode": ["page_range", "barcode_split"]
  }
}
```

### 2.3 工具参数请求结构（JSON）

```json
{
  "toolName": "split_pdf",                         // 工具名称
  "toolDescription": "拆分 PDF 文档，支持按页码、条码等方式拆分",
  "title": "需要补充拆分参数",                       // 对话框标题
  
  "parameters": [                                   // 参数列表（JSON Schema）
    {
      "name": "split_mode",
      "label": "拆分方式",
      "type": "enum",
      "required": true,
      "description": "选择文档的拆分方式",
      "options": [
        {"label": "按页码拆分", "value": "page_range"},
        {"label": "按条码拆分", "value": "barcode_split"},
        {"label": "手动拆分", "value": "manual"}
      ],
      "defaultValue": "page_range"
    },
    {
      "name": "output_dir",
      "label": "输出目录",
      "type": "directory",
      "required": true,
      "description": "选择拆分后文件的保存目录",
      "defaultValue": "D:\\Documents\\output"
    },
    {
      "name": "custom_ranges",
      "label": "自定义页码范围",
      "type": "multiline",
      "required": false,
      "description": "格式: 1-10, 15-20, 30-35",
      "placeholder": "例如: 1-10, 15-20",
      "visibleWhen": {
        "split_mode": "page_range"
      }
    }
  ],
  
  "context": {                                      // 上下文信息
    "filePath": "D:\\Documents\\report.pdf"
  }
}
```

### 2.4 参数补全响应结构（JSON）

```json
{
  "requestId": "split_pdf_output_dir_123",          // 请求 ID
  "values": {                                       // 用户输入的值
    "split_mode": "page_range",
    "output_dir": "D:\\Documents\\output",
    "custom_ranges": "1-10, 15-20"
  },
  "cancelled": false                                // 用户是否取消
}
```

---

## 三、工具编排层设计

### 3.1 工具注册表

```python
class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, ToolSchema] = {}                    # 工具注册表
        self.tool_schemas: Dict[str, List[ParameterSchema]] = {}  # 工具参数 Schema
    
    def register_tool(self, tool_schema: ToolSchema):
        """注册工具"""
        self.tools[tool_schema.name] = tool_schema
    
    def get_tool_schema(self, tool_name: str) -> ToolSchema:
        """获取工具 Schema"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[ToolSchema]:
        """列出所有工具"""
        return list(self.tools.values())

class ToolSchema:
    """工具 Schema"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        handler: Callable,
        parameters: List[ParameterSchema] = None
    ):
        self.name = name
        self.description = description
        self.category = category
        self.handler = handler
        self.parameters = parameters or []
```

### 3.2 工具执行状态管理

```python
class ToolState(Enum):
    """工具执行状态"""
    PENDING = "pending"          # 等待执行
    RUNNING = "running"          # 执行中
    WAITING_PARAM = "waiting"    # 等待参数补全
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"     # 已取消

class ToolExecution:
    """工具执行状态"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.state = ToolState.PENDING
        self.parameters: Dict[str, Any] = {}      # 已填充的参数
        self.missing_params: List[str] = []      # 缺失的参数列表
        self.result: Any = None                  # 执行结果
        self.error: Exception = None             # 错误信息
        self.coroutine_id: str = None            # 协程 ID
        self.start_time: datetime = None
        self.end_time: datetime = None
```

### 3.3 异步任务执行器

```python
class AsyncTaskRunner(QObject):
    """异步任务运行器 - 桥接 asyncio 和 Qt"""
    
    # 发送给 UI 线程的信号
    parameter_requested = pyqtSignal(object)        # ParameterRequest (JSON)
    parameter_responded = pyqtSignal(str, object)  # request_id, value
    
    def __init__(self):
        super().__init__()
        self.event_loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()
        
        # 存储等待用户输入的 Future
        self.pending_futures: Dict[str, Future] = {}
        
        # 连接响应信号
        self.parameter_responded.connect(self._on_parameter_responded)
    
    def _run_event_loop(self):
        """在后台线程运行 asyncio 事件循环"""
        asyncio.set_event_loop(self.event_loop)
        self.event_loop.run_forever()
    
    def run_coroutine(self, coro: Coroutine) -> Future:
        """在事件循环中运行协程，返回 Future"""
        future = asyncio.run_coroutine_threadsafe(
            coro,
            self.event_loop
        )
        return future
    
    async def request_parameters(self, request: ToolParameterRequest) -> Dict[str, Any]:
        """
        请求用户输入参数
        
        Args:
            request: 参数请求对象
        
        Returns:
            用户输入的参数字典
        
        工作流程:
        1. 创建 Future 来接收用户输入
        2. 通过信号发送 request 到 UI 线程（非阻塞）
        3. await 等待用户输入
        4. UI 响应后，Future 被设置
        5. 返回用户输入的值
        """
        request_id = request.get("requestId", generate_id())
        
        # 创建 Future 来接收用户输入
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_futures[request_id] = future
        
        # 发送参数请求到 UI 线程（信号是线程安全的）
        self.parameter_requested.emit(request)
        
        # 等待用户输入（不会阻塞 UI 线程）
        values = await future
        
        return values
    
    def _on_parameter_responded(self, request_id: str, values: Dict[str, Any]):
        """处理用户响应（在后台线程中）"""
        future = self.pending_futures.get(request_id)
        if future and not future.done():
            future.set_result(values)
            self.pending_futures.pop(request_id)
    
    def stop(self):
        """停止事件循环"""
        self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        self.thread.join(timeout=1.0)
```

### 3.4 工具执行器

```python
class ToolExecutor(QThread):
    """工具执行器（在后台线程运行）"""
    
    # 信号
    started = pyqtSignal(str)                      # tool_name
    progress = pyqtSignal(str, int, str)          # tool_name, progress_percent, message
    completed = pyqtSignal(str, dict)            # tool_name, result
    failed = pyqtSignal(str, str)                # tool_name, error_message
    
    def __init__(self, tool_name: str, tool_handler: Callable, parameters: dict, task_runner: AsyncTaskRunner):
        super().__init__()
        self.tool_name = tool_name
        self.tool_handler = tool_handler
        self.parameters = parameters
        self.task_runner = task_runner
        self._stop_flag = False
    
    def run(self):
        """执行工具（在后台线程）"""
        try:
            self.started.emit(self.tool_name)
            
            # 创建工具执行上下文
            context = ToolExecutionContext(
                task_runner=self.task_runner,
                parameters=self.parameters
            )
            
            # 在异步事件循环中执行工具
            future = self.task_runner.run_coroutine(
                self.tool_handler(context, **self.parameters)
            )
            
            # 等待结果
            result = future.result(timeout=300)  # 5分钟超时
            
            if self._stop_flag:
                raise ToolCancelledException("工具已被用户取消")
            
            self.completed.emit(self.tool_name, result)
            
        except ToolCancelledException as e:
            self.failed.emit(self.tool_name, "操作已取消")
        except Exception as e:
            self.failed.emit(self.tool_name, str(e))
    
    def cancel(self):
        """取消工具执行"""
        self._stop_flag = True
        self.terminate()
```

---

## 四、UI 协调层设计

### 4.1 通用参数表单组件

```python
class ParameterFormWidget(QWidget):
    """通用参数表单组件 - 动态渲染参数"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields: Dict[str, BaseFieldWidget] = {}
        self.layout = QVBoxLayout(self)
    
    def load_schema(self, request: ToolParameterRequest):
        """加载参数 Schema 并渲染表单"""
        # 清除旧字段
        self._clear_fields()
        
        # 遍历参数列表
        for param_schema in request.get("parameters", []):
            field = self._create_field(param_schema)
            self.fields[param_schema["name"]] = field
            self.layout.addWidget(field)
        
        self.layout.addStretch()
    
    def _create_field(self, schema: Dict[str, Any]) -> BaseFieldWidget:
        """根据 Schema 创建对应的字段组件"""
        param_type = schema["type"]
        
        field_map = {
            "text": TextFieldWidget,
            "multiline": MultilineFieldWidget,
            "number": NumberFieldWidget,
            "integer": IntegerFieldWidget,
            "boolean": BooleanFieldWidget,
            "file": FileSelectorWidget,
            "file_multiple": FileMultiSelectorWidget,
            "directory": DirectorySelectorWidget,
            "enum": EnumDropdownWidget,
            "enum_multiple": EnumMultiSelectWidget,
            "date": DateFieldWidget,
            "time": TimeFieldWidget,
            "range": RangeSliderWidget
        }
        
        field_class = field_map.get(param_type, TextFieldWidget)
        field = field_class(schema)
        
        # 连接变化信号（用于动态显示/隐藏）
        field.value_changed.connect(self._on_field_changed)
        
        return field
    
    def get_values(self) -> Dict[str, Any]:
        """获取所有字段的值"""
        values = {}
        for name, field in self.fields.items():
            values[name] = field.get_value()
        return values
    
    def validate(self) -> Tuple[bool, List[str]]:
        """验证所有字段"""
        errors = []
        
        for name, field in self.fields.items():
            is_valid, error = field.validate()
            if not is_valid:
                errors.append(f"{field.label}: {error}")
        
        return (len(errors) == 0, errors)
    
    def _clear_fields(self):
        """清除所有字段"""
        for field in self.fields.values():
            field.deleteLater()
        self.fields.clear()
    
    def _on_field_changed(self, field_name: str, value: Any):
        """字段值变化时的回调（处理动态显示/隐藏）"""
        for name, field in self.fields.items():
            # 检查 visibleWhen 条件
            if "visibleWhen" in field.schema:
                condition = field.schema["visibleWhen"]
                if field_name in condition:
                    expected_value = condition[field_name]
                    if value == expected_value:
                        field.setVisible(True)
                    else:
                        field.setVisible(False)
```

### 4.2 字段组件基类

```python
class BaseFieldWidget(QWidget):
    """字段组件基类"""
    
    value_changed = pyqtSignal(str, object)  # field_name, value
    
    def __init__(self, schema: Dict[str, Any]):
        super().__init__()
        self.schema = schema
        self.name = schema["name"]
        self.label = schema["label"]
        self.required = schema.get("required", False)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI（子类实现）"""
        raise NotImplementedError
    
    def get_value(self) -> Any:
        """获取字段值（子类实现）"""
        raise NotImplementedError
    
    def set_value(self, value: Any):
        """设置字段值（子类实现）"""
        raise NotImplementedError
    
    def validate(self) -> Tuple[bool, str]:
        """验证字段值"""
        value = self.get_value()
        
        # 检查必填
        if self.required and (value is None or value == ""):
            return (False, "此字段为必填项")
        
        # 检查类型（子类可重写）
        return (True, "")
```

### 4.3 参数对话框

```python
class ParameterDialog(QDialog):
    """参数补全对话框"""
    
    def __init__(self, request: ToolParameterRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.values = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle(self.request.get("title", "需要补充参数"))
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # 工具描述
        if "toolDescription" in self.request:
            desc_label = QLabel(self.request["toolDescription"])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; padding: 5px;")
            layout.addWidget(desc_label)
        
        # 参数表单
        self.form_widget = ParameterFormWidget()
        self.form_widget.load_schema(self.request)
        layout.addWidget(self.form_widget)
        
        # 按钮栏
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(button_layout)
    
    def _on_confirm(self):
        """确认按钮点击"""
        # 验证输入
        is_valid, errors = self.form_widget.validate()
        
        if not is_valid:
            QMessageBox.warning(self, "输入错误", "\n".join(errors))
            return
        
        # 获取值
        self.values = self.form_widget.get_values()
        self.accept()
    
    def get_result(self) -> Dict[str, Any]:
        """获取对话框结果"""
        return {
            "requestId": self.request.get("requestId"),
            "values": self.values,
            "cancelled": self.result() == QDialog.Rejected
        }
```

### 4.4 UI 协调器

```python
class UICoordinator(QObject):
    """UI 协调器"""
    
    def __init__(self, main_window, task_runner: AsyncTaskRunner):
        super().__init__()
        self.main_window = main_window
        self.task_runner = task_runner
        self.pending_dialogs: Dict[str, ParameterDialog] = {}
        
        # 连接任务运行器的信号
        self.task_runner.parameter_requested.connect(
            self._show_parameter_dialog
        )
    
    def _show_parameter_dialog(self, request: ToolParameterRequest):
        """显示参数补全对话框（在 UI 线程）"""
        request_id = request.get("requestId")
        
        # 创建对话框
        dialog = ParameterDialog(request, self.main_window)
        self.pending_dialogs[request_id] = dialog
        
        # 显示对话框（模态）
        result = dialog.exec_()
        
        # 获取结果
        dialog_result = dialog.get_result()
        
        # 将用户输入传回后台线程
        self.task_runner.parameter_responded.emit(
            request_id,
            dialog_result.get("values", {})
        )
        
        # 清理对话框
        self.pending_dialogs.pop(request_id)
        dialog.deleteLater()
```

---

## 五、对话理解层设计

### 5.1 意图类型

```python
class IntentType(Enum):
    """意图类型"""
    OPEN_FILE = "open_file"                 # 打开文档
    TRANSLATE = "translate"                 # 翻译
    SPLIT = "split"                        # 拆分
    MERGE = "merge"                        # 合并
    OCR_RECOGNIZE = "ocr_recognize"        # OCR 识别
    BARCODE_DETECT = "barcode_detect"       # 条码检测
    SEARCH = "search"                      # 搜索
    EXPORT = "export"                       # 导出
    SETTING = "setting"                    # 设置
    QUERY = "query"                        # 查询状态
    UNKNOWN = "unknown"                    # 未知意图
```

### 5.2 意图解析器

```python
class IntentParser:
    """意图解析器"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.tool_registry = ToolRegistry()
    
    async def parse_intent(
        self,
        user_input: str,
        context: ConversationContext
    ) -> IntentResult:
        """
        解析用户意图
        
        Args:
            user_input: 用户输入
            context: 对话上下文
        
        Returns:
            意图解析结果
        """
        # 构造 Prompt
        available_tools = self._get_available_tools_description()
        prompt = self._build_intent_prompt(user_input, available_tools, context)
        
        # 调用 LLM
        response = await self.llm_client.chat(prompt)
        
        # 解析响应
        result = self._parse_llm_response(response)
        
        return result
    
    def _build_intent_prompt(
        self,
        user_input: str,
        available_tools: str,
        context: ConversationContext
    ) -> str:
        """构造意图识别 Prompt"""
        return f"""你是一个 PDF 助手的意图识别器。请分析用户的输入，识别他们的意图和参数。

当前上下文：
- 当前打开的文件: {context.current_file}
- 上次操作: {context.last_tool}

可用的工具：
{available_tools}

用户输入: {user_input}

请以 JSON 格式返回结果，包含以下字段：
{{
    "intent": "工具名称（如 split_pdf）",
    "confidence": 0.95,
    "parameters": {{
        "file_path": "文件路径",
        "split_mode": "拆分方式",
        ...
    }},
    "missing_parameters": ["缺失的参数名称列表"]
}}

注意：
1. 如果用户明确提到了参数，提取出来
2. 如果参数可以从上下文推断，自动填充
3. 无法推断的参数放入 missing_parameters
4. 如果没有匹配的工具，intent 设为 "unknown"
"""
    
    def _get_available_tools_description(self) -> str:
        """获取可用工具的描述"""
        tools = []
        for tool_schema in self.tool_registry.list_tools():
            tool_desc = f"- {tool_schema.name}: {tool_schema.description}"
            tools.append(tool_desc)
        return "\n".join(tools)
    
    def _parse_llm_response(self, response: str) -> IntentResult:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            return IntentResult(
                intent=data.get("intent"),
                confidence=data.get("confidence", 0.0),
                parameters=data.get("parameters", {}),
                missing_parameters=data.get("missing_parameters", [])
            )
        except json.JSONDecodeError:
            return IntentResult(intent=IntentType.UNKNOWN)
```

### 5.3 对话上下文

```python
class ConversationContext:
    """对话上下文"""
    
    def __init__(self):
        self.history: List[ConversationTurn] = []
        self.current_file: Optional[str] = None
        self.last_tool: Optional[str] = None
        self.user_preferences: Dict[str, Any] = {}
    
    def add_turn(self, turn: ConversationTurn):
        """添加对话轮次"""
        self.history.append(turn)
        # 保留最近 20 轮
        if len(self.history) > 20:
            self.history = self.history[-20:]
    
    def get_recent_turns(self, count: int = 5) -> List[ConversationTurn]:
        """获取最近的对话轮次"""
        return self.history[-count:]

class ConversationTurn:
    """对话轮次"""
    
    def __init__(
        self,
        user_input: str,
        intent: IntentType,
        tool_used: str,
        parameters: Dict[str, Any],
        result: Any,
        timestamp: datetime
    ):
        self.user_input = user_input
        self.intent = intent
        self.tool_used = tool_used
        self.parameters = parameters
        self.result = result
        self.timestamp = timestamp
```

---

## 六、会话记忆管理

### 6.1 存储目录结构

```
~/.pypdf/conversations/
├── 2026-02-02.md              # 今天的对话记录
├── 2026-02-01.md              # 昨天的对话记录
├── 2026-01-31.md
├── archived/                   # 归档目录
│   ├── 2025-12-01.md
│   ├── 2025-11-15.md
│   └── ...
└── summary/                   # 摘要目录
    ├── weekly_2025-W01.md     # 周报
    ├── weekly_2025-W02.md
    ├── monthly_2025-01.md     # 月报
    └── monthly_2025-02.md
```

### 6.2 Markdown 记录格式

```markdown
# 对话记录 - 2026-02-02

## 会话 001 - 10:30:15
**用户输入**: "帮我把这个PDF翻译成英文"
**意图**: TRANSLATE
**工具**: translate_pdf
**参数**:
```json
{
  "file_path": "D:\\Documents\\report.pdf",
  "target_language": "en",
  "source_language": "auto",
  "translate_images": false
}
```
**结果**: ✅ 翻译完成，生成 15 页译文
**耗时**: 45 秒

---

## 会话 002 - 11:15:30
**用户输入**: "拆分这个文档"
**意图**: SPLIT
**工具**: split_pdf
**参数**:
```json
{
  "file_path": "D:\\Documents\\report.pdf",
  "split_mode": "page_range",
  "output_dir": "D:\\Documents\\output"
}
```
**状态**: ⏸️ 等待参数补全（custom_ranges）
**备注**: 需要用户提供自定义页码范围

---

## 今日统计
- 打开文档: 3 次
- 翻译文档: 2 次
- 拆分文档: 1 次
- OCR 识别: 1 次
- 总耗时: 3 分 20 秒
```

### 6.3 记忆管理器

```python
class ConversationMemory:
    """会话记忆管理器"""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.current_file = self._get_today_file()
        self.archived_dir = os.path.join(storage_dir, "archived")
        self.summary_dir = os.path.join(storage_dir, "summary")
        
        # 确保目录存在
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.archived_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
    
    def _get_today_file(self) -> str:
        """获取今天的记录文件路径"""
        today = datetime.now().strftime("%Y-%m-%d.md")
        return os.path.join(self.storage_dir, today)
    
    async def save_conversation(self, record: ConversationRecord):
        """
        保存对话记录
        
        Args:
            record: 对话记录
        """
        markdown = self._record_to_markdown(record)
        
        # 追加到文件
        async with aiofiles.open(self.current_file, 'a', encoding='utf-8') as f:
            await f.write(markdown + "\n\n---\n\n")
    
    async def get_context(self, max_turns: int = 10) -> List[ConversationRecord]:
        """
        获取最近的对话上下文
        
        Args:
            max_turns: 最大轮次数
        
        Returns:
            对话记录列表
        """
        records = await self._load_records(self.current_file)
        
        if len(records) < max_turns:
            # 加载昨天的记录
            yesterday_file = self._get_yesterday_file()
            yesterday_records = await self._load_records(yesterday_file)
            records.extend(yesterday_records)
        
        return records[:max_turns]
    
    async def archive_old_records(self, days_to_keep: int = 7):
        """
        归档过期记录
        
        Args:
            days_to_keep: 保留天数
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for filename in os.listdir(self.storage_dir):
            if not filename.endswith('.md'):
                continue
            
            file_path = os.path.join(self.storage_dir, filename)
            file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_date < cutoff_date:
                # 移动到归档目录
                archive_path = os.path.join(self.archived_dir, filename)
                shutil.move(file_path, archive_path)
    
    async def summarize_and_cleanup(self):
        """定期整理归纳"""
        # 每周生成摘要
        await self._generate_weekly_summary()
        
        # 每月生成月度总结
        await self._generate_monthly_summary()
        
        # 删除重复或无意义的记录
        await self._remove_duplicates()
    
    async def backup(self, backup_dir: str):
        """
        备份记忆
        
        Args:
            backup_dir: 备份目录
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"conversations_backup_{timestamp}.zip")
        
        # 压缩整个 conversations 目录
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.storage_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.storage_dir)
                    zipf.write(file_path, arcname)
    
    def _record_to_markdown(self, record: ConversationRecord) -> str:
        """将记录转换为 Markdown"""
        return f"""## 会话 {record.session_id} - {record.timestamp.strftime('%H:%M:%S')}
**用户输入**: "{record.user_input}"
**意图**: {record.intent}
**工具**: {record.tool_used}
**参数**:
```json
{json.dumps(record.parameters, ensure_ascii=False, indent=2)}
```
**结果**: {"✅" if record.success else "❌"} {record.result}
**耗时**: {record.duration} 秒
"""
    
    async def _load_records(self, file_path: str) -> List[ConversationRecord]:
        """从文件加载记录"""
        if not os.path.exists(file_path):
            return []
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # 解析 Markdown 文件（简化版）
        records = []
        for section in content.split("---"):
            if section.strip():
                record = self._parse_record_section(section)
                if record:
                    records.append(record)
        
        return records
    
    async def _generate_weekly_summary(self):
        """生成周报摘要"""
        # 获取本周的所有记录
        # 统计工具使用情况
        # 生成摘要 Markdown
        pass
    
    async def _generate_monthly_summary(self):
        """生成月报摘要"""
        # 获取本月的所有记录
        # 统计工具使用情况
        # 生成摘要 Markdown
        pass
    
    async def _remove_duplicates(self):
        """删除重复记录"""
        # 识别重复的对话轮次
        # 保留最新的，删除旧的
        pass
```

---

## 七、工具定义示例

### 7.1 工具装饰器

```python
from functools import wraps

def llm_tool(
    name: str,
    description: str,
    category: str = "general"
):
    """
    LLM 工具装饰器
    
    使用示例：
    @llm_tool(
        name="split_pdf",
        description="拆分 PDF 文档",
        category="file_operations"
    )
    async def split_pdf(context, file_path: str, split_mode: str = None, ...):
        ...
    """
    def decorator(func):
        # 保存工具元数据
        func._llm_tool_metadata = {
            "name": name,
            "description": description,
            "category": category,
            "handler": func
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator
```

### 7.2 工具定义示例

```python
@llm_tool(
    name="split_pdf",
    description="拆分 PDF 文档，支持按页码、条码、手动方式拆分",
    category="file_operations"
)
async def split_pdf(
    context: AsyncTaskRunner,
    file_path: str,
    split_mode: str = None,
    output_dir: str = None,
    custom_ranges: str = None
) -> dict:
    """
    拆分 PDF 文档
    
    Args:
        context: 任务运行器上下文
        file_path: PDF 文件路径
        split_mode: 拆分模式（page_range/barcode_split/manual）
        output_dir: 输出目录
        custom_ranges: 自定义页码范围（格式: 1-10, 15-20）
    
    Returns:
        拆分结果
    """
    # 1. 检测参数缺失并构造 Schema
    missing_schemas = []
    
    if split_mode is None:
        missing_schemas.append({
            "name": "split_mode",
            "label": "拆分方式",
            "type": "enum",
            "required": True,
            "description": "选择文档的拆分方式",
            "options": [
                {"label": "按页码拆分", "value": "page_range"},
                {"label": "按条码拆分", "value": "barcode_split"},
                {"label": "手动拆分", "value": "manual"}
            ],
            "defaultValue": "page_range"
        })
    
    if output_dir is None:
        missing_schemas.append({
            "name": "output_dir",
            "label": "输出目录",
            "type": "directory",
            "required": True,
            "description": "选择拆分后文件的保存目录",
            "defaultValue": os.path.dirname(file_path) if file_path else ""
        })
    
    # 添加可选参数
    missing_schemas.append({
        "name": "custom_ranges",
        "label": "自定义页码范围",
        "type": "multiline",
        "required": False,
        "description": "格式: 1-10, 15-20, 30-35",
        "placeholder": "例如: 1-10, 15-20",
        "defaultValue": "",
        "visibleWhen": {"split_mode": "page_range"}
    })
    
    # 2. 如果有缺失参数，请求用户输入
    if missing_schemas:
        request = {
            "toolName": "split_pdf",
            "toolDescription": "拆分 PDF 文档，支持按页码、条码、手动方式拆分",
            "title": "需要补充拆分参数",
            "requestId": f"split_pdf_{int(time.time())}",
            "parameters": missing_schemas,
            "context": {"file_path": file_path}
        }
        
        # 非阻塞地请求参数
        user_values = await context.request_parameters(request)
        
        # 检查是否取消
        if user_values.get("cancelled"):
            raise ToolCancelledException("用户取消操作")
        
        # 3. 填充参数
        if "split_mode" in user_values:
            split_mode = user_values["split_mode"]
        if "output_dir" in user_values:
            output_dir = user_values["output_dir"]
        if "custom_ranges" in user_values:
            custom_ranges = user_values["custom_ranges"]
    
    # 4. 执行拆分逻辑
    if split_mode == "barcode_split":
        result = await barcode_plugin_manager.split_document_by_barcodes(...)
    elif split_mode == "page_range":
        result = await split_manager.split_by_ranges(file_path, output_dir, custom_ranges)
    else:
        result = await split_manager.manual_split(...)
    
    return {
        "success": True,
        "files_created": len(result.files),
        "output_dir": output_dir
    }

@llm_tool(
    name="translate_pdf",
    description="翻译 PDF 文档，支持多种语言互译",
    category="translation"
)
async def translate_pdf(
    context: AsyncTaskRunner,
    file_path: str,
    source_language: str = "auto",
    target_language: str = None,
    translate_images: bool = False,
    preserve_layout: bool = True
) -> dict:
    """翻译 PDF 文档"""
    # 参数检测和请求
    param_schemas = []
    
    if target_language is None:
        param_schemas.append({
            "name": "target_language",
            "label": "目标语言",
            "type": "enum",
            "required": True,
            "description": "选择要翻译成的语言",
            "options": [
                {"label": "英语", "value": "en"},
                {"label": "日语", "value": "ja"},
                {"label": "韩语", "value": "ko"},
                {"label": "法语", "value": "fr"},
                {"label": "德语", "value": "de"},
                {"label": "西班牙语", "value": "es"}
            ],
            "defaultValue": "en"
        })
    
    # 添加可选参数
    param_schemas.append({
        "name": "translate_images",
        "label": "翻译图片中的文字",
        "type": "boolean",
        "required": False,
        "description": "是否使用 OCR 识别并翻译图片中的文字",
        "defaultValue": False
    })
    
    param_schemas.append({
        "name": "preserve_layout",
        "label": "保持原文档布局",
        "type": "boolean",
        "required": False,
        "description": "翻译后是否保持原文档的排版格式",
        "defaultValue": True
    })
    
    # 请求参数
    if target_language is None or any([p for p in param_schemas if p["name"] not in ["target_language", "translate_images", "preserve_layout"]]):
        request = {
            "toolName": "translate_pdf",
            "toolDescription": "翻译 PDF 文档，支持多种语言互译",
            "title": "需要补充翻译参数",
            "requestId": f"translate_pdf_{int(time.time())}",
            "parameters": param_schemas,
            "context": {"file_path": file_path}
        }
        
        user_values = await context.request_parameters(request)
        
        if user_values.get("cancelled"):
            raise ToolCancelledException("用户取消操作")
        
        target_language = user_values.get("target_language", target_language)
        translate_images = user_values.get("translate_images", translate_images)
        preserve_layout = user_values.get("preserve_layout", preserve_layout)
    
    # 执行翻译
    result = await translation_service.translate(
        file_path=file_path,
        source_lang=source_language,
        target_lang=target_language,
        translate_images=translate_images,
        preserve_layout=preserve_layout
    )
    
    return {
        "success": True,
        "output_path": result.output_path,
        "pages_translated": result.page_count
    }

@llm_tool(
    name="open_file",
    description="打开 PDF 文件并显示",
    category="file_operations"
)
async def open_pdf_file(
    context: AsyncTaskRunner,
    file_path: str,
    page_number: int = None,
    zoom_level: float = 1.0
) -> dict:
    """打开 PDF 文件"""
    if not os.path.exists(file_path):
        # 请求用户选择文件
        request = {
            "toolName": "open_file",
            "toolDescription": "打开 PDF 文件",
            "title": "选择要打开的文件",
            "requestId": f"open_file_{int(time.time())}",
            "parameters": [{
                "name": "file_path",
                "label": "选择 PDF 文件",
                "type": "file",
                "required": True,
                "description": "选择要打开的 PDF 文件",
                "allowedExtensions": [".pdf"]
            }],
            "context": {}
        }
        
        values = await context.request_parameters(request)
        
        if values.get("cancelled"):
            raise ToolCancelledException("用户取消操作")
        
        file_path = values["file_path"]
    
    # 打开文件
    result = file_manager.open_file(file_path)
    
    return {
        "success": True,
        "file_info": {
            "path": file_path,
            "page_count": result.page_count,
            "file_size": result.file_size
        }
    }
```

---

## 八、完整工作流程

### 8.1 正常流程（参数完整）

```
1. 用户输入: "翻译当前文档成英文"
   ↓
2. 对话理解层:
   - 调用 LLM 识别意图: translate_pdf
   - 提取参数: 
     * file_path = 当前文档 (从上下文)
     * target_language = "英文" (从用户输入)
     * 其他参数使用默认值
   ↓
3. 工具编排层:
   - 查找工具: translate_pdf
   - 验证参数: ✅ 完整
   - 创建 ToolExecutor (后台线程)
   ↓
4. 工具执行 (后台线程):
   - 调用翻译 API
   - 更新进度
   - 完成翻译
   ↓
5. 工具完成信号:
   - 触发 completed 信号
   ↓
6. 对话理解层:
   - 格式化结果
   - 保存到会话记忆
   ↓
7. UI 显示: "翻译完成！已生成 15 页译文"
```

### 8.2 参数补全流程

```
1. 用户输入: "拆分这个文档"
   ↓
2. 对话理解层:
   - 调用 LLM 识别意图: split_pdf
   - 提取参数: file_path = 当前文档, split_mode = ❓, output_dir = ❓
   - 标记缺失参数
   ↓
3. 工具编排层:
   - 查找工具: split_pdf
   - 验证参数: ❌ 缺失 split_mode 和 output_dir
   - 创建 ToolExecutor (后台线程)
   ↓
4. 工具执行 (后台线程):
   - 检测 split_mode 为 None
   - 构造参数请求 JSON:
     {
       "toolName": "split_pdf",
       "parameters": [
         {"name": "split_mode", "type": "enum", ...},
         {"name": "output_dir", "type": "directory", ...}
       ]
     }
   - 调用 await context.request_parameters(request)
   ↓
5. AsyncTaskRunner (后台线程):
   - 创建 Future
   - 通过信号发送 JSON 到 UI 线程 (非阻塞)
   - 协程暂停 (await Future)
   ↓
6. UI 协调层 (主线程):
   - 接收参数请求 JSON
   - 创建参数对话框
   - 调用 ParameterFormWidget.load_schema(request)
   - 动态渲染表单:
     * split_mode: 下拉框（按页码/按条码/手动）
     * output_dir: 目录选择器
   - 显示模态对话框
   ↓
7. 用户操作:
   - 选择 "按页码拆分"
   - 选择输出目录 "D:\Documents\output"
   - 点击确认
   ↓
8. UI 协调层:
   - 验证用户输入
   - 构造响应 JSON:
     {
       "requestId": "xxx",
       "values": {"split_mode": "page_range", "output_dir": "D:\\Documents\\output"},
       "cancelled": false
     }
   - 通过信号发送回后台线程
   - 关闭对话框
   ↓
9. AsyncTaskRunner (后台线程):
   - 接收响应
   - 设置 Future 值
   ↓
10. 工具协程恢复:
    - await 返回用户输入的值
    - 填充参数: split_mode = "page_range", output_dir = "D:\Documents\output"
    - 继续执行拆分逻辑
    ↓
11. 拆分完成
    ↓
12. 返回结果并保存到会话记忆
    ↓
13. UI 显示: "拆分完成！生成了 5 个文件"
```

---

## 九、技术要点

### 9.1 非阻塞设计

| 组件 | 线程/循环 | 说明 |
|------|-----------|------|
| UI 主界面 | 主线程 (Qt 事件循环) | 负责界面渲染和用户交互 |
| UI 协调层 | 主线程 | 接收参数请求，显示对话框 |
| 工具编排层 | 主线程 | 管理工具注册和状态 |
| 工具执行器 | 后台线程 (QThread) | 在后台线程执行工具 |
| AsyncTaskRunner | 后台线程 (asyncio) | 拥有独立的 asyncio 事件循环 |

**通信机制**:
- Qt 信号槽机制（线程安全）
- asyncio Future（协程暂停/恢复）
- JSON 格式数据传输

### 9.2 JSON Schema 驱动

**优势**:
1. 工具层不依赖具体 UI 组件
2. UI 层完全根据 Schema 动态渲染
3. 易于扩展新的参数类型
4. 参数定义与实现分离

**实现**:
- 所有参数通过 JSON Schema 描述
- UI 层根据 Schema 自动生成对应的 Widget
- 参数验证规则在 Schema 中定义

### 9.3 参数验证

**客户端验证（UI 层）**:
- 类型检查（根据 Schema 的 type）
- 必填项检查（required）
- 范围检查（minValue/maxValue）
- 长度检查（minLength/maxLength）
- 正则表达式匹配（pattern）
- 文件扩展名检查（allowedExtensions）

**服务端验证（工具层）**:
- 二次验证（防止客户端绕过）
- 业务逻辑检查（如文件是否存在）
- 友好错误提示

### 9.4 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 工具执行失败 | 显示错误信息，允许重试 |
| 参数验证失败 | 高亮错误字段，显示错误消息 |
| 用户取消 | 清理资源，记录取消事件 |
| LLM 调用失败 | 使用本地规则回退，提示用户 |
| 超时 | 提示用户，允许取消或继续等待 |

### 9.5 状态持久化

- 工具执行状态保存到本地 JSON 文件
- 支持断点续传（工具可恢复执行）
- 应用重启后恢复对话上下文
- 任务队列管理（支持多任务）

---

## 十、扩展性设计

### 10.1 自定义参数类型

**添加新的参数类型步骤**:

1. 在 `ParameterType` 枚举中添加新类型
2. 创建对应的 Field Widget 类（继承 `BaseFieldWidget`）
3. 在 `ParameterFormWidget._create_field()` 中注册
4. 实现渲染、验证、值获取逻辑

**示例**:
```python
# 1. 添加枚举值
class ParameterType(Enum):
    ...
    COLOR_PICKER = "color_picker"  # 新增

# 2. 创建 Widget
class ColorPickerFieldWidget(BaseFieldWidget):
    def _init_ui(self):
        self.color_picker = QColorButton()
    
    def get_value(self):
        return self.color_picker.color().name()
    
    def validate(self):
        # 颜色验证逻辑
        pass

# 3. 注册
def _create_field(self, schema):
    field_map = {
        ...
        "color_picker": ColorPickerFieldWidget,  # 新增
    }
```

### 10.2 插件式工具

**支持的工具类型**:
1. 内置工具（使用装饰器注册）
2. 插件工具（从插件目录加载）
3. 自定义工具（用户脚本）

**插件结构**:
```
app/llm-tools/
├── custom_tools/
│   ├── advanced_split/
│   │   ├── __init__.py
│   │   └── tool.py
│   └── batch_translate/
│       ├── __init__.py
│       └── tool.py
└── tool_manifest.json
```

### 10.3 LLM 可切换

**支持的 LLM**:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- 阿里云 (通义千问)
- 百度 (文心一言)
- 智谱 AI (GLM)
- 本地模型 (Ollama, LM Studio)

**切换机制**:
```python
class LLMProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    QIANWEN = "qianwen"
    WENXIN = "wenxin"
    GLM = "glm"
    LOCAL = "local"

class LLMClient:
    def __init__(self, provider: LLMProvider, config: dict):
        self.provider = provider
        self.config = config
        self.client = self._create_client()
    
    def _create_client(self):
        """根据 provider 创建对应的客户端"""
        factory_map = {
            LLMProvider.OPENAI: OpenAIClient,
            LLMProvider.CLAUDE: ClaudeClient,
            # ...
        }
        return factory_map[self.provider](self.config)
```

---

## 十一、UI 布局建议

### 11.1 对话界面

```
┌─────────────────────────────────────────────────────────────────────┐
│  PDF Assistant - AI 对话                              [_][□][X]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 对话历史区                                              │  │
│  │                                                          │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ 🤖 AI: 您好！我是您的 PDF 助手，有什么可以帮您？    │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ 👤 用户: 帮我拆分这个文档                         │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ 🤖 AI: 请选择拆分方式:                             │   │  │
│  │ │     - 按页码拆分                                   │   │  │
│  │ │     - 按条码拆分                                   │   │  │
│  │ │     - 手动拆分                                     │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ 👤 用户: 按页码拆分                                 │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ 🤖 AI: ✅ 拆分完成！生成了 5 个文件                  │   │  │
│  │ │       保存位置: D:\Documents\output                  │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  │                                                          │  │
│  │ ... (自动滚动)                                            │  │
│  │                                                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ [输入框...]                                      [📎] [发送]│  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                               │
│  [对话历史] [参数设置] [关于]                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 参数补全对话框

```
┌─────────────────────────────────────────────────────────────────────┐
│  需要补充拆分参数                                    [X]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                               │
│  拆分 PDF 文档，支持按页码、条码、手动方式拆分                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 拆分方式 *                                             │  │
│  │ ┌─────────────────────────────────────────────────────┐   │  │
│  │ │ 按页码拆分                       ▼          │   │  │
│  │ ├─────────────────────────────────────────────────────┤   │  │
│  │ │ 按页码拆分                                         │   │  │
│  │ │ 按条码拆分                                         │   │  │
│  │ │ 手动拆分                                           │   │  │
│  │ └─────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 输出目录 *                                             │  │
│  │ ┌─────────────────────────────────────────────────────┐   │  │
│  │ │ D:\Documents\output               [浏览...]      │   │  │
│  │ └─────────────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                               │
│  [▼ 显示高级选项]                                               │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ 自定义页码范围                                       │  │
│  │ ┌─────────────────────────────────────────────────────┐   │  │
│  │ │ 1-10, 15-20                                     │   │  │
│  │ │                                                   │   │  │
│  │ └─────────────────────────────────────────────────────┘   │  │
│  │ 格式: 1-10, 15-20, 30-35                           │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────┐              ┌──────────────────┐  │
│  │        [取消]           │              │     [确认]       │  │
│  └──────────────────────────┘              └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.3 设置界面

```
┌─────────────────────────────────────────────────────────────────────┐
│  设置                                            [X]           │
├─────────────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┬───────────────────────────────────────────┐ │
│  │ [ 通用设置  ] │                                           │ │
│  │  LLM 配置    │ LLM Provider:                       │ │
│  │              │ ┌──────────────────────────────┐          │ │
│  │  对话设置    │ │ OpenAI                    │  ▼      │ │
│  │              │ ├──────────────────────────────┤          │ │
│  │  记忆管理    │ │ OpenAI                           │          │ │
│  │              │ │ Claude                          │          │ │
│  │              │ │ 通义千问                        │          │ │
│  │              │ │ 文心一言                        │          │ │
│  │              │ └──────────────────────────────┘          │ │
│  │              │                                           │ │
│  │  [高级设置]  │ API Key:                              │ │
│  │              │ ┌──────────────────────────────┐          │ │
│  │              │ │ sk-xxxx...                │          │ │
│  │              │ └──────────────────────────────┘          │ │
│  │              │                                           │ │
│  │              │ Model:                                │ │
│  │              │ ┌──────────────────────────────┐          │ │
│  │              │ │ GPT-4                      │  ▼      │ │
│  │              │ └──────────────────────────────┘          │ │
│  │              │                                           │ │
│  │              │ [测试连接]                                  │ │
│  │              │                                           │ │
│  └───────────────┴───────────────────────────────────────────┘ │
│                                                               │
│                                       [取消]          [保存]  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 十二、实施计划

### 12.1 开发阶段

| 阶段 | 任务 | 预计时间 | 优先级 |
|------|------|---------|--------|
| **阶段一** | 基础架构搭建 | 3 天 | P0 |
| | - 创建目录结构 | | |
| | - 实现 AsyncTaskRunner | | |
| | - 实现工具注册表 | | |
| | - 实现参数 Schema 数据结构 | | |
| **阶段二** | UI 组件开发 | 4 天 | P0 |
| | - 实现 BaseFieldWidget | | |
| | - 实现各类型 Field Widget | | |
| | - 实现 ParameterFormWidget | | |
| | - 实现 ParameterDialog | | |
| | - 实现 UICoordinator | | |
| **阶段三** | 对话理解层 | 3 天 | P0 |
| | - 实现 IntentParser | | |
| | - 实现 ConversationContext | | |
| | - 集成 LLM API | | |
| **阶段四** | 工具实现 | 5 天 | P0 |
| | - 实现 split_pdf 工具 | | |
| | - 实现 translate_pdf 工具 | | |
| | - 实现 open_file 工具 | | |
| | - 实现 merge_pdf 工具 | | |
| | - 实现其他常用工具 | | |
| **阶段五** | 会话记忆 | 3 天 | P1 |
| | - 实现 ConversationMemory | | |
| | - 实现 Markdown 存储格式 | | |
| | - 实现定期归档和备份 | | |
| **阶段六** | 对话 UI | 4 天 | P0 |
| | - 实现对话主界面 | | |
| | - 实现消息气泡组件 | | |
| | - 实现输入框 | | |
| | - 集成参数对话框 | | |
| **阶段七** | 测试与优化 | 3 天 | P1 |
| | - 单元测试 | | |
| | - 集成测试 | | |
| | - 性能优化 | | |
| | - Bug 修复 | | |
| **阶段八** | 文档与部署 | 2 天 | P2 |
| | - 编写用户文档 | | |
| | - 编写开发者文档 | | |
| | - 打包发布 | | |

**总计**: 约 27 天（约 4 周）

### 12.2 技术依赖

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.8 | 开发语言 |
| PyQt5 | >= 5.15 | UI 框架 |
| openai | >= 1.0 | OpenAI API |
| anthropic | >= 0.5 | Claude API |
| aiofiles | >= 0.8 | 异步文件操作 |
| aiohttp | >= 3.8 | 异步 HTTP 请求 |

### 12.3 待确认事项

1. **LLM 选择**:
   - 使用哪家 LLM？
   - API Key 如何管理（本地存储/环境变量）？

2. **UI 布局**:
   - 对话界面位置：侧边栏/独立窗口/底部面板？
   - 快捷输入方式：悬浮窗/全局快捷键？

3. **会话记忆策略**:
   - 保留天数：7/30/90 天？
   - 是否支持用户手动删除会话？

4. **参数类型需求**:
   - 是否需要支持所有设计的参数类型？
   - 是否有特殊需求的参数类型？

5. **多模态输入**:
   - 是否支持语音输入？
   - 是否支持文件拖拽？

6. **离线能力**:
   - 是否支持本地 LLM（Ollama/LM Studio）？
   - LLM 不可用时的降级策略？

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| LLM | Large Language Model，大语言模型 |
| Intent | 意图，用户想要执行的操作 |
| Schema | 数据结构定义，描述参数的类型和约束 |
| Coroutine | 协程，Python 的异步编程特性 |
| Future | Future 对象，表示一个尚未完成的异步操作 |
| Signal/Slot | Qt 的信号槽机制，用于对象间通信 |

### B. 参考资料

- [OpenAI API 文档](https://platform.openai.com/docs)
- [PyQt5 文档](https://doc.qt.io/qtforpython/)
- [asyncio 文档](https://docs.python.org/3/library/asyncio.html)
- [JSON Schema 规范](https://json-schema.org/)

---

**文档结束**
