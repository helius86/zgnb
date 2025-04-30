#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批量转录选项卡
提供将音频文件批量转录为文本的界面
"""

import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
                             QProgressBar, QListWidget, QListWidgetItem, QMessageBox,
                             QSplitter, QCheckBox, QSpinBox, QDateTimeEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime

from utils.worker_thread import WorkerThread
from utils.log_handler import setup_logger
from utils.transcription_service import TranscriptionService
from utils.config_manager import SECRETS_FILE

class TranscriptionTab(QWidget):
    """批量转录选项卡，提供将音频文件批量转录为文本的界面"""
    
    # 定义信号
    log_message = pyqtSignal(str, int)  # 消息和日志级别
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None
        self.is_running = False
        self.file_urls = []  # 要转录的文件URL列表
        
        # 设置界面
        self.setup_ui()
        
        # 更新配置
        self.update_config(config)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # API配置区域
        api_group = QGroupBox("API配置")
        api_layout = QFormLayout()
        
        # APP ID
        self.app_id_input = QLineEdit()
        api_layout.addRow("APP ID:", self.app_id_input)
        
        # Access Token
        self.access_token_input = QLineEdit()
        api_layout.addRow("Access Token:", self.access_token_input)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # 文件URL列表
        url_group = QGroupBox("音频文件URL")
        url_layout = QVBoxLayout()
        
        # URL文本编辑框
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("请输入音频文件URL，每行一个\n例如：https://example.com/audio.mp3")
        url_layout.addWidget(self.url_input)
        
        # URL操作按钮
        url_btn_layout = QHBoxLayout()
        self.load_url_file_btn = QPushButton("从文件导入URL")
        self.load_url_file_btn.clicked.connect(self.load_url_from_file)
        self.clear_url_btn = QPushButton("清空URL")
        self.clear_url_btn.clicked.connect(self.clear_urls)
        self.parse_url_btn = QPushButton("解析URL列表")
        self.parse_url_btn.clicked.connect(self.parse_urls)
        url_btn_layout.addWidget(self.load_url_file_btn)
        url_btn_layout.addWidget(self.clear_url_btn)
        url_btn_layout.addWidget(self.parse_url_btn)
        url_layout.addLayout(url_btn_layout)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # 转录设置
        settings_group = QGroupBox("转录设置")
        settings_layout = QFormLayout()
        
        # 输出目录
        output_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("输出目录 (默认为当前目录下的transcripts)")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(browse_btn)
        settings_layout.addRow("输出目录:", output_layout)
        
        # 基准时间设置
        time_layout = QHBoxLayout()
        self.use_current_time = QCheckBox("使用当前时间")
        self.use_current_time.setChecked(True)
        self.start_time_input = QDateTimeEdit()
        self.start_time_input.setDateTime(QDateTime.currentDateTime())
        self.start_time_input.setEnabled(False)  # 默认禁用，因为默认使用当前时间
        self.use_current_time.toggled.connect(lambda checked: self.start_time_input.setEnabled(not checked))
        time_layout.addWidget(self.use_current_time)
        time_layout.addWidget(self.start_time_input)
        settings_layout.addRow("基准时间:", time_layout)
        
        # 并行处理设置
        self.max_workers_input = QSpinBox()
        self.max_workers_input.setRange(1, 5)
        self.max_workers_input.setValue(3)
        self.max_workers_input.setToolTip("同时处理的转录任务数量")
        settings_layout.addRow("并行任务数:", self.max_workers_input)
        
        # 高级选项
        advanced_layout = QHBoxLayout()
        self.auto_retry = QCheckBox("自动重试失败任务")
        self.auto_retry.setChecked(True)
        advanced_layout.addWidget(self.auto_retry)
        settings_layout.addRow("高级选项:", advanced_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始转录")
        self.start_btn.clicked.connect(self.start_transcription)
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
        
        # 创建分割器，上面是文件列表，下面是日志
        splitter = QSplitter(Qt.Vertical)
        
        # 文件列表显示
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout()
        self.file_list_widget = QListWidget()
        file_layout.addWidget(self.file_list_widget)
        file_group.setLayout(file_layout)
        splitter.addWidget(file_group)
        
        # 日志输出区域
        log_group = QGroupBox("转录日志")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        # 设置初始分割比例
        splitter.setSizes([200, 300])
        layout.addWidget(splitter, 1)  # 给分割器分配更多空间
        
        # 设置日志处理器
        self.logger = setup_logger(self.log_output, "TranscriptionTab")
    
    def update_config(self, config):
        """从配置更新UI控件"""
        # API配置
        self.app_id_input.setText(config.get_secret("api", "app_id", ""))
        self.access_token_input.setText(config.get_secret("api", "access_token", ""))
        
        # 转录设置
        self.max_workers_input.setValue(config.get("max_workers", 3))
        
        # 输出目录
        last_output = config.get("last_output_dir", "")
        if last_output and os.path.exists(last_output):
            self.output_dir_input.setText(last_output)
    
    def save_config(self):
        """保存当前设置到配置"""
        # 更新非敏感配置
        self.config.update({
            "max_workers": self.max_workers_input.value(),
            "last_output_dir": self.output_dir_input.text() if self.output_dir_input.text() else self.config.get("last_output_dir", "")
        })
        
        # 更新敏感配置
        if "api" not in self.config.secrets:
            self.config.secrets["api"] = {}
        
        self.config.secrets["api"].update({
            "app_id": self.app_id_input.text(),
            "access_token": self.access_token_input.text()
        })
        
        # 保存非敏感配置
        self.config.save_config()
        
        # 保存敏感配置
        self.config.save_secrets()
    
    def load_url_from_file(self):
        """从文本文件加载URL列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择URL列表文件",
            self.config.get("last_input_dir", ""),
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            if urls:
                # 先清空现有内容
                self.url_input.clear()
                # 添加新URL
                self.url_input.setPlainText("\n".join(urls))
                self.logger.info(f"从文件 {file_path} 加载了 {len(urls)} 个URL")
            else:
                self.logger.warning(f"文件 {file_path} 中未找到URL")
                QMessageBox.information(self, "未找到URL", f"文件 {file_path} 中未找到URL")
        
        except Exception as e:
            self.logger.error(f"加载URL文件失败: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"加载URL文件失败:\n{str(e)}")
    
    def clear_urls(self):
        """清空URL输入框"""
        if self.url_input.toPlainText().strip():
            reply = QMessageBox.question(
                self,
                "确认清空",
                "确定要清空URL列表吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.url_input.clear()
                self.file_list_widget.clear()
                self.file_urls = []
                self.logger.info("已清空URL列表")
    
    def parse_urls(self):
        """解析URL输入框中的URL列表"""
        url_text = self.url_input.toPlainText().strip()
        if not url_text:
            QMessageBox.warning(self, "URL为空", "请先输入音频文件URL")
            return
        
        # 分割和过滤URL
        urls = [line.strip() for line in url_text.split('\n') if line.strip()]
        
        # 过滤无效URL（必须以http://或https://开头）
        valid_urls = [url for url in urls if url.startswith(('http://', 'https://'))]
        invalid_count = len(urls) - len(valid_urls)
        
        if invalid_count > 0:
            self.logger.warning(f"忽略了 {invalid_count} 个无效URL")
        
        if not valid_urls:
            QMessageBox.warning(self, "无有效URL", "未找到有效的音频文件URL\n有效URL必须以http://或https://开头")
            return
        
        # 更新URL列表
        self.file_urls = valid_urls
        
        # 更新文件列表显示
        self.file_list_widget.clear()
        for url in valid_urls:
            # 从URL中提取文件名
            file_name = os.path.basename(url.split('?')[0])  # 移除查询参数
            item = QListWidgetItem(file_name)
            item.setToolTip(url)
            self.file_list_widget.addItem(item)
        
        self.logger.info(f"解析出 {len(valid_urls)} 个有效URL")
        QMessageBox.information(self, "解析完成", f"成功解析 {len(valid_urls)} 个有效URL\n已更新文件列表")
    
    def browse_output_dir(self):
        """浏览选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            self.output_dir_input.text() or self.config.get("last_output_dir", "")
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self.config.set("last_output_dir", dir_path)
    
    def start_transcription(self):
        """开始转录任务"""
        # 检查API配置
        if not self.app_id_input.text() or not self.access_token_input.text():
            QMessageBox.warning(self, "API配置不完整", "请输入APP ID和Access Token")
            return
        
        # 检查URL列表
        if not self.file_urls:
            # 尝试解析URL
            self.parse_urls()
            if not self.file_urls:
                return
        
        # 获取输出目录
        output_dir = self.output_dir_input.text().strip()
        if not output_dir:
            # 使用默认输出目录
            output_dir = os.path.join(os.getcwd(), "transcripts")
            self.output_dir_input.setText(output_dir)
        
        # 获取基准时间
        if self.use_current_time.isChecked():
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_time = self.start_time_input.dateTime().toString("yyyy-MM-dd hh:mm:ss")
        
        # 保存配置
        self.save_config()
        
        # 清空日志
        self.log_output.clear()
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setValue(0)
        self.is_running = True
        
        # 创建转录服务
        transcription_service = TranscriptionService(
            self.app_id_input.text(),
            self.access_token_input.text()
        )
        
        # 创建工作线程
        self.worker = WorkerThread(
            transcription_service.batch_transcribe,
            self.file_urls,
            output_dir,
            self.max_workers_input.value(),
            start_time
        )
        
        # 连接信号
        self.worker.progress_update.connect(self.update_progress)
        self.worker.task_finished.connect(self.on_task_finished)
        self.worker.log_message.connect(self.on_log_message)
        
        # 启动线程
        self.logger.info(f"开始批量转录 {len(self.file_urls)} 个音频文件")
        self.logger.info(f"输出目录: {output_dir}")
        self.logger.info(f"基准时间: {start_time}")
        self.worker.start()
    
    def cancel_task(self):
        """取消当前任务"""
        if self.worker and self.is_running:
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要取消转录吗？这将中断转录过程。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.logger.warning("用户取消了转录")
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
        """转录完成处理"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success and isinstance(result, dict):
            # 统计成功和失败的文件数
            files = result.get("files", [])
            success_count = sum(1 for f in files if f.get("status") == "success")
            fail_count = len(files) - success_count
            
            # 获取输出目录和汇总文件
            output_dir = result.get("output_dir", "")
            summary_file = result.get("summary_file", "")
            
            # 显示完成消息
            self.logger.info(f"转录完成，总计: {len(files)}，成功: {success_count}，失败: {fail_count}")
            if summary_file:
                self.logger.info(f"汇总文件: {summary_file}")
            
            completion_message = (
                f"批量转录已完成\n\n"
                f"总计: {len(files)} 个文件\n"
                f"成功: {success_count}\n"
                f"失败: {fail_count}\n\n"
                f"输出目录: {output_dir}"
            )
            
            if summary_file:
                completion_message += f"\n\n汇总文件: {summary_file}"
            
            QMessageBox.information(self, "转录完成", completion_message)
            
            # 在文件列表中更新状态
            for i, file_result in enumerate(files):
                status = file_result.get("status", "unknown")
                name = file_result.get("name", f"文件 {i+1}")
                
                # 查找对应的列表项
                for j in range(self.file_list_widget.count()):
                    item = self.file_list_widget.item(j)
                    if item.text() == name:
                        if status == "success":
                            item.setForeground(Qt.green)
                            item.setText(f"{name} ✓")
                        else:
                            item.setForeground(Qt.red)
                            item.setText(f"{name} ✗")
                        break
        else:
            error_msg = str(result) if result else "未知错误"
            self.logger.error(f"转录失败: {error_msg}")
            
            QMessageBox.critical(
                self,
                "转录失败",
                f"转录过程中发生错误:\n{error_msg}"
            )