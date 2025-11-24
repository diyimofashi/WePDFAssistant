# 极光PDF项目规则

## 项目结构规范

### 目录结构
```
pypdf/
├── app/                     # 主应用目录
│   ├── __init__.py
│   ├── main.py             # 程序入口和主窗口
│   ├── config/             # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py     # 应用设置
│   ├── core/               # 核心处理模块
│   │   ├── __init__.py
│   │   ├── pdf_processor.py # PDF处理核心
│   │   └── thumbnail_manager.py # 缩略图管理
│   ├── ui/                 # 界面模块
│   │   ├── __init__.py
│   │   ├── styles.py       # 样式定义
│   │   └── dialogs/        # 对话框模块
│   ├── utils/              # 工具模块
│   │   ├── __init__.py
│   │   └── helpers.py      # 辅助函数
│   └── features/           # 功能模块
│       ├── __init__.py
│       ├── editor/         # 编辑功能
│       ├── ocr/            # OCR功能
│       └── export/         # 导出功能
├── assets/                 # 资源文件
│   ├── icons/              # 图标资源
│   └── styles/             # 样式资源
├── tests/                  # 测试文件
├── docs/                   # 文档
│   ├── project_rule.md     # 项目规则
│   └── development_plan.md # 开发计划
├── requirements.txt        # 依赖包列表
├── start.py               # 启动脚本
└── README.md              # 项目说明
```

## 代码规范

### 命名规范
- 类名使用 PascalCase（如 `PdfProcessor`）
- 函数和变量使用 snake_case（如 `render_page`）
- 常量使用 UPPER_SNAKE_CASE（如 `MAX_CACHE_SIZE`）
- 私有成员使用下划线前缀（如 `_private_method`）

### 模块划分原则
1. **单一职责原则**：每个模块只负责一个功能领域
2. **高内聚低耦合**：模块内部功能相关性强，模块间依赖关系清晰
3. **可复用性**：模块设计应考虑在不同场景下的复用

### 依赖管理
1. 优先使用Python标准库和项目已有的依赖
2. 新增第三方库必须在 `requirements.txt` 中声明
3. 避免不必要的依赖，保持项目轻量

## 功能开发流程

### 开发步骤
1. 完善开发文档，明确功能需求和设计
2. 编写代码实现
3. 添加必要的单元测试
4. 进行功能测试
5. 代码审查和优化

### 文档要求
1. 所有功能模块必须有相应的文档说明
2. 复杂功能需要提供使用示例
3. API接口需要详细说明参数和返回值