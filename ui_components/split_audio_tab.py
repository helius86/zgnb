#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频分割选项卡
提供长音频文件分割功能
"""

import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
                             QProgressBar, QSpinBox, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal

from utils.worker_thread import WorkerThread
from utils.log_handler import setup_logger
from utils.audio_processor import AudioProcessor

class SplitAudioTab(QWidget):
    """音频分割选项卡，提供将长音频文件分割为多个片段的功能"""
    
    # 定义信号
    log_message = pyqtSignal(str, int)  # 消息和日志级别
    progress_update = pyqtSignal(int, str)  # 进度更新信号，提前声明
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None
        self.is_running = False
        
        # 设置界面
        self.setup_ui()
        
        # 更新配置
        self.update_config(config)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # 文件选择区域
        file_group = QGroupBox("音频文件")
        file_layout = QFormLayout()
        
        # 输入音频文件
        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("要分割的音频文件路径")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_audio_file)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(browse_btn)
        file_layout.addRow("输入音频:", input_layout)
        
        # 输出目录
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("输出目录 (默认为音频文件所在目录)")
        output_browse_btn = QPushButton("浏览...")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_browse_btn)
        file_layout.addRow("输出目录:", output_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 分割设置区域
        split_group = QGroupBox("分割设置")
        split_layout = QFormLayout()
        
        # 分段时长
        self.segment_duration = QSpinBox()
        self.segment_duration.setRange(1, 3600)  # 1秒到1小时
        self.segment_duration.setValue(3600)  # 默认1小时
        self.segment_duration.setSuffix(" 秒")
        split_layout.addRow("分段时长:", self.segment_duration)
        
        # 音频格式设置
        format_layout = QHBoxLayout()
        self.output_format = QLineEdit("mp3")
        self.output_format.setPlaceholderText("输出音频格式 (mp3, wav, ogg, flac)")
        format_layout.addWidget(self.output_format)
        split_layout.addRow("输出格式:", format_layout)
        
        # 输出文件名格式设置
        name_format_layout = QHBoxLayout()
        self.output_name_format = QLineEdit("{filename}_segment_{index}")
        self.output_name_format.setPlaceholderText("例如: {filename}_part_{index}")
        self.output_name_format.setToolTip("可用变量: {filename} - 原文件名, {index} - 分段序号, {start_time} - 开始时间(秒)")
        name_format_layout.addWidget(self.output_name_format)
        split_layout.addRow("输出文件名格式:", name_format_layout)
        
        split_group.setLayout(split_layout)
        layout.addWidget(split_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始分割")
        self.start_btn.clicked.connect(self.start_splitting)
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
        
        # 创建分割器，上面是分割信息，下面是日志
        splitter = QSplitter(Qt.Vertical)
        
        # 分割信息显示
        info_group = QGroupBox("分割信息")
        info_layout = QVBoxLayout()
        self.info_output = QTextEdit()
        self.info_output.setReadOnly(True)
        info_layout.addWidget(self.info_output)
        info_group.setLayout(info_layout)
        splitter.addWidget(info_group)
        
        # 日志输出区域
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        # 设置初始分割比例
        splitter.setSizes([200, 200])
        layout.addWidget(splitter, 1)  # 给分割器分配更多空间
        
        # 设置日志处理器
        self.logger = setup_logger(self.log_output, "SplitAudioTab")
        
        # 连接进度信号
        self.progress_update.connect(self.update_progress)
    
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
    
    def save_config(self):
        """保存当前设置到配置"""
        # 更新配置
        self.config.update({
            "last_input_dir": os.path.dirname(self.input_path.text()) if os.path.isfile(self.input_path.text()) else "",
            "last_output_dir": self.output_path.text(),
            "segment_duration": self.segment_duration.value()
        })
        
        # 保存到文件
        self.config.save_config()
    
    def browse_audio_file(self):
        """浏览选择音频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            self.input_path.text() or self.config.get("last_input_dir", ""),
            "音频文件 (*.mp3 *.wav *.ogg *.flac *.m4a);;所有文件 (*)"
        )
        
        if file_path:
            self.input_path.setText(file_path)
            # 自动设置输出目录为音频所在目录
            audio_dir = os.path.dirname(file_path)
            self.output_path.setText(audio_dir)
    
    def browse_output_dir(self):
        """浏览选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_path.text() or self.config.get("last_output_dir", "")
        )
        
        if dir_path:
            self.output_path.setText(dir_path)
    
    def start_splitting(self):
        """开始音频分割任务"""
        # 检查输入路径是否存在
        input_path = self.input_path.text().strip()
        if not input_path:
            QMessageBox.warning(self, "输入错误", "请指定要分割的音频文件")
            return
            
        if not os.path.exists(input_path):
            QMessageBox.warning(self, "路径错误", f"输入文件不存在: {input_path}")
            return
        
        # 获取输出目录
        output_dir = self.output_path.text().strip()
        if not output_dir:
            # 使用默认输出目录
            output_dir = os.path.dirname(input_path)
            self.output_path.setText(output_dir)
        
        # 检查分段时长
        segment_duration = self.segment_duration.value()
        if segment_duration <= 0:
            QMessageBox.warning(self, "参数错误", "分段时长必须大于0")
            return
        
        # 获取输出格式
        output_format = self.output_format.text().strip()
        if not output_format:
            output_format = "mp3"
            self.output_format.setText(output_format)
            
        # 获取文件名格式
        filename_format = self.output_name_format.text().strip()
        if not filename_format:
            filename_format = "{filename}_segment_{index}"
            self.output_name_format.setText(filename_format)
        
        # 创建音频处理器
        processor = AudioProcessor(
            segment_duration=segment_duration,
            output_dir=output_dir,
            audio_format=output_format
        )
        
        # 清空信息和日志
        self.info_output.clear()
        self.log_output.clear()
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.is_running = True
        
        # 保存配置
        self.save_config()
        
        # 创建工作线程
        self.worker = WorkerThread(self.split_audio_task, processor, input_path)
        
        # 连接信号
        self.worker.progress_update.connect(self.update_progress)
        self.worker.task_finished.connect(self.on_task_finished)
        self.worker.log_message.connect(self.on_log_message)
        
        # 启动线程
        self.logger.info(f"开始分割音频文件: {os.path.basename(input_path)}")
        self.worker.start()
    
    def split_audio_task(self, processor, input_path, progress_callback=None):
        """音频分割任务"""
        try:
            # 获取音频时长
            duration = processor.get_video_duration(input_path)
            if duration <= 0:
                raise ValueError("无法获取音频时长")
            
            # 计算可能的分段数
            segment_duration = processor.segment_duration
            segment_count = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
            
            # 更新进度
            if progress_callback:
                progress_callback(5, f"音频时长: {self.format_duration(duration)}, 将分割为 {segment_count} 个片段")
            
            # 生成分割信息文本
            info_text = f"<b>音频文件:</b> {os.path.basename(input_path)}<br>"
            info_text += f"<b>文件时长:</b> {self.format_duration(duration)}<br>"
            info_text += f"<b>分段时长:</b> {self.format_duration(segment_duration)}<br>"
            info_text += f"<b>分段数量:</b> {segment_count}<br>"
            info_text += f"<b>输出格式:</b> {processor.audio_format}<br>"
            info_text += f"<b>输出目录:</b> {processor.output_dir}<br>"
            
            # 显示文件名格式
            filename_format = self.output_name_format.text() or "{filename}_segment_{index}"
            info_text += f"<b>文件名格式:</b> {filename_format}<br><br>"
            
            # 描述最后一个片段的情况
            if duration % segment_duration > 0:
                last_segment_duration = duration % segment_duration
                info_text += f"<b>最后一个片段:</b> {self.format_duration(last_segment_duration)}<br><br>"
            
            # 使用信号更新UI
            if progress_callback:
                progress_callback(5, "准备分割音频文件")
            
            # 使用process_audio方法处理音频文件，传入文件名格式
            if hasattr(processor, 'process_audio'):
                result = processor.process_audio(input_path, progress_callback, filename_format)
                segments = result.get("segments", [])
            else:
                # 兼容旧版本，直接调用split_audio
                segments = processor.split_audio(input_path, progress_callback)
            
            # 返回结果以及信息文本用于更新UI
            return {
                "input_file": input_path,
                "output_dir": processor.output_dir,
                "duration": duration,
                "segment_count": segment_count,
                "segments": segments,
                "filename_format": filename_format,
                "info_text": info_text  # 包含要显示的信息
            }
        
        except Exception as e:
            # 使用工作线程的日志记录机制
            if progress_callback:
                progress_callback(0, f"错误: {str(e)}")
            raise
    
    def format_duration(self, seconds):
        """将秒数格式化为时:分:秒格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
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
            if isinstance(result, dict):
                input_file = os.path.basename(result.get("input_file", ""))
                output_dir = result.get("output_dir", "")
                segments = result.get("segments", [])
                info_text = result.get("info_text", "")
                
                # 更新信息输出 - 在主线程中安全地更新
                if info_text:
                    self.info_output.setHtml(info_text)
                
                # 添加成功信息
                self.info_output.append(f"<b>处理结果:</b> 成功<br>")
                self.info_output.append(f"<b>生成片段数:</b> {len(segments)}<br><br>")
                
                self.info_output.append("<b>生成的音频片段:</b><br>")
                for i, segment in enumerate(segments):
                    segment_name = os.path.basename(segment)
                    self.info_output.append(f"{i+1}. {segment_name}<br>")
                
                self.logger.info(f"分割完成，生成了 {len(segments)} 个音频片段")
                self.logger.info(f"输出目录: {output_dir}")
                
                # 显示完成消息框
                QMessageBox.information(
                    self,
                    "分割完成",
                    f"音频分割成功完成!\n生成了 {len(segments)} 个音频片段\n输出目录: {output_dir}"
                )
        else:
            # 显示错误消息
            error_msg = str(result) if result else "未知错误"
            self.logger.error(f"分割失败: {error_msg}")
            
            # 更新信息输出
            self.info_output.append(f"<b>处理结果:</b> <span style='color:red'>失败</span><br>")
            self.info_output.append(f"<b>错误信息:</b> <span style='color:red'>{error_msg}</span><br>")
            
            QMessageBox.critical(
                self,
                "分割失败",
                f"音频分割过程中发生错误:\n{error_msg}"
            )