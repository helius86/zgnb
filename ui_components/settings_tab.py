#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置选项卡
提供应用程序全局设置的界面
"""

import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
                             QTabWidget, QCheckBox, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal

from utils.log_handler import setup_logger
from utils.config_manager import SECRETS_FILE

class SettingsTab(QWidget):
    """设置选项卡，提供应用程序全局设置的界面"""
    
    # 定义信号
    config_updated = pyqtSignal()  # 配置更新信号
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # 设置界面
        self.setup_ui()
        
        # 更新控件内容
        self.load_settings()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # API设置选项卡
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        # 火山引擎API配置
        api_group = QGroupBox("火山引擎API配置")
        api_form = QFormLayout()
        
        # APP ID
        self.app_id_input = QLineEdit()
        api_form.addRow("APP ID:", self.app_id_input)
        
        # Access Token
        self.access_token_input = QLineEdit()
        api_form.addRow("Access Token:", self.access_token_input)
        
        api_group.setLayout(api_form)
        api_layout.addWidget(api_group)
        
        # TOS存储配置
        tos_group = QGroupBox("TOS存储配置")
        tos_form = QFormLayout()
        
        # Access Key
        self.tos_ak_input = QLineEdit()
        tos_form.addRow("Access Key:", self.tos_ak_input)
        
        # Secret Key
        self.tos_sk_input = QLineEdit()
        tos_form.addRow("Secret Key:", self.tos_sk_input)
        
        # 端点
        self.tos_endpoint_input = QLineEdit()
        tos_form.addRow("端点 (Endpoint):", self.tos_endpoint_input)
        
        # 区域
        self.tos_region_input = QLineEdit()
        tos_form.addRow("区域 (Region):", self.tos_region_input)
        
        # 存储桶
        self.tos_bucket_input = QLineEdit()
        tos_form.addRow("存储桶 (Bucket):", self.tos_bucket_input)
        
        tos_group.setLayout(tos_form)
        api_layout.addWidget(tos_group)
        
        # 添加到选项卡
        tab_widget.addTab(api_tab, "API设置")
        
        # 音频处理选项卡
        audio_tab = QWidget()
        audio_layout = QVBoxLayout(audio_tab)
        
        # 音频提取设置
        extract_group = QGroupBox("音频提取设置")
        extract_form = QFormLayout()
        
        # 分段时长
        self.segment_duration_input = QSpinBox()
        self.segment_duration_input.setRange(0, 7200)
        self.segment_duration_input.setValue(3600)
        self.segment_duration_input.setSuffix(" 秒")
        self.segment_duration_input.setToolTip("设置为0表示不分段")
        extract_form.addRow("分段时长:", self.segment_duration_input)
        
        # 音频格式
        self.audio_format_input = QComboBox()
        self.audio_format_input.addItems(["mp3", "wav", "ogg", "flac"])
        extract_form.addRow("音频格式:", self.audio_format_input)
        
        # 音频比特率
        self.audio_bitrate_input = QComboBox()
        self.audio_bitrate_input.addItems(["64k", "128k", "192k", "256k", "320k"])
        extract_form.addRow("音频比特率:", self.audio_bitrate_input)
        
        # 音频通道
        self.audio_channels_input = QComboBox()
        self.audio_channels_input.addItems(["1 (单声道)", "2 (立体声)"])
        extract_form.addRow("音频通道:", self.audio_channels_input)
        
        # 音频采样率
        self.audio_sample_rate_input = QComboBox()
        self.audio_sample_rate_input.addItems(["8000 Hz", "16000 Hz", "22050 Hz", "44100 Hz", "48000 Hz"])
        extract_form.addRow("音频采样率:", self.audio_sample_rate_input)
        
        # 音频增强选项
        enhance_layout = QHBoxLayout()
        self.noise_reduction_input = QCheckBox("降噪")
        self.normalize_volume_input = QCheckBox("音量归一化")
        enhance_layout.addWidget(self.noise_reduction_input)
        enhance_layout.addWidget(self.normalize_volume_input)
        extract_form.addRow("音频增强:", enhance_layout)
        
        extract_group.setLayout(extract_form)
        audio_layout.addWidget(extract_group)
        
        # 添加到选项卡
        tab_widget.addTab(audio_tab, "音频设置")
        
        # 转录设置选项卡
        transcribe_tab = QWidget()
        transcribe_layout = QVBoxLayout(transcribe_tab)
        
        # 转录设置
        transcribe_group = QGroupBox("转录设置")
        transcribe_form = QFormLayout()
        
        # 并行处理设置
        self.max_workers_input = QSpinBox()
        self.max_workers_input.setRange(1, 5)
        self.max_workers_input.setValue(3)
        self.max_workers_input.setToolTip("同时处理的任务数量")
        transcribe_form.addRow("并行任务数:", self.max_workers_input)
        
        # 最大等待时间
        self.max_wait_time_input = QSpinBox()
        self.max_wait_time_input.setRange(300, 3600)
        self.max_wait_time_input.setValue(1800)
        self.max_wait_time_input.setSuffix(" 秒")
        self.max_wait_time_input.setToolTip("转录任务的最大等待时间")
        transcribe_form.addRow("最大等待时间:", self.max_wait_time_input)
        
        transcribe_group.setLayout(transcribe_form)
        transcribe_layout.addWidget(transcribe_group)
        
        # 添加到选项卡
        tab_widget.addTab(transcribe_tab, "转录设置")
        
        # 添加选项卡控件到主布局
        layout.addWidget(tab_widget)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存设置")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.reset_btn = QPushButton("恢复默认设置")
        self.reset_btn.clicked.connect(self.confirm_reset)
        
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.reset_btn)
        
        layout.addLayout(buttons_layout)
        
        # 日志输出区域
        log_group = QGroupBox("设置日志")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 设置日志处理器
        self.logger = setup_logger(self.log_output, "SettingsTab")
    
    def load_settings(self):
        """从配置加载设置"""
        # API配置
        self.app_id_input.setText(self.config.get_secret("api", "app_id", ""))
        self.access_token_input.setText(self.config.get_secret("api", "access_token", ""))
        
        # TOS存储配置
        self.tos_ak_input.setText(self.config.get_secret("tos", "ak", ""))
        self.tos_sk_input.setText(self.config.get_secret("tos", "sk", ""))
        self.tos_endpoint_input.setText(self.config.get_secret("tos", "endpoint", ""))
        self.tos_region_input.setText(self.config.get_secret("tos", "region", ""))
        self.tos_bucket_input.setText(self.config.get_secret("tos", "bucket", ""))
        
        # 音频提取设置
        self.segment_duration_input.setValue(self.config.get("segment_duration", 3600))
        
        # 音频格式
        audio_format = self.config.get("audio_format", "mp3")
        index = self.audio_format_input.findText(audio_format)
        if index >= 0:
            self.audio_format_input.setCurrentIndex(index)
            
        # 比特率
        audio_bitrate = self.config.get("audio_bitrate", "128k")
        index = self.audio_bitrate_input.findText(audio_bitrate)
        if index >= 0:
            self.audio_bitrate_input.setCurrentIndex(index)
            
        # 音频通道
        audio_channels = self.config.get("audio_channels", 1)
        index = 0 if audio_channels == 1 else 1
        self.audio_channels_input.setCurrentIndex(index)
        
        # 采样率
        audio_sample_rate = str(self.config.get("audio_sample_rate", 16000)) + " Hz"
        index = self.audio_sample_rate_input.findText(audio_sample_rate)
        if index >= 0:
            self.audio_sample_rate_input.setCurrentIndex(index)
            
        # 音频增强
        self.noise_reduction_input.setChecked(self.config.get("noise_reduction", False))
        self.normalize_volume_input.setChecked(self.config.get("normalize_volume", True))
        
        # 转录设置
        self.max_workers_input.setValue(self.config.get("max_workers", 3))
        self.max_wait_time_input.setValue(self.config.get("max_wait_time", 1800))
        
        self.logger.info("已加载配置设置")
    
    def save_settings(self):
        """保存设置到配置"""
        try:
            # 提取通道数（从"1 (单声道)"格式中获取数字）
            channels_text = self.audio_channels_input.currentText()
            channels = 1 if "1" in channels_text else 2
            
            # 提取采样率（从"16000 Hz"格式中获取数字）
            sample_rate_text = self.audio_sample_rate_input.currentText()
            sample_rate = int(sample_rate_text.split()[0])
            
            # 更新非敏感配置
            self.config.update({
                # 音频提取设置
                "segment_duration": self.segment_duration_input.value(),
                "audio_format": self.audio_format_input.currentText(),
                "audio_bitrate": self.audio_bitrate_input.currentText(),
                "audio_channels": channels,
                "audio_sample_rate": sample_rate,
                "noise_reduction": self.noise_reduction_input.isChecked(),
                "normalize_volume": self.normalize_volume_input.isChecked(),
                
                # 转录设置
                "max_workers": self.max_workers_input.value(),
                "max_wait_time": self.max_wait_time_input.value()
            })
            
            # 更新敏感配置
            self.config.secrets.update({
                "api": {
                    "app_id": self.app_id_input.text(),
                    "access_token": self.access_token_input.text()
                },
                "tos": {
                    "ak": self.tos_ak_input.text(),
                    "sk": self.tos_sk_input.text(),
                    "endpoint": self.tos_endpoint_input.text(),
                    "region": self.tos_region_input.text(),
                    "bucket": self.tos_bucket_input.text()
                }
            })
            
            # 保存非敏感配置
            config_saved = self.config.save_config()
            # 保存敏感配置
            secrets_saved = self.config.save_secrets()
            
            if config_saved and secrets_saved:
                self.logger.info("配置已成功保存")
                # 发送配置更新信号
                self.config_updated.emit()
                QMessageBox.information(self, "保存成功", "设置已成功保存")
            else:
                self.logger.error("保存配置失败")
                QMessageBox.warning(self, "保存失败", "保存配置时发生错误")
        
        except Exception as e:
            self.logger.error(f"保存配置时出错: {e}")
            QMessageBox.critical(self, "保存错误", f"保存配置时出错:\n{e}")
    
    def confirm_reset(self):
        """确认是否重置设置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要恢复所有设置为默认值吗？\n这将覆盖当前的所有设置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.reset_settings()
    
    def reset_settings(self):
        """重置设置为默认值"""
        try:
            # 重置配置
            self.config.config = self.config.DEFAULT_CONFIG.copy()
            # 重置secrets为空
            self.config.secrets = {"api": {}, "tos": {}}
            
            # 重新加载UI
            self.load_settings()
            
            # 保存到文件
            config_saved = self.config.save_config()
            secrets_saved = self.config.save_secrets()
            
            if config_saved and secrets_saved:
                self.logger.info("已恢复默认设置")
                # 发送配置更新信号
                self.config_updated.emit()
                QMessageBox.information(self, "重置成功", "已恢复默认设置")
            else:
                self.logger.error("保存默认配置失败")
                QMessageBox.warning(self, "重置失败", "恢复默认设置时发生错误")
        
        except Exception as e:
            self.logger.error(f"重置设置时出错: {e}")
            QMessageBox.critical(self, "重置错误", f"重置设置时出错:\n{e}")