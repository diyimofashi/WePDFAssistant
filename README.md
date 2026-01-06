# 极灵PDF - PDF文档处理工具

一个功能丰富的PDF文档处理工具，采用模块化设计，界面美观，操作简单。支持PDF查看、编辑、OCR识别、插件扩展等高级功能。

## 🎯 项目特色

- **模块化架构**：清晰的分层设计，便于维护和扩展
- **美观界面**：现代化的UI界面，图标化操作
- **傻瓜式操作**：直观的界面设计，一键式功能操作
- **高性能优化**：集成多种性能优化技术
- **插件系统**：支持OCR、上传、下载等多种插件扩展
- **智能功能**：OCR文字识别、条码拆分、PDF转图片等

## 📁 项目结构

```
PyPDF/
├── app/                          # 应用主包
│   ├── assets/                   # 资源文件
│   │   ├── app_icon.ico          # 应用图标
│   │   └── app_icon.png          # 应用图标
│   ├── config/                   # 配置模块
│   │   ├── settings.py           # 应用设置和配置管理
│   │   ├── ocr_plugin_config.py  # OCR插件配置管理
│   │   ├── download_plugin_config.py # 下载插件配置管理
│   │   ├── upload_plugin_config.py # 上传插件配置管理
│   │   └── barcode_split_config.json # 条码分割配置
│   ├── core/                     # 核心功能模块
│   │   ├── processing/           # PDF处理与渲染
│   │   │   ├── pdf_processor.py  # PDF处理核心功能（重构版）
│   │   │   ├── pdf_loader.py     # PDF加载和文件打开功能
│   │   │   ├── pdf_renderer.py   # 页面渲染和缓存功能
│   │   │   ├── pdf_navigation.py # 页面导航和缩放功能
│   │   │   ├── pdf_search.py     # 搜索和高亮功能
│   │   │   ├── pdf_operations.py # PDF操作和编辑功能
│   │   │   ├── pdf_conversion.py # PDF转换和导入功能
│   │   │   ├── pdf_history_manager.py # 操作历史记录功能
│   │   │   ├── async_loader.py   # 异步PDF加载器
│   │   │   └── thumbnail_manager.py # 缩略图管理
│   │   ├── main/                 # 主窗口功能模块（重构版）
│   │   │   ├── main_window_base.py # 主窗口基础类
│   │   │   ├── pdf_manager_mixin.py # PDF管理混入类
│   │   │   ├── view_manager_mixin.py # 视图管理混入类
│   │   │   ├── thumbnail_manager_mixin.py # 缩略图管理混入类
│   │   │   ├── search_manager_mixin.py # 搜索管理混入类
│   │   │   ├── ocr_manager_mixin.py # OCR管理混入类
│   │   │   ├── upload_manager_mixin.py # 上传管理混入类
│   │   │   ├── download_manager_mixin.py # 下载管理混入类
│   │   │   └── operation_manager_mixin.py # 操作管理混入类
│   │   ├── performance/          # 缓存与性能优化
│   │   │   ├── cache_manager.py  # 缓存管理器
│   │   │   └── ocr_performance_optimizer.py # OCR性能优化器
│   │   ├── ocr/                  # OCR系统
│   │   │   ├── ocr_integration.py # OCR系统集成
│   │   │   ├── ocr_error_handler.py # OCR错误处理
│   │   │   ├── ocr_plugin_interface.py # OCR插件接口
│   │   │   ├── ocr_plugin_security.py # OCR插件安全
│   │   │   └── ocr_searchable_pdf.py # OCR可搜索PDF生成
│   │   ├── editing/              # 编辑与历史记录
│   │   │   ├── operation_history.py # 操作历史记录管理
│   │   │   └── page_editor.py    # 页面编辑功能
│   │   ├── barcode/              # 条码处理模块
│   │   │   ├── barcode_detection_thread.py # 条码检测线程
│   │   │   ├── barcode_detector.py # 条码检测器
│   │   │   └── barcode_split_processor.py # 条码分割处理器
│   │   └── upload/               # 上传功能模块
│   │       └── upload_plugin_interface.py # 上传插件接口
│   ├── managers/                 # 管理器模块
│   │   ├── file_manager.py       # 文件管理器
│   │   ├── ocr_plugin_manager.py # OCR插件管理器
│   │   ├── search_manager.py     # 搜索管理器
│   │   ├── split_manager.py      # 分割管理器
│   │   ├── view_controller.py    # 视图控制器
│   │   ├── upload_plugin_manager.py # 上传插件管理器
│   │   └── download_plugin_manager.py # 下载插件管理器
│   ├── ui/                       # UI界面模块
│   │   ├── styles.py             # 界面样式定义
│   │   ├── menu_manager.py       # 菜单管理器
│   │   ├── toolbar_manager.py    # 工具栏管理器
│   │   ├── context_menu_manager.py  # 右键菜单管理器
│   │   ├── context_menu_styles.py   # 右键菜单样式
│   │   ├── context_menu_builders.py # 右键菜单构建器
│   │   ├── virtual_scroll.py     # 虚拟滚动组件
│   │   ├── barcode_result_dialog.py # 条码结果对话框
│   │   ├── barcode_split_dialog.py # 条码分割对话框
│   │   ├── download_file_dialog.py # 下载文件对话框
│   │   ├── download_settings_dialog.py # 下载设置对话框
│   │   ├── ocr_page_label.py     # OCR页面标签
│   │   ├── ocr_settings_dialog.py # OCR设置对话框
│   │   ├── smart_thumbnail.py    # 智能缩略图
│   │   ├── upload_settings_dialog.py # 上传设置对话框
│   │   └── styles.py             # 样式定义
│   ├── utils/                    # 工具模块
│   │   └── logger.py             # 日志工具
│   ├── plugins/                  # OCR插件系统
│   │   ├── template/             # OCR插件模板
│   │   └── win7_x64_RapidOCR_json/ # RapidOCR插件
│   ├── plugins-upload/           # 上传插件系统
│   │   ├── upload_ftp/           # FTP上传插件
│   │   ├── upload_http/          # HTTP上传插件
│   │   └── upload_template/      # 上传插件模板
│   └── plugins-download/         # 下载插件系统
│       ├── download_http/        # HTTP下载插件
│       └── download_template/    # 下载插件模板
├── docs/                         # 文档目录
│   ├── development_plan.md       # 开发计划
│   ├── ocr_plugin_development_template.md # OCR插件开发模板
│   ├── ocr_plugin_system_design.md # OCR插件系统设计
│   └── split_guide.md            # 分割指南
├── tests/                        # 测试目录
├── requirements.txt              # 依赖包列表
├── run.bat                       # 一键启动脚本
├── start.py                      # 主启动脚本
├── main.py                       # 重构后的主程序入口
├── project_rule.md               # 项目规则
└── README.md                     # 项目说明
```

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
python start.py
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

- **顶部工具栏**：文件操作、编辑、视图控制、导航、转换工具
  - 📂 打开：打开PDF文件
  - 💾 保存：保存PDF文件
  - 📄 另存为：将PDF保存到指定位置
  - 🖼️ 缩略图：显示/隐藏缩略图面板
  - 🔍 搜索：搜索PDF中的文本
  - 📟 条码拆分：根据条码分割PDF
  - ⬆️ 上传：上传当前文档到远程服务器
  - 🌐 下载：下载远程PDF文件

- **左侧缩略图面板**：显示PDF所有页面缩略图，支持点击跳转

- **中央预览区域**：PDF页面渲染显示区域

- **底部状态栏**：显示当前状态、页码、缩放比例、性能信息

### 核心功能

- ✅ PDF文件打开和高质量显示
- ✅ PDF文件保存和另存为
- ✅ 现代化的UI界面
- ✅ 图标化操作，直观易用
- ✅ 完整的工具栏（文件操作、缩放、导航、搜索）
- ✅ PDF页面导航（上一页、下一页、跳转）
- ✅ 智能缩放控制（放大、缩小、适合宽度/页面）
- ✅ PDF文本搜索功能（支持高亮和导航）
- ✅ 智能缩略图面板（显示所有页面缩略图）
- ✅ 目录记忆功能（记住上次打开/保存的目录）
- ✅ 菜单栏和状态栏
- ✅ 撤销/重做功能
- ✅ 操作历史记录管理
- ✅ 连续浏览模式（虚拟滚动，支持大文件）
- ✅ OCR文字识别功能（插件化支持）
- ✅ 条码检测与分割
- ✅ PDF转图片功能
- ✅ 远程文件下载（插件化支持HTTP等协议）
- ✅ 文档上传功能（插件化支持FTP、HTTP等协议）
- ✅ 错误处理与PDF修复功能

## 🔌 插件系统

### OCR插件
- 支持多种OCR引擎（RapidOCR等）
- 插件化架构，易于扩展
- 支持生成可搜索PDF
- 配置界面，可调整参数

### 上传插件
- 支持多种上传协议（FTP、HTTP等）
- 插件化设计，易于扩展
- 支持认证和安全传输
- 配置界面，可设置服务器参数

### 下载插件
- 支持多种下载协议（HTTP等）
- 插件化设计，易于扩展
- 支持认证和进度监控
- 配置界面，可设置服务器参数

## 🛠️ 技术架构

- **Python 3.8+** - 编程语言
- **PyQt5** - 桌面应用框架
- **PyMuPDF** - PDF渲染引擎
- **Pillow** - 图像处理
- **PyZBar** - 条码识别
- **OpenCV** - 计算机视觉处理
- **模块化设计** - 清晰的分层架构
- **插件化架构** - 支持功能扩展
- **混入类设计** - 功能模块化，便于维护

## ⌨️ 快捷键

文件操作：
- Ctrl+O: 打开文件
- Ctrl+S: 保存文件
- Ctrl+Shift+S: 另存为
- Ctrl+Z: 撤销
- Ctrl+Y: 重做

视图操作：
- Ctrl++: 放大
- Ctrl+-: 缩小
- Ctrl+F: 搜索

页面导航：
- PgUp: 上一页
- PgDown: 下一页

## 📋 开发计划

### 已实现功能
- ✅ PDF文件查看和渲染
- ✅ 文件打开、保存、另存为
- ✅ 撤销/重做功能
- ✅ 搜索和高亮
- ✅ 缩略图显示
- ✅ OCR插件系统
- ✅ 上传插件系统
- ✅ 下载插件系统
- ✅ 条码检测与分割
- ✅ PDF转图片
- ✅ 性能优化（异步加载、虚拟滚动、缓存）
- ✅ 应用图标
- ✅ 代码模块化重构
- ✅ 主窗口功能拆分

### 远期目标
- [ ] PDF合并功能
- [ ] PDF加密/解密
- [ ] PDF表单处理
- [ ] 更多OCR引擎支持
- [ ] 更多上传/下载协议支持
- [ ] 批量处理功能
- [ ] 云服务集成

## 💡 使用技巧

1. **快速打开文件**：使用快捷键 `Ctrl+O` 或点击工具栏的打开按钮
2. **另存为功能**：使用 `Ctrl+Shift+S` 或工具栏按钮，会使用当前文件名作为默认文件名
3. **缩略图导航**：左侧缩略图面板可直接点击跳转到指定页面
4. **状态提示**：底部状态栏实时显示操作状态和性能信息
5. **搜索高亮**：使用 `Ctrl+F` 搜索文本，支持高亮显示和结果导航
6. **插件配置**：可通过菜单栏的相应设置项配置OCR、上传、下载插件
7. **条码拆分**：使用工具栏的"条码拆分"按钮，可按条码自动分割PDF
8. **文档上传**：使用工具栏的"上传"按钮，可将当前文档上传到远程服务器
9. **远程下载**：使用菜单栏的"下载"功能，可下载远程PDF文件

## 🐛 问题反馈

如果在使用过程中遇到问题，请检查：

1. 虚拟环境是否正确激活
2. 依赖包是否完整安装
3. 系统是否支持PyQt5
4. PDF文件是否损坏或加密
5. 插件配置是否正确

## 📄 许可证

MIT License