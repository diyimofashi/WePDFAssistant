# PDFAssistant

**PDFAssistant** 是一款专为个人和企业用户打造的专业级 PDF 文档处理工具。它不仅是一个 PDF 阅读器，更是一个功能全面的 PDF 工作台，集成了 PDF 查看、编辑、转换、OCR 文字识别、条码处理、云存储协作等强大功能，帮助用户高效处理各类 PDF 文档。

## 💡 适用场景

- **办公文档处理**：快速编辑、合并、分割 PDF 文档，提升办公效率
- **PDF 扫描件处理**：将扫描的 PDF 转换为可搜索、可编辑的文档
- **文档归档管理**：通过条码自动分割大量 PDF 文档，便于归档管理
- **文档数字化**：批量 OCR 识别，将纸质文档快速数字化
- **多人协作办公**：通过云存储实现文档的云端备份和共享
- **批量文档处理**：批量加解密、转换格式，提高处理效率

## ✨ 核心优势

### 🎯 一站式解决方案
无需安装多个工具，PDFAssistant 集成了 PDF 处理所需的全部功能，从查看到编辑、从转换到识别、从本地处理到云端协作，一站式满足您的所有需求。

### 🚀 性能卓越
采用先进的虚拟滚动技术和智能缓存机制，即使是上千页的大型 PDF 也能流畅浏览，毫无卡顿。异步加载设计确保操作响应迅速，用户体验极佳。

### 🔍 智能识别
内置强大的 OCR 文字识别引擎，支持中英文混合识别，准确率高。支持单页识别、批量识别、截图识别等多种方式，轻松将扫描件转换为可搜索 PDF。

### 📊 条码智能分割
支持识别一维码（CODE128、CODE39、EAN13 等）和二维码（QR Code、PDF417），可根据条码内容自动分割 PDF 文档，是批量文档处理的利器。

### 🌐 云端集成
支持腾讯云 COS、阿里云 OSS 等主流云存储服务，轻松实现文档的云端备份和跨设备协作，重要文档永不丢失。

### 🔧 插件化架构
采用模块化插件设计，易于扩展功能。用户可以根据需求启用或禁用不同的插件，保持软件轻量高效。

### 🎨 现代化界面
简洁美观的界面设计，操作直观，学习成本低。支持多标签页浏览，可同时打开多个文档，提升工作效率。

## 📁 项目结构

```
PyPDF/
├── app/                          # 应用主包
│   ├── assets/                   # 资源文件
│   │   ├── app_icon.ico          # 应用图标
│   │   ├── app_icon.png          # 应用图标
│   │   ├── wechat_contact_qrcode.png  # 联系微信二维码
│   │   └── sponsor_qrcode.png         # 赞助二维码
│   ├── aurora_pdf/               # Aurora PDF 模块
│   ├── config/                   # 配置模块
│   │   ├── settings.py           # 应用设置和配置管理
│   │   ├── ocr_plugin_config.py  # OCR插件配置管理
│   │   ├── barcode_plugin_config.py  # 条码插件配置管理
│   │   ├── storage_plugin_config.py  # 存储插件配置管理
│   │   └── shortcut_config.py    # 快捷键配置管理
│   ├── core/                     # 核心功能模块
│   │   ├── processing/           # PDF处理与渲染
│   │   ├── main/                 # 主窗口功能模块
│   │   ├── performance/          # 缓存与性能优化
│   │   ├── ocr/                  # OCR系统
│   │   ├── barcode/              # 条码处理模块
│   │   ├── storage/              # 存储处理模块
│   │   └── editing/              # 编辑与历史记录
│   ├── managers/                 # 管理器模块
│   │   ├── file_manager.py       # 文件管理器
│   │   ├── ocr_plugin_manager.py # OCR插件管理器
│   │   ├── search_manager.py     # 搜索管理器
│   │   ├── split_manager.py      # 分割管理器
│   │   ├── view_controller.py    # 视图控制器
│   │   ├── storage_plugin_manager.py # 存储插件管理器
│   │   ├── barcode_plugin_manager.py   # 条码插件管理器
│   │   └── shortcut_manager.py    # 快捷键管理器
│   ├── ui/                       # UI界面模块
│   │   ├── styles.py             # 界面样式定义
│   │   ├── menu_manager.py       # 菜单管理器
│   │   ├── toolbar_manager.py    # 工具栏管理器
│   │   ├── context_menu_manager.py  # 右键菜单管理器
│   │   ├── virtual_scroll.py     # 虚拟滚动组件
│   │   ├── smart_thumbnail.py    # 智能缩略图
│   │   ├── ocr_page_label.py     # OCR页面标签
│   │   ├── screenshot_ocr_widget.py  # 截图选区组件
│   │   ├── barcode_result_dialog.py    # 条码结果对话框
│   │   ├── barcode_split_dialog.py     # 条码分割对话框
│   │   ├── ocr_settings_dialog.py     # OCR设置对话框
│   │   ├── storage_settings_dialog.py # 存储设置对话框
│   │   ├── shortcut_settings_dialog.py # 快捷键设置对话框
│   │   ├── password_dialog.py         # 密码输入对话框
│   │   └── batch_crypto_dialog.py     # 批量加密对话框
│   ├── utils/                    # 工具模块
│   │   └── logger.py             # 日志工具
│   ├── plugins/                  # OCR插件系统
│   ├── plugins-barcode/          # 条码插件系统
│   ├── plugins-storage/          # 存储插件系统
│   ├── llm/                      # LLM相关模块
│   ├── conversations/            # 对话记录
│   └── main.py                   # 主程序入口
├── dist/                         # 编译输出目录
├── docs/                         # 文档目录
├── cache/                        # 缓存目录
├── logs/                         # 日志目录
├── PDFAssistant/                 # 编译后的应用程序
├── requirements.txt              # 依赖包列表
├── run.bat                       # 一键启动脚本
├── start.py                      # 主启动脚本
└── README.md                     # 项目说明
```

## 🚀 如何启动

### 方式一：一键启动（推荐）

直接双击 `run.bat` 文件即可启动应用。

### 方式二：Python环境启动

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

### 方式三：使用编译后的可执行文件

直接运行 `PDFAssistant/` 目录下的可执行文件即可。

## 📦 编译打包为 EXE

### 前置要求

- **Python 3.8+**：已安装 Python
- **Nuitka**：Python 编译工具
- **Inno Setup**（可选）：用于创建 Windows 安装程序

### 步骤一：安装 Nuitka

在虚拟环境中安装 Nuitka：
```bash
pip install nuitka
```

### 步骤二：编译为 EXE

项目提供了两种编译脚本：

#### 方式一：完整编译（推荐）

双击运行 `build_nuitka.bat` 脚本：

```bash
build_nuitka.bat
```

该脚本会自动：
1. 检查并激活虚拟环境
2. 安装 Nuitka（如果未安装）
3. 清理旧的编译输出
4. 执行 Nuitka 编译（需要 10-30 分钟）
5. 复制必要的插件和配置文件到输出目录

编译完成后，可执行文件位于：`dist\start.dist\PDFAssistant.exe`

#### 方式二：快速编译

如果需要增量编译或使用较少资源，可以修改或创建快速编译脚本。完整编译脚本 `build_nuitka.bat` 使用了 4 个并行作业进行编译。

### 步骤三：创建安装程序（可选）

如果需要创建 Windows 安装程序（.exe），使用 Inno Setup：

1. 确保 Inno Setup 已安装
   - 下载地址：https://jrsoftware.org/isdl.php

2. 双击运行 `create_installer.bat`：

```bash
create_installer.bat
```

该脚本会：
1. 检查 Inno Setup 是否已安装
2. 使用 `create_installer.iss` 配置文件创建安装程序
3. 输出安装程序：`installer\PDFAssistant-Setup.exe`

### 编译说明

#### 编译参数

项目使用 `build_config.py` 管理编译参数，主要参数包括：

- `--standalone`：生成独立可执行文件
- `--enable-plugin=pyqt5`：启用 PyQt5 插件
- `--follow-imports`：跟随所有导入
- `--include-package=app`：包含 app 包
- `--include-data-dir`：包含数据目录（资源文件、配置文件）
- `--windows-console-mode=disable`：禁用控制台窗口
- `--windows-icon-from-ico`：设置应用程序图标

#### 编译输出

编译完成后，输出目录结构：

```
dist/
└── start.dist/
    ├── PDFAssistant.exe          # 主程序
    ├── app/                      # 应用包
    │   ├── assets/               # 资源文件
    │   ├── config/               # 配置文件
    │   ├── plugins/              # OCR插件
    │   ├── plugins-barcode/      # 条码插件
    │   └── plugins-storage/      # 存储插件
    └── about.md                  # 关于文件
```

#### 编译注意事项

1. **编译时间**：首次编译可能需要 10-30 分钟，取决于硬件性能
2. **磁盘空间**：编译过程中需要约 2-3GB 的临时空间
3. **输出大小**：生成的程序约 150-200MB
4. **虚拟环境**：确保虚拟环境已正确配置所有依赖

### 分发使用

编译完成后：

1. **直接分发**：
   - 将 `dist\start.dist\` 目录打包为 ZIP 文件
   - 用户解压后直接运行 `PDFAssistant.exe`

2. **安装程序分发**：
   - 使用 `create_installer.bat` 创建安装程序
   - 分发 `installer\PDFAssistant-Setup.exe`
   - 用户双击安装程序进行安装

### 故障排除

1. **Nuitka 未找到**：
   ```bash
   pip install nuitka
   ```

2. **缺少 C 编译器**（Windows）：
   - 下载并安装 Microsoft C++ Build Tools
   - 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/

3. **编译失败**：
   - 检查虚拟环境是否激活
   - 确保所有依赖已安装（`pip install -r requirements.txt`）
   - 查看错误日志了解详细信息

4. **运行时错误**：
   - 确保所有资源文件已正确复制到输出目录
   - 检查配置文件是否完整

## ⭐ 核心功能

### 📄 PDF文档处理
- **文件打开**：支持PDF文件、多张图片、图片目录批量打开
- **密码保护**：支持打开和保存加密的PDF文件
- **页面编辑**：插入、删除、复制、旋转页面
- **撤销/重做**：完整的操作历史管理
- **PDF分割**：支持单页、范围、分组、书签、条码等多种分割方式
- **PDF合并**：将多个PDF文档合并为一个
- **PDF转图片**：将PDF文档的每一页转换为图片
- **批量加解密**：批量处理PDF文件的加密/解密

### 🔍 OCR文字识别
- **单页OCR**：对当前页面执行OCR识别
- **批量OCR**：对全部页面批量执行OCR识别
- **截图OCR**：截图选区OCR识别功能（快捷键 Alt+S）
- **可搜索PDF**：生成包含OCR文本层的可搜索PDF
- **OCR文本层**：高亮显示识别结果，支持调试模式
- **多引擎支持**：支持RapidOCR、Azure Vision OCR等多种OCR引擎
- **性能优化**：支持并发识别，大幅提升批量处理速度

### 📊 条码处理
- **多种条码类型**：
  - 一维码：CODE128、CODE39、CODE93、CODABAR、EAN13、EAN8、UPCA、UPCE等
  - 二维码：QRCODE、PDF417、SQCODE
- **条码自动分割**：根据条码自动分割PDF文档
- **分割预览**：预览分割结果，确认后再执行
- **过滤规则**：支持设置条码过滤规则

### 🌐 云存储支持
- **云存储插件**：支持腾讯云COS、阿里云OSS等多种云存储
- **文件上传**：将PDF文档上传到云存储
- **文件下载**：从云存储下载PDF文件
- **配置灵活**：可设置服务器地址、认证信息等参数

### 👁️ 视图控制
- **缩放控制**：放大/缩小、适应宽度/高度/容器、实际尺寸、预设比例
- **页面导航**：上一页/下一页、跳转到指定页
- **缩略图导航**：智能缩略图，延迟加载，点击跳转
- **虚拟滚动**：支持流畅浏览大文件（1000+页）
- **多标签页**：支持在单个窗口中打开多个PDF文档

### 🔎 搜索功能
- **文本搜索**：在PDF中搜索指定文本（快捷键 Ctrl+F）
- **区分大小写**：支持区分大小写的搜索
- **全词匹配**：支持全词匹配搜索
- **OCR文本搜索**：支持在OCR识别的文本中搜索
- **结果高亮**：搜索结果自动高亮显示

### ⚙️ 系统功能
- **快捷键管理**：可自定义快捷键，支持冲突检测
- **配置管理**：灵活的应用配置管理
- **日志系统**：完整的日志记录，便于问题排查
- **性能监控**：实时显示内存使用、缓存命中率等信息
- **智能缓存**：LRU缓存策略，内存和磁盘双重缓存

## ⌨️ 常用快捷键

### 文件操作
- `Ctrl+O`：打开文件
- `Ctrl+S`：保存文件
- `Ctrl+Shift+S`：另存为
- `Ctrl+W`：关闭当前标签

### 视图操作
- `Ctrl++`：放大
- `Ctrl+-`：缩小
- `Ctrl+0`：实际尺寸

### 页面导航
- `PgUp`：上一页
- `PgDown`：下一页

### 搜索
- `Ctrl+F`：搜索文本

### OCR操作
- `Alt+S`：截图OCR

### 其他
- `Ctrl+K`：快捷键设置
- `Ctrl+Q`：退出

## 🛠️ 技术架构

- **Python 3.8+**：编程语言
- **PyQt5**：桌面应用框架，提供现代化UI
- **PyMuPDF (fitz)**：PDF渲染引擎，高性能PDF处理
- **Pillow**：图像处理库，支持多种图片格式
- **PyZBar**：条码识别，支持一维码和二维码
- **OpenCV**：计算机视觉处理，用于截图OCR等功能
- **模块化设计**：清晰的分层架构
- **插件化架构**：支持功能扩展
- **混入类设计**：功能模块化，便于维护
- **异步处理**：使用QThread实现异步操作
- **LRU缓存**：高效的内存和磁盘缓存策略

## 📦 依赖项

### 核心依赖
- PyQt5 - GUI框架
- PyMuPDF - PDF处理引擎
- Pillow - 图像处理

### 功能依赖
- PyZBar - 条码识别
- OpenCV - 计算机视觉
- picologging - 日志记录
- psutil - 系统监控
- requests - HTTP请求

### OCR依赖
- pytesseract - Tesseract OCR

### 云存储依赖
- cos-python-sdk-v5 - 腾讯云COS
- oss2 - 阿里云OSS

完整依赖列表请查看 `requirements.txt`

## 📄 许可证

本项目采用 MIT License 开源协议，是最宽松的开源协议之一。

您可以：
- ✅ 自由使用、复制、修改和分发
- ✅ 用于商业用途
- ✅ 将本代码集成到您的产品中
- ✅ 修改代码并作为开源或闭源发布

唯一的限制是：
- ⚠️ 保留原作者的版权声明和许可证声明

## 📞 联系与赞助

如果您对本项目有任何问题、建议或想要赞助项目的发展，欢迎联系我！

### 联系方式

![微信公众号](app/assets/wechat_contact_qrcode.png)

扫描二维码关注微信公众号，获取最新动态和问题解答。

### 赞助支持

如果您觉得本项目对您有帮助，欢迎赞助支持项目的持续开发和维护！

![赞助二维码](app/assets/sponsor_qrcode.png)

感谢您的支持！

## 📝 更新日志

### 当前版本
- 支持PDF查看、编辑、分割、合并
- OCR文字识别（多引擎支持）
- 条码检测与自动分割
- 云存储支持（腾讯云COS、阿里云OSS）
- 虚拟滚动和智能缓存
- 多标签页支持

详细更新记录请查看项目文档。
