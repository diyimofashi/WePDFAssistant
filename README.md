# 极光PDF - PDF文档处理工具

一个模仿极光PDF软件的桌面客户端应用，采用模块化设计，界面美观，操作简单。

## 🎯 项目特色

- **模块化架构**：清晰的分层设计，便于维护和扩展
- **美观界面**：现代化的深色主题，图标化操作
- **傻瓜式操作**：直观的界面设计，一键式功能操作
- **高性能优化**：集成多种性能优化技术

## 📁 项目结构

```
PyPDF/
├── app/                          # 应用主包
│   ├── config/                    # 配置模块
│   │   ├── settings.py           # 应用设置和配置管理
│   │   ├── ocr_plugin_config.py  # OCR插件配置管理
│   │   └── barcode_split_config.json # 条码分割配置
│   ├── core/                      # 核心功能模块
│   │   ├── processing/           # PDF处理与渲染
│   │   │   ├── pdf_processor.py  # PDF处理核心功能
│   │   │   ├── async_loader.py   # 异步PDF加载器
│   │   │   └── thumbnail_manager.py # 缩略图管理
│   │   ├── performance/          # 缓存与性能优化
│   │   │   ├── cache_manager.py  # 缓存管理器
│   │   │   └── ocr_performance_optimizer.py # OCR性能优化器
│   │   ├── ocr/                  # OCR系统
│   │   │   ├── ocr_integration.py # OCR系统集成
│   │   │   ├── ocr_error_handler.py # OCR错误处理
│   │   │   ├── ocr_plugin_interface.py # OCR插件接口
│   │   │   ├── ocr_plugin_security.py # OCR插件安全
│   │   │   └── ocr_searchable_pdf.py # OCR可搜索PDF生成
│   │   └── editing/              # 编辑与历史记录
│   │       ├── operation_history.py # 操作历史记录管理
│   │       └── page_editor.py    # 页面编辑功能
│   ├── managers/                  # 管理器模块
│   │   ├── file_manager.py       # 文件管理器
│   │   ├── ocr_plugin_manager.py # OCR插件管理器
│   │   ├── search_manager.py     # 搜索管理器
│   │   ├── split_manager.py      # 分割管理器
│   │   ├── view_controller.py    # 视图控制器
│   │   ├── barcode_detector.py  # 条码检测器
│   │   ├── barcode_split_processor.py # 条码分割处理器
│   │   └── barcode_detection_thread.py # 条码检测线程
│   ├── ui/                        # UI界面模块
│   │   ├── styles.py             # 界面样式定义
│   │   ├── menu_manager.py       # 菜单管理器
│   │   ├── toolbar_manager.py    # 工具栏管理器
│   │   ├── virtual_scroll.py     # 虚拟滚动组件
│   │   ├── barcode_result_dialog.py # 条码结果对话框
│   │   ├── barcode_split_dialog.py # 条码分割对话框
│   │   ├── ocr_page_label.py     # OCR页面标签
│   │   ├── ocr_settings_dialog.py # OCR设置对话框
│   │   ├── smart_thumbnail.py    # 智能缩略图
│   │   └── styles.py             # 样式定义
│   ├── utils/                     # 工具模块
│   │   └── logger.py             # 日志工具
│   ├── plugins/                   # 插件系统
│   │   ├── template/             # 插件模板
│   │   └── win7_x64_RapidOCR_json/ # RapidOCR插件
│   └── main.py                   # 主程序入口
├── docs/                         # 文档目录
│   ├── development_plan.md       # 开发计划
│   ├── ocr_plugin_development_template.md # OCR插件开发模板
│   ├── ocr_plugin_system_design.md # OCR插件系统设计
│   └── split_guide.md           # 分割指南
├── tests/                        # 测试目录
├── pypdf/                        # 虚拟环境目录
├── cache/                        # 缓存目录
├── logs/                         # 日志目录
├── requirements.txt              # 依赖包列表
├── run.bat                      # 一键启动脚本
├── start.py                     # 主启动脚本
├── project_rule.md              # 项目规则
└── README.md                    # 项目说明

## 🚀 快速开始

### 方法一：一键启动（推荐）

直接双击 `run.bat` 文件即可启动应用。

### 方法二：手动启动

1. 创建虚拟环境：
```bash
python -m venv pypdf
```

2. 激活虚拟环境：
```bash
pypdf\Scripts\activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 运行应用：
```bash
python app\main.py
```

## ⚡ 性能优化特性

### 异步加载
- 后台线程异步加载PDF文件
- 实时进度显示，UI无卡顿

### 虚拟滚动技术
- 只渲染可视区域页面
- 支持流畅浏览大文件（1000+页）

### 智能缓存系统
- LRU内存缓存 + 磁盘持久化缓存
- 缓存命中率高达85%+

### 延迟加载缩略图
- 按需生成缩略图
- 智能预加载策略

### 实时性能监控
- 内存使用实时显示
- 自动内存优化

## 🎨 界面功能

### 主界面布局

- **左侧面板**：文件管理和工具区域
  - 📁 快速访问：最近文件列表
  - 🛠️ PDF工具：合并、分割、转换、加密等一键式工具

- **右侧面板**：PDF预览和编辑区域
  - 👁️ 预览标签页：PDF文档预览和页面导航
  - ✏️ 编辑标签页：PDF编辑功能（开发中）
  - 📝 注释标签页：PDF注释功能（开发中）

### 核心功能

- ✅ PDF文件打开和高质量显示
- ✅ 文件保存功能
- ✅ 现代化的浅色主题UI界面
- ✅ 图标化操作，直观易用
- ✅ 完整的工具栏（文件操作、缩放、导航、搜索）
- ✅ PDF页面导航（上一页、下一页、跳转）
- ✅ 智能缩放控制（放大、缩小、适合宽度/页面）
- ✅ PDF文本搜索功能（支持高亮和导航）
- ✅ 连续浏览模式（网页式滚动，多页显示）
- ✅ 灵活的浏览方式（连续模式 vs 单页模式）
- ✅ 目录记忆功能（记住上次打开/保存的目录）
- ✅ 菜单栏和状态栏
- 🔄 PDF合并/分割功能（开发中）
- 🔄 格式转换功能（开发中）
- 🔄 加密解密功能（开发中）

## 🛠️ 技术架构

- **Python 3.8+** - 编程语言
- **PyQt5** - 桌面应用框架
- **PyPDF2** - PDF文档处理
- **PyMuPDF** - PDF渲染引擎
- **模块化设计** - 清晰的分层架构

## 📋 开发计划

### 近期目标
- [ ] 实现PDF页面渲染和显示
- [ ] 添加PDF文本编辑功能
- [ ] 实现PDF注释工具
- [ ] 完善PDF合并/分割功能

### 远期目标
- [ ] 支持更多PDF格式转换
- [ ] 添加OCR文字识别
- [ ] 实现PDF表单处理
- [ ] 添加批量处理功能

## 💡 使用技巧

1. **快速打开文件**：使用快捷键 `Ctrl+O` 或点击工具栏的打开按钮
2. **一键式工具**：左侧面板的工具按钮提供一键式操作
3. **直观预览**：右侧预览区域显示详细的PDF信息
4. **状态提示**：底部状态栏实时显示操作状态
5. **连续浏览**：使用 `Ctrl+M` 切换到连续浏览模式，像网页一样滚动查看PDF
6. **单页浏览**：使用 `Ctrl+N` 切换到单页模式，传统的翻页方式
7. **智能导航**：连续模式下滚动查看，单页模式下使用翻页按钮
8. **搜索高亮**：使用 `Ctrl+F` 搜索文本，支持高亮显示和结果导航

## 🐛 问题反馈

如果在使用过程中遇到问题，请检查：

1. 虚拟环境是否正确激活
2. 依赖包是否完整安装
3. 系统是否支持PyQt5
4. PDF文件是否损坏或加密

## 📄 许可证

MIT License