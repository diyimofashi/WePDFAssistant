"""
高级条码拆分插件配置文件
定义插件的配置项和默认值
"""

from app.config.barcode_plugin_config import ConfigItem, ConfigItemType


# 定义插件配置项
PLUGIN_CONFIG_DEFINITIONS = [
    # 拆分规则
    ConfigItem(
        key="split_position_rule",
        title="拆分位置规则",
        type_=ConfigItemType.ENUM,
        default="first_page",
        options_list=["first_page", "last_page", "separator_page"],
        description="拆分位置规则：first_page(首页规则)、last_page(尾页规则)、separator_page(分隔页规则)"
    ),
    ConfigItem(
        key="separator_barcodes",
        title="分隔条码",
        type_=ConfigItemType.LIST,
        default=[],
        description="分隔页规则使用的分隔条码列表（仅separator_page模式有效）"
    ),
    ConfigItem(
        key="keep_separator_page",
        title="保留分隔页",
        type_=ConfigItemType.BOOLEAN,
        default=False,
        description="是否在结果中保留分隔页（仅separator_page模式有效）"
    ),
    ConfigItem(
        key="merge_same_barcode",
        title="合并相同条码",
        type_=ConfigItemType.BOOLEAN,
        default=False,
        description="是否将相同条码值的页面合并到同一个文件（适合批次归档）"
    ),
    
    # 条码类型过滤
    ConfigItem(
        key="enabled_types",
        title="启用的条码类型",
        type_=ConfigItemType.LIST,
        default=["ALL_TYPES"],
        description="要检测的条码类型列表"
    ),
    
    # 条码内容过滤
    ConfigItem(
        key="min_length",
        title="最小长度",
        type_=ConfigItemType.INTEGER,
        default=1,
        min_value=1,
        max_value=1000,
        description="条码内容最小长度"
    ),
    ConfigItem(
        key="max_length",
        title="最大长度",
        type_=ConfigItemType.INTEGER,
        default=1000,
        min_value=1,
        max_value=10000,
        description="条码内容最大长度"
    ),
    ConfigItem(
        key="include_keywords",
        title="包含关键词",
        type_=ConfigItemType.LIST,
        default=[],
        description="条码内容必须包含的关键词列表"
    ),
    ConfigItem(
        key="exclude_keywords",
        title="排除关键词",
        type_=ConfigItemType.LIST,
        default=[],
        description="条码内容必须排除的关键词列表"
    ),
    ConfigItem(
        key="include_regex",
        title="包含正则表达式",
        type_=ConfigItemType.STRING,
        default="",
        description="条码内容必须匹配的正则表达式"
    ),
    ConfigItem(
        key="exclude_regex",
        title="排除正则表达式",
        type_=ConfigItemType.STRING,
        default="",
        description="条码内容必须排除的正则表达式"
    ),
    
    # 方向/区域过滤
    ConfigItem(
        key="horizontal_only",
        title="仅水平条码",
        type_=ConfigItemType.BOOLEAN,
        default=False,
        description="是否只识别水平方向的条码（排除旋转页、附件页中的垂直条码）"
    ),
    ConfigItem(
        key="filter_region",
        title="过滤区域",
        type_=ConfigItemType.LIST,
        default=[],
        description="限定条码检测的矩形区域 [x1, y1, x2, y2]，留空则检测整个页面"
    ),
    
    # 输出配置
    ConfigItem(
        key="use_barcode_filename",
        title="使用条码值作为文件名",
        type_=ConfigItemType.BOOLEAN,
        default=True,
        description="是否使用条码值作为输出文件的文件名"
    ),
    ConfigItem(
        key="filename_template",
        title="文件名模板",
        type_=ConfigItemType.STRING,
        default="{barcode}_{index}",
        description="输出文件名的模板，支持变量：{barcode}, {index}"
    ),
    
    # 检测配置
    ConfigItem(
        key="max_barcode_count",
        title="最大条码数量",
        type_=ConfigItemType.INTEGER,
        default=100,
        min_value=1,
        max_value=1000,
        description="单页检测的最大条码数量"
    ),
]
