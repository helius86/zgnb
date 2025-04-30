#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频提取选项卡
提供从视频中提取音频的界面
"""

import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
                             QProgressBar, QComboBox, QCheckBox, QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

from utils.worker_thread import WorkerThread
from utils.log_handler import setup_logger
from utils.audio_processor import AudioProcessor

class ExtractionTab(QWidget):
    """音频提取选项卡，提供从视频中提取音频的界面"""
    
    # 定义信号
    log_message = pyqtSignal(str, int)  # 消息和日志级别
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None
        self.is_running = False
        self.logger = logging.getLogger("ExtractionTab")
        
        # 设置界面
        self.setup_ui()
        
        # 更新配置
        self.update_config(config)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # 上部控制区域
        control_group = QGroupBox("音频提取设置")
        control_layout = QFormLayout()
        
        # 输入视频文件或目录
        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("视频文件路径或目录")
        browse_btn = QPushButton("浏览文件")
        browse_dir_btn = QPushButton("浏览目录")
        browse_btn.clicked.connect(self.browse_video_file)
        browse_dir_btn.clicked.connect(self.browse_video_dir)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(browse_btn)
        input_layout.addWidget(browse_dir_btn)
        control_layout.addRow("输入视频:", input_layout)
        
        # 输出目录
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("输出目录 (默认在视频目录下创建audio_output子目录)")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_browse_btn)
        control_layout.addRow("输出目录:", output_layout)
        
        # 分段设置
        self.segment_duration = QSpinBox()
        self.segment_duration.setRange(0, 7200)
        self.segment_duration.setValue(3600)
        self.segment_duration.setSuffix(" 秒")
        self.segment_duration.setToolTip("设置为0表示不分段")
        control_layout.addRow("分段时长:", self.segment_duration)
        
        # 音频格式设置
        format_layout = QHBoxLayout()
        self.audio_format = QComboBox()
        self.audio_format.addItems(["mp3", "wav", "ogg", "flac"])
        self.audio_bitrate = QComboBox()
        self.audio_bitrate.addItems(["64k", "128k", "192k", "256k", "320k"])
        self.audio_bitrate.setCurrentText("128k")
        format_layout.addWidget(self.audio_format)
        format_layout.addWidget(QLabel("比特率:"))
        format_layout.addWidget(self.audio_bitrate)
        control_layout.addRow("音频格式:", format_layout)
        
        # 音频处理选项
        options_layout = QHBoxLayout()
        self.audio_channels = QComboBox()
        self.audio_channels.addItems(["1 (单声道)", "2 (立体声)"])
        self.audio_sample_rate = QComboBox()
        self.audio_sample_rate.addItems(["8000 Hz", "16000 Hz", "22050 Hz", "44100 Hz", "48000 Hz"])
        self.audio_sample_rate.setCurrentText("16000 Hz")
        options_layout.addWidget(self.audio_channels)
        options_layout.addWidget(QLabel("采样率:"))
        options_layout.addWidget(self.audio_sample_rate)
        control_layout.addRow("音频通道:", options_layout)
        
        # 音频增强选项
        enhance_layout = QHBoxLayout()
        self.noise_reduction = QCheckBox("降噪")
        self.normalize_volume = QCheckBox("音量归一化")
        self.normalize_volume.setChecked(True)
        enhance_layout.addWidget(self.noise_reduction)
        enhance_layout.addWidget(self.normalize_volume)
        control_layout.addRow("音频增强:", enhance_layout)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始提取")
        self.start_btn.clicked.connect(self.start_extraction)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_task)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # 日志输出区域
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group, 1)  # 给日志区域分配更多空间
        
        # 设置日志处理器
        self.logger = setup_logger(self.log_output, "ExtractionTab")
        
    def update_config(self, config):
        """从配置更新UI控件"""
        # 设置上次使用的目录
        last_input = config.get("last_input_dir", "")
        if last_input and os.path.exists(last_input):
            self.input_path.setText(last_input)
            
        last_output = config.get("last_output_dir", "")
        if last_output and os.path.exists(last_output):
            self.output_path.setText(last_output)
            
        # 设置音频处理选项
        self.segment_duration.setValue(config.get("segment_duration", 3600))
        
        # 音频格式
        audio_format = config.get("audio_format", "mp3")
        index = self.audio_format.findText(audio_format)
        if index >= 0:
            self.audio_format.setCurrentIndex(index)
            
        # 比特率
        audio_bitrate = config.get("audio_bitrate", "128k")
        index = self.audio_bitrate.findText(audio_bitrate)
        if index >= 0:
            self.audio_bitrate.setCurrentIndex(index)
            
        # 音频通道
        audio_channels = config.get("audio_channels", 1)
        index = 0 if audio_channels == 1 else 1
        self.audio_channels.setCurrentIndex(index)
        
        # 采样率
        audio_sample_rate = str(config.get("audio_sample_rate", 16000)) + " Hz"
        index = self.audio_sample_rate.findText(audio_sample_rate)
        if index >= 0:
            self.audio_sample_rate.setCurrentIndex(index)
            
        # 音频增强
        self.noise_reduction.setChecked(config.get("noise_reduction", False))
        self.normalize_volume.setChecked(config.get("normalize_volume", True))
    
    def save_config(self):
        """保存当前设置到配置"""
        # 提取通道数（从"1 (单声道)"格式中获取数字）
        channels_text = self.audio_channels.currentText()
        channels = 1 if "1" in channels_text else 2
        
        # 提取采样率（从"16000 Hz"格式中获取数字）
        sample_rate_text = self.audio_sample_rate.currentText()
        sample_rate = int(sample_rate_text.split()[0])
        
        # 更新配置
        self.config.update({
            "last_input_dir": os.path.dirname(self.input_path.text()) if os.path.isfile(self.input_path.text()) else self.input_path.text(),
            "last_output_dir": self.output_path.text(),
            "segment_duration": self.segment_duration.value(),
            "audio_format": self.audio_format.currentText(),
            "audio_bitrate": self.audio_bitrate.currentText(),
            "audio_channels": channels,
            "audio_sample_rate": sample_rate,
            "noise_reduction": self.noise_reduction.isChecked(),
            "normalize_volume": self.normalize_volume.isChecked()
        })
        
        # 保存到文件
        self.config.save_config()
    
    def browse_video_file(self):
        """浏览选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            self.input_path.text() or self.config.get("last_input_dir", ""),
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v);;所有文件 (*)"
        )
        
        if file_path:
            self.input_path.setText(file_path)
            # 自动设置输出目录为视频所在目录下的audio_output子目录
            video_dir = os.path.dirname(file_path)
            self.output_path.setText(os.path.join(video_dir, "audio_output"))
    
    def browse_video_dir(self):
        """浏览选择视频目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择视频目录",
            self.input_path.text() or self.config.get("last_input_dir", "")
        )
        
        if dir_path:
            self.input_path.setText(dir_path)
            # 自动设置输出目录为选择目录下的audio_output子目录
            self.output_path.setText(os.path.join(dir_path, "audio_output"))
    
    def browse_output_dir(self):
        """浏览选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_path.text() or self.config.get("last_output_dir", "")
        )
        
        if dir_path:
            self.output_path.setText(dir_path)
    
    def start_extraction(self):
        """开始音频提取任务"""
        # 检查输入路径是否存在
        input_path = self.input_path.text().strip()
        if not input_path:
            QMessageBox.warning(self, "输入错误", "请指定视频文件或目录")
            return
            
        if not os.path.exists(input_path):
            QMessageBox.warning(self, "路径错误", f"输入路径不存在: {input_path}")
            return
        
        # 获取输出目录
        output_dir = self.output_path.text().strip()
        if not output_dir:
            # 使用默认输出目录
            if os.path.isfile(input_path):
                # 如果输入是文件，输出到文件所在目录下的audio_output
                output_dir = os.path.join(os.path.dirname(input_path), "audio_output")
            else:
                # 如果输入是目录，输出到该目录下的audio_output
                output_dir = os.path.join(input_path, "audio_output")
            
            self.output_path.setText(output_dir)
        
        # 提取音频通道数
        channels_text = self.audio_channels.currentText()
        channels = 1 if "1" in channels_text else 2
        
        # 提取采样率
        sample_rate_text = self.audio_sample_rate.currentText()
        sample_rate = int(sample_rate_text.split()[0])
        
        # 创建音频处理器
        processor = AudioProcessor(
            segment_duration=self.segment_duration.value(),
            output_dir=output_dir,
            audio_format=self.audio_format.currentText(),
            audio_bitrate=self.audio_bitrate.currentText(),
            audio_channels=channels,
            audio_sample_rate=sample_rate,
            noise_reduction=self.noise_reduction.isChecked(),
            normalize_volume=self.normalize_volume.isChecked()
        )
        
        # 清空日志
        self.log_output.clear()
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.is_running = True
        
        # 保存配置
        self.save_config()
        
        # 创建工作线程
        if os.path.isfile(input_path):
            # 处理单个文件
            self.worker = WorkerThread(processor.process_video, input_path)
            self.logger.info(f"开始处理视频文件: {os.path.basename(input_path)}")
        else:
            # 处理目录
            self.worker = WorkerThread(processor.process_directory, input_path)
            self.logger.info(f"开始处理视频目录: {input_path}")
        
        # 连接信号
        self.worker.progress_update.connect(self.update_progress)
        self.worker.task_finished.connect(self.on_task_finished)
        self.worker.log_message.connect(self.on_log_message)
        
        # 启动线程
        self.worker.start()
    
    def cancel_task(self):
        """取消当前任务"""
        if self.worker and self.is_running:
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要取消当前任务吗？这将中断处理过程。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.logger.warning("用户取消了任务")
                self.worker.cancel()
                self.is_running = False
                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
    
    def update_progress(self, value, message):
        """更新进度条和状态"""
        self.progress.setValue(value)
        if message:
            self.logger.info(message)
    
    def on_log_message(self, message, level):
        """处理来自工作线程的日志消息"""
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def on_task_finished(self, success, result):
        """任务完成处理"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            # 提取结果信息
            if isinstance(result, dict):  # 单个视频结果
                output_dir = result.get("output_dir", "")
                segments = result.get("segments", [])
                self.logger.info(f"提取完成，生成了 {len(segments)} 个音频片段")
                self.logger.info(f"输出目录: {output_dir}")
                
                # 显示完成消息框
                QMessageBox.information(
                    self,
                    "提取完成",
                    f"音频提取成功完成!\n生成了 {len(segments)} 个音频片段\n输出目录: {output_dir}"
                )
            elif isinstance(result, list):  # 目录处理结果
                total_videos = len(result)
                total_segments = sum(len(r.get("segments", [])) for r in result)
                output_dir = result[0].get("output_dir", "") if result else ""
                
                self.logger.info(f"批量提取完成，处理了 {total_videos} 个视频，生成了 {total_segments} 个音频片段")
                self.logger.info(f"输出目录: {output_dir}")
                
                # 显示完成消息框
                QMessageBox.information(
                    self,
                    "批量提取完成",
                    f"批量音频提取成功完成!\n处理了 {total_videos} 个视频\n生成了 {total_segments} 个音频片段\n输出目录: {output_dir}"
                )
        else:
            # 显示错误消息
            error_msg = str(result) if result else "未知错误"
            self.logger.error(f"提取失败: {error_msg}")
            
            QMessageBox.critical(
                self,
                "提取失败",
                f"音频提取过程中发生错误:\n{error_msg}"
            )