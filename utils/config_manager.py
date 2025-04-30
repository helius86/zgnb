#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理器
用于管理应用程序的配置设置，包括API密钥、存储路径等
"""

import os
import json
import logging

# 配置文件路径
CONFIG_FILE = "audio_app_config.json"
SECRETS_FILE = "config/secrets.json"

# 默认配置
DEFAULT_CONFIG = {
    # 音频提取配置
    "segment_duration": 3600,  # 默认分割时长（秒）
    "audio_format": "mp3",
    "audio_bitrate": "128k",
    "audio_channels": 1,
    "audio_sample_rate": 16000,
    "noise_reduction": False,
    "normalize_volume": True,
    
    # 转录配置
    "max_workers": 3,  # 并行处理的任务数
    "max_wait_time": 1800,  # 最长等待时间（秒）
    
    # 文件路径配置
    "last_input_dir": "",  # 上次使用的输入目录
    "last_output_dir": ""   # 上次使用的输出目录
}

class ConfigManager:
    """配置管理类，负责加载、保存和管理应用程序配置"""
    
    def __init__(self):
        self.logger = logging.getLogger("ConfigManager")
        self.config = DEFAULT_CONFIG.copy()
        self.secrets = {"api": {}, "tos": {}}
        self.load_config()
        self.load_secrets()
    
    def load_secrets(self):
        """从secrets文件加载敏感信息"""
        try:
            if os.path.exists(SECRETS_FILE):
                with open(SECRETS_FILE, 'r', encoding='utf-8') as f:
                    self.secrets = json.load(f)
                self.logger.info("敏感信息配置文件加载成功")
            else:
                self.logger.warning(f"敏感信息配置文件 {SECRETS_FILE} 不存在，将使用空配置")
                # 创建默认的空结构
                self.secrets = {"api": {}, "tos": {}}
        except Exception as e:
            self.logger.error(f"加载敏感信息配置文件失败: {e}")
            self.secrets = {"api": {}, "tos": {}}
    
    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 更新配置，同时保留默认配置中的项
                    for key, value in loaded_config.items():
                        if key in self.config:
                            self.config[key] = value
                self.logger.info("配置文件加载成功")
            else:
                self.logger.info("配置文件不存在，使用默认配置")
                self.save_config()  # 创建默认配置文件
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            self.logger.info("使用默认配置")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info("配置文件保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            return False
    
    def save_secrets(self):
        """保存敏感信息到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(SECRETS_FILE), exist_ok=True)
            with open(SECRETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.secrets, f, ensure_ascii=False, indent=2)
            self.logger.info("敏感信息配置文件保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存敏感信息配置文件失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def get_secret(self, section, key, default=None):
        """获取敏感信息配置项"""
        return self.secrets.get(section, {}).get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value
        return self
    
    def update(self, config_dict):
        """批量更新配置"""
        for key, value in config_dict.items():
            self.config[key] = value
        return self