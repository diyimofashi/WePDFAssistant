"""
Azure Vision OCR插件 - 核心实现
"""

import os
import time
import requests
from base64 import b64decode
from typing import Dict, List, Any
from app.core.ocr.ocr_plugin_interface import OCRPluginInterface, OCRResult, OCRErrorCode
from app.core.performance.ocr_performance_optimizer import cached_ocr_result


class AzureVisionOCR(OCRPluginInterface):
    """Azure Vision OCR插件实现类"""
    
    def __init__(self):
        """初始化插件"""
        super().__init__()
        self.plugin_name = "Azure Vision OCR Plugin"
        self.plugin_version = "1.0.0"
        self.plugin_author = "Azure Cognitive Services"
        self.config = {}
        
        # 插件特定的属性
        self.app_key = ""
        self.server_url = ""
        self.api_url = ""
        self.supported_languages = ["zh-Hans", "en", "ja", "ko", "auto"]
    
    def initialize(self, config: Dict[str, Any]) -> OCRResult:
        """
        初始化插件
        
        Args:
            config: 插件配置参数
            
        Returns:
            OCRResult: 初始化结果
        """
        try:
            # 保存配置
            self.config = config
            self.app_key = config.get("app_key", "")
            self.server_url = config.get("server_url", "")
            self.api_url = f"{self.server_url}/vision/v3.2/read/analyze"
            
            # 验证配置参数
            if not self.app_key or not self.server_url:
                return OCRResult(
                    code=OCRErrorCode.INIT_ERROR,
                    message="Azure Vision OCR初始化失败: 缺少必要的配置参数(app_key或server_url)",
                    plugin_name=self.plugin_name
                )
            
            self.is_initialized = True
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                message="Azure Vision OCR插件初始化成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            self.is_initialized = False
            return OCRResult(
                code=OCRErrorCode.INIT_ERROR,
                message=f"插件初始化失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    @cached_ocr_result(plugin_name="AzureVisionOCR", language="auto")
    def recognize_from_file(self, file_path: str, language: str = "auto") -> OCRResult:
        """
        从文件路径识别文本
        
        Args:
            file_path: 图片文件路径
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return OCRResult(
                code=OCRErrorCode.FILE_NOT_FOUND,
                message=f"文件不存在: {file_path}",
                plugin_name=self.plugin_name
            )
        
        try:
            # 检查是否支持指定语言
            if language != "auto" and language not in self.supported_languages:
                return OCRResult(
                    code=OCRErrorCode.UNSUPPORTED_LANGUAGE,
                    message=f"不支持的语言: {language}",
                    plugin_name=self.plugin_name
                )
            
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            
            result_data = self._perform_ocr_from_bytes(img_bytes, language)
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="Azure Vision OCR识别成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"Azure Vision OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    @cached_ocr_result(plugin_name="AzureVisionOCR", language="auto")
    def recognize_from_bytes(self, image_bytes: bytes, language: str = "auto") -> OCRResult:
        """
        从字节流识别文本
        
        Args:
            image_bytes: 图片字节流
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        try:
            # 检查是否支持指定语言
            if language != "auto" and language not in self.supported_languages:
                return OCRResult(
                    code=OCRErrorCode.UNSUPPORTED_LANGUAGE,
                    message=f"不支持的语言: {language}",
                    plugin_name=self.plugin_name
                )
            
            result_data = self._perform_ocr_from_bytes(image_bytes, language)
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="Azure Vision OCR识别成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"Azure Vision OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    @cached_ocr_result(plugin_name="AzureVisionOCR", language="auto")
    def recognize_from_base64(self, base64_string: str, language: str = "auto") -> OCRResult:
        """
        从Base64字符串识别文本
        
        Args:
            base64_string: Base64编码的图片字符串
            language: 识别语言，默认为自动识别
            
        Returns:
            OCRResult: 识别结果
        """
        try:
            # 检查是否支持指定语言
            if language != "auto" and language not in self.supported_languages:
                return OCRResult(
                    code=OCRErrorCode.UNSUPPORTED_LANGUAGE,
                    message=f"不支持的语言: {language}",
                    plugin_name=self.plugin_name
                )
            
            # 解码Base64字符串
            img_bytes = b64decode(base64_string)
            
            result_data = self._perform_ocr_from_bytes(img_bytes, language)
            
            return OCRResult(
                code=OCRErrorCode.SUCCESS,
                data=result_data,
                message="Azure Vision OCR识别成功",
                plugin_name=self.plugin_name
            )
            
        except Exception as e:
            return OCRResult(
                code=OCRErrorCode.RECOGNITION_FAILED,
                message=f"Azure Vision OCR识别失败: {str(e)}",
                plugin_name=self.plugin_name
            )
    
    def _perform_ocr_from_bytes(self, img_bytes: bytes, language: str = "auto") -> List[Dict[str, Any]]:
        """
        使用Azure Vision API执行OCR识别
        
        Args:
            img_bytes: 图片字节流
            language: 识别语言
            
        Returns:
            List[Dict[str, Any]]: 识别结果列表
        """
        headers = {
            "Ocp-Apim-Subscription-Key": self.app_key,
            "Content-Type": "application/octet-stream"
        }
        
        # 发送初始请求
        response = requests.post(self.api_url, headers=headers, data=img_bytes)
        
        # 检查初始响应
        if response.status_code != 202:
            raise Exception(f"API request failed with status code: {response.status_code}, message: {response.text}")
        
        # 获取操作位置URL
        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            raise Exception("No Operation-Location header in response")
        
        # 轮询获取结果
        result = self._get_operation_result(operation_location)
        
        if result["code"] != 100:
            raise Exception(result["data"])
        
        # 转换结果格式
        return self._convert_result_format(result["data"])
    
    def _get_operation_result(self, operation_url):
        """
        轮询获取操作结果
        
        Args:
            operation_url: 操作结果URL
            
        Returns:
            dict: 包含结果或错误信息的字典
        """
        result_headers = {
            "Ocp-Apim-Subscription-Key": self.app_key
        }
        
        max_retries = 300  # 最大重试次数
        retry_interval = 1  # 重试间隔（秒）
        
        for i in range(max_retries):
            try:
                response = requests.get(operation_url, headers=result_headers)
                
                if response.status_code == 200:
                    result_data = response.json()
                    status = result_data.get("status", "")
                    
                    if status == "succeeded":
                        # 处理成功结果
                        return self._process_result(result_data)
                    elif status == "failed" or status == "Failed":
                        return {"code": 207, "data": "[Error] OCR operation failed on server"}
                    # 如果还在运行中，继续等待
                elif response.status_code != 202:
                    return {"code": 208, "data": f"[Error] Failed to get operation result. Status code: {response.status_code}"}
                
                # 等待一段时间后重试
                time.sleep(retry_interval)
                
            except Exception as e:
                return {"code": 209, "data": f"[Error] Failed to get operation result: {e}"}
        
        return {"code": 210, "data": "[Error] OCR operation timeout"}
    
    def _process_result(self, result_data):
        """
        处理Azure Vision API返回的结果
        
        Args:
            result_data: API返回的原始数据
            
        Returns:
            dict: 处理后的结果
        """
        try:
            analyze_result = result_data.get("analyzeResult", {})
            read_results = analyze_result.get("readResults", [])
            
            # 转换为标准格式
            ocr_result = []
            for page_result in read_results:
                lines = page_result.get("lines", [])
                
                for line in lines:
                    # 提取文本和位置信息
                    text = line.get("text", "")
                    bounding_box = line.get("boundingBox", [])
                    
                    # 转换边界框格式
                    box = []
                    for i in range(0, len(bounding_box), 2):
                        if i + 1 < len(bounding_box):
                            box.append([bounding_box[i], bounding_box[i + 1]])
                    
                    # 如果边界框点数不足4个，补充默认值
                    while len(box) < 4:
                        box.append([0, 0])
                    
                    # 计算平均置信度
                    words = line.get("words", [])
                    score = 0
                    if words:
                        total_score = sum(word.get("confidence", 0) for word in words)
                        score = total_score / len(words)
                    
                    ocr_result.append({
                        "text": text,
                        "box": box,
                        "confidence": score
                    })
            
            return {"code": 100, "data": ocr_result}
            
        except Exception as e:
            return {"code": 211, "data": f"[Error] Failed to process OCR result: {e}"}

    def _convert_result_format(self, azure_result: List[Dict]) -> List[Dict[str, Any]]:
        """
        将Azure Vision API的结果转换为项目标准格式
        
        Args:
            azure_result: Azure Vision API返回的结果
            
        Returns:
            List[Dict[str, Any]]: 标准格式的OCR结果
        """
        standard_result = []
        
        for item in azure_result:
            text = item.get("text", "")
            box = item.get("box", [])  # box 是包含4个点坐标的列表: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            score = item.get("score", 0.0)
            
            # 使用原始的4点坐标格式作为bbox
            # 检查bbox格式是否为4个点的坐标
            if len(box) >= 4 and isinstance(box[0], list) and len(box[0]) == 2:
                # 格式已经是4个点的坐标: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                final_bbox = box
            else:
                # 如果格式不符合预期，使用默认值
                final_bbox = [[0, 0], [0, 0], [0, 0], [0, 0]]
            
            standard_result.append({
                "text": text,
                "confidence": score,
                "bbox": final_bbox,  # 保持4个点的坐标格式
                "language": "unknown"  ***REMOVED*** API通常不直接提供语言信息
            })
        
        return standard_result
    
    def get_supported_languages(self) -> List[str]:
        """
        获取支持的语言列表
        
        Returns:
            List[str]: 支持的语言标识列表
        """
        return self.supported_languages.copy()
    
    def cleanup(self) -> None:
        """
        清理资源
        在插件卸载或应用关闭时调用
        """
        ***REMOVED*** Vision OCR插件不需要清理本地资源
        self.is_initialized = False