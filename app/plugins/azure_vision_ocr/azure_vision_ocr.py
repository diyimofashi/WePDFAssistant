# -*- coding: utf-8 -*-
# 调用 Azure Vision OCR API 的 Python Api

import time
import requests
from base64 import b64decode

class Api:  # 公开接口
    def __init__(self, globalArgd):
        # 初始化参数
        self.app_key = globalArgd.get("app_key", "")
        self.server_url = globalArgd.get("server_url", "")
        self.api_url = f"{self.server_url}/vision/v3.2/read/analyze"
        
    def start(self, argd):  # 启动引擎。返回： "" 成功，"[Error] xxx" 失败
        # 更新参数
        self.app_key = argd.get("app_key", self.app_key)
        self.server_url = argd.get("server_url", self.server_url)
        self.api_url = f"{self.server_url}/vision/v3.2/read/analyze"
        return ""

    def stop(self):  # 停止引擎
        pass

    def runPath(self, imgPath: str):  # 路径识图
        try:
            with open(imgPath, "rb") as f:
                imgBytes = f.read()
            return self._analyze_image(imgBytes)
        except Exception as e:
            return {"code": 201, "data": f"[Error] Failed to read image file: {e}"}

    def runBytes(self, imageBytes):  # 字节流
        try:
            return self._analyze_image(imageBytes)
        except Exception as e:
            return {"code": 202, "data": f"[Error] Failed to process image bytes: {e}"}

    def runBase64(self, imageBase64):  # base64字符串
        try:
            # 将base64转换为字节数据
            imgBytes = b64decode(imageBase64)
            return self._analyze_image(imgBytes)
        except Exception as e:
            return {"code": 203, "data": f"[Error] Failed to process base64 image: {e}"}

    def _analyze_image(self, imgBytes):
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": self.app_key,
                "Content-Type": "application/octet-stream"
            }
            
            # 发送初始请求
            response = requests.post(self.api_url, headers=headers, data=imgBytes)
            
            # 检查初始响应
            if response.status_code != 202:
                return {"code": 204, "data": f"[Error] API request failed with status code: {response.status_code}, message: {response.text}"}
            
            # 获取操作位置URL
            operation_location = response.headers.get("Operation-Location")
            if not operation_location:
                return {"code": 205, "data": "[Error] No Operation-Location header in response"}
            
            # 轮询获取结果
            result = self._get_operation_result(operation_location)
            return result
            
        except Exception as e:
            return {"code": 206, "data": f"[Error] Failed to analyze image: {e}"}

    def _get_operation_result(self, operation_url):
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
                        "bbox": box,
                        "confidence": score
                    })
            
            return {"code": 100, "data": ocr_result}
            
        except Exception as e:
            return {"code": 211, "data": f"[Error] Failed to process OCR result: {e}"}
