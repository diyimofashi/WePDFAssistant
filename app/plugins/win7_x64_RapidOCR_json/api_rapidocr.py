"""
RapidOCR插件实现
基于RapidOCR-json引擎的OCR插件实现，符合标准OCR插件接口规范
"""

import os
from typing import Dict, List, Any
from app.core.ocr.ocr_plugin_interface import OCRPluginInterface, OCRResult, OCRErrorCode
from .rapidocr import Rapid_pipe
from .config import LangDict, global_options, local_options


class Api(OCRPluginInterface):  # 公开接口
    """RapidOCR插件实现类"""
    
    def __init__(self, globalArgd=None):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "RapidOCR (Local)"
        self.plugin_version = "1.0.0"
        self.plugin_author = "hiroi-sora"
        
        # exe路径
        self.exePath = os.path.dirname(os.path.abspath(__file__)) + "/RapidOCR-json.exe"
        
        # 测试路径是否存在
        if not os.path.exists(self.exePath):
            raise ValueError(f'[Error] Exe path "{self.exePath}" does not exist.')
        
        # 初始化参数
        self.api = None  # api对象
        self.exeConfigs = {  # exe启动参数字典
            "models": "models",
            "ensureAscii": 1,
            "det": None,
            "cls": None,
            "rec": None,
            "keys": None,
            "doAngle": 0,
            "mostAngle": 0,
            "maxSideLen": None,
            "numThread": globalArgd["numThread"] if globalArgd and "numThread" in globalArgd else 4,
        }
    
    def initialize(self, config: Dict[str, Any]) -> OCRResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            OCRResult: 初始化结果
        """
        try:
            # 更新线程数配置
            if "numThread" in config:
                self.exeConfigs["numThread"] = config["numThread"]
            
            self.is_initialized = True
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                message="RapidOCR插件初始化成功",
                plugin_name=self.plugin_name
            )
        except Exception as e:
            self.is_initialized = False
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"RapidOCR插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_file(self, file_path: str, language: str = "auto") -> OCRResult:
        """
        从文件路径识别文本
        
        Args:
            file_path: 图片文件路径
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        if not self.is_initialized:
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message="插件未初始化",
                plugin_name=self.plugin_name
            )
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return OCRResult(
                code=OCRErrorCode.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                plugin_name=self.plugin_name
            )
        
        try:
            # 启动OCR引擎
            start_result = self.start({"language": language})
            if start_result != "":
                return OCRResult(
                    code=OCRErrorCode.RECOGNITION_FAILED,
                    message=f"OCR引擎启动失败: {start_result}",
                    plugin_name=self.plugin_name
                )
            
            # 执行OCR识别
            raw_result = self.runPath(file_path)
            
            # 转换结果格式
            converted_result = self._convert_result(raw_result)
            
            return converted_result
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_bytes(self, image_bytes: bytes, language: str = "auto") -> OCRResult:
        """
        从字节流识别文本
        
        Args:
            image_bytes: 图片字节流
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        if not self.is_initialized:
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message="插件未初始化",
                plugin_name=self.plugin_name
            )
        
        try:
            # 启动OCR引擎
            start_result = self.start({"language": language})
            if start_result != "":
                return OCRResult(
                    code=OCRErrorCode.RECOGNITION_FAILED,
                    message=f"OCR引擎启动失败: {start_result}",
                    plugin_name=self.plugin_name
                )
            
            # 执行OCR识别
            raw_result = self.runBytes(image_bytes)
            
            # 转换结果格式
            converted_result = self._convert_result(raw_result)
            
            return converted_result
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def recognize_from_base64(self, base64_string: str, language: str = "auto") -> OCRResult:
        """
        从Base64字符串识别文本
        
        Args:
            base64_string: Base64编码的图片字符串
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        if not self.is_initialized:
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message="插件未初始化",
                plugin_name=self.plugin_name
            )
        
        try:
            # 启动OCR引擎
            start_result = self.start({"language": language})
            if start_result != "":
                return OCRResult(
                    code=OCRErrorCode.RECOGNITION_FAILED,
                    message=f"OCR引擎启动失败: {start_result}",
                    plugin_name=self.plugin_name
                )
            
            # 执行OCR识别
            raw_result = self.runBase64(base64_string)
            
            # 转换结果格式
            converted_result = self._convert_result(raw_result)
            
            return converted_result
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言标识列表
        """
        # 从配置中获取支持的语言列表
        language_options = local_options.get("language", {}).get("optionsList", [])
        languages = [option[0] for option in language_options]
        return languages
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        if self.api:
            self.stop()
        self.api = None
        self.is_initialized = False
    
    def start(self, argd):  # 启动引擎。返回： "" 成功，"[Error] xxx" 失败
        """启动OCR引擎"""
        # 加载局部参数
        tempConfigs = self.exeConfigs.copy()
        try:
            # 处理自动语言检测
            if argd["language"] == "auto":
                # 使用第一个可用的语言作为默认语言
                first_lang = next(iter(LangDict)) if LangDict else None
                if first_lang:
                    lang = LangDict[first_lang]
                else:
                    lang = {}
            else:
                lang = LangDict[argd["language"]]
            tempConfigs.update(lang)
            if argd.get("angle", False):
                tempConfigs["doAngle"] = tempConfigs["mostAngle"] = 1
            else:
                tempConfigs["doAngle"] = tempConfigs["mostAngle"] = 0
            tempConfigs["maxSideLen"] = argd.get("maxSideLen", 1024)
        except Exception as e:
            self.api = None
            return f"[Error] OCR start fail. Argd: {argd}\n{e}"

        # 若引擎已启动，且局部参数与传入参数一致，则无需重启
        if not self.api == None:
            if set(tempConfigs.items()) == set(self.exeConfigs.items()):
                return ""
            # 若引擎已启动但需要更改参数，则停止旧引擎
            self.stop()
        # 启动新引擎
        self.exeConfigs = tempConfigs
        try:
            self.api = Rapid_pipe(self.exePath, tempConfigs)
        except Exception as e:
            self.api = None
            return f"[Error] OCR init fail. Argd: {tempConfigs}\n{e}"
        return ""

    def stop(self):  # 停止引擎
        """停止OCR引擎"""
        if self.api == None:
            return
        self.api.exit()
        self.api = None

    def runPath(self, imgPath: str):  # 路径识图
        """从文件路径识别"""
        res = self.api.run(imgPath)
        return res

    def runBytes(self, imageBytes):  # 字节流
        """从字节流识别"""
        res = self.api.runBytes(imageBytes)
        return res

    def runBase64(self, imageBase64):  # base64字符串
        """从Base64字符串识别"""
        res = self.api.runBase64(imageBase64)
        return res
    
    def _convert_result(self, raw_result: Dict[str, Any]) -> OCRResult:
        """
        转换RapidOCR的原始结果到标准格式

        Args:
            raw_result: RapidOCR的原始结果

        Returns:
            OCRResult: 转换后的标准结果
        """
        try:
            # 检查结果码
            code = raw_result.get("code", 0)

            if code == 100 or code == 101:  # 成功或部分成功
                data = raw_result.get("data", [])

                # 转换数据格式
                converted_data = []
                for item in data:
                    if isinstance(item, dict):
                        converted_item = {
                            "text": item.get("text", ""),
                            "confidence": item.get("score", 0),
                            "bbox": item.get("box", []),  # RapidOCR返回"box"，映射到标准格式"bbox"
                            "language": "unknown",  # RapidOCR不直接提供语言信息
                            "end": item.get("end", "")
                        }
                        converted_data.append(converted_item)

                return OCRResult(
                    code=OCRErrorCode.SUCCESS,
                    data=converted_data,
                    message="OCR识别成功",
                    plugin_name=self.plugin_name
                )
            elif code == 200:  # 未识别到文字
                return OCRResult(
                    code=OCRErrorCode.SUCCESS,
                    data=[],
                    message="图片中未识别到文字",
                    plugin_name=self.plugin_name
                )
            else:  # 其他错误
                error_msg = raw_result.get("data", "未知错误")
                return OCRResult(
                    code=OCRErrorCode.RECOGNITION_FAILED,
                    message=f"OCR识别失败: {error_msg}",
                    plugin_name=self.plugin_name
                )

        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"结果转换失败: {str(e)}",
                plugin_name=self.plugin_name
            )