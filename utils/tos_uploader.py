#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TOS上传器模块
负责将文件上传到火山引擎对象存储(TOS)
"""

import os
import logging
import uuid
from datetime import datetime

# 条件导入tos库
try:
    import tos
    HAS_TOS = True
except ImportError:
    HAS_TOS = False
    import warnings
    warnings.warn("未安装TOS SDK，上传功能将不可用", ImportWarning)

class TosUploader:
    """火山引擎对象存储上传器"""
    
    def __init__(self, ak, sk, endpoint, region, bucket):
        """
        初始化TOS客户端
        
        参数:
            ak (str): Access Key
            sk (str): Secret Key
            endpoint (str): 访问端点
            region (str): 区域
            bucket (str): 存储桶名称
        """
        self.ak = ak
        self.sk = sk
        self.endpoint = endpoint
        self.region = region
        self.bucket = bucket
        self.client = None
        self.logger = logging.getLogger("TosUploader")
        
        # 初始化客户端
        self.initialize_client()

    def initialize_client(self):
        """初始化TOS客户端"""
        if not HAS_TOS:
            self.logger.error("未安装TOS SDK，无法使用上传功能")
            return False
            
        try:
            self.client = tos.TosClientV2(self.ak, self.sk, self.endpoint, self.region)
            self.logger.info("TOS客户端初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"TOS客户端初始化失败: {e}")
            return False

    def upload_file(self, file_path, object_key=None, progress_callback=None):
        """
        上传单个文件到TOS存储
        
        参数:
            file_path (str): 本地文件路径
            object_key (str, optional): 对象键名，不指定时使用文件名
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            str: 上传成功后的URL，失败返回None
        """
        # 检查TOS客户端是否可用
        if not HAS_TOS or not self.client:
            self.logger.error("TOS客户端不可用")
            return None
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            self.logger.error(f"错误: 文件 {file_path} 不存在!")
            return None

        # 如果未指定对象键，使用文件名
        if not object_key:
            file_name = os.path.basename(file_path)
            # 添加时间戳前缀，避免文件名冲突
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_suffix = uuid.uuid4().hex[:8]
            object_key = f"audio_transcription/{timestamp}_{random_suffix}_{file_name}"

        try:
            self.logger.info(f"开始上传: {file_path} -> {object_key}")
            
            # 定义进度回调
            def upload_progress(consumed_bytes, total_bytes, rw_once_bytes, type):
                if total_bytes and progress_callback:
                    progress = int(100 * float(consumed_bytes) / float(total_bytes))
                    progress_callback(progress, f"已上传: {consumed_bytes}/{total_bytes} 字节")
            
            # 上传文件
            result = self.client.put_object_from_file(
                self.bucket, 
                object_key, 
                file_path,
                data_transfer_listener=upload_progress if progress_callback else None
            )
            
            self.logger.info(f"上传成功: {file_path}, 状态码: {result.status_code}")
            
            # 生成对象的访问URL
            object_url = f"https://{self.bucket}.{self.endpoint}/{object_key}"
            self.logger.info(f"文件URL: {object_url}")
            
            return object_url
            
        except Exception as e:
            self.logger.error(f"上传失败: {file_path}, 错误: {e}")
            return None
    
    def batch_upload(self, file_paths, progress_callback=None):
        """
        批量上传文件
        
        参数:
            file_paths (list): 本地文件路径列表
            progress_callback (callable, optional): 总体进度回调函数
            
        返回:
            dict: 文件路径到URL的映射，失败的文件映射到None
        """
        results = {}
        total_files = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            # 更新总体进度
            if progress_callback:
                overall_progress = int(100 * i / total_files)
                progress_callback(overall_progress, f"正在上传第 {i+1}/{total_files} 个文件: {os.path.basename(file_path)}")
            
            # 单个文件进度回调
            def file_progress(percent, message):
                if progress_callback:
                    # 计算总体进度：当前文件的进度占比为 1/total_files
                    file_contribution = percent / total_files
                    overall_progress = int(100 * i / total_files + file_contribution)
                    progress_callback(overall_progress, message)
            
            # 上传文件
            url = self.upload_file(file_path, progress_callback=file_progress)
            results[file_path] = url
        
        # 最终进度
        if progress_callback:
            progress_callback(100, f"批量上传完成，共 {total_files} 个文件")
        
        return results
    
    def check_file_exists(self, object_key):
        """
        检查TOS存储中是否存在指定对象
        
        参数:
            object_key (str): 对象键名
            
        返回:
            bool: 对象是否存在
        """
        if not HAS_TOS or not self.client:
            self.logger.error("TOS客户端不可用")
            return False
            
        try:
            self.client.head_object(self.bucket, object_key)
            return True
        except tos.exceptions.TosServerError as e:
            if e.status_code == 404:  # 对象不存在
                return False
            raise  # 其他错误重新抛出