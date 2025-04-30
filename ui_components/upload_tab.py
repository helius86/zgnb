#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TOS上传选项卡
提供将音频文件上传到火山引擎对象存储的界面
"""

import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
                             QProgressBar, QListWidget, QListWidgetItem, QMessageBox,
                             QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QClipboard, QColor
import pyperclip

from utils.worker_thread import WorkerThread
from utils.log_handler import setup_logger
from utils.tos_uploader import TosUploader, HAS_TOS
from utils.config_manager import SECRETS_FILE

class UploadTab(QWidget):
    """TOS上传选项卡，提供将音频文件上传到火山引擎对象存储的界面"""
    
    # 定义信号
    log_message = pyqtSignal(str, int)  # 消息和日志级别
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.worker = None
        self.is_running = False
        self.file_list = []  # 待上传文件列表
        self.upload_results = {}  # 上传结果，文件路径到URL的映射
        
        # 设置界面
        self.setup_ui()
        
        # 更新配置
        self.update_config(config)
    
    def setup_ui(self):
        """设置用户界面"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # TOS配置区域
        tos_group = QGroupBox("TOS存储配置")
        tos_layout = QFormLayout()
        
        # Access Key
        self.ak_input = QLineEdit()
        self.ak_input.setEchoMode(QLineEdit.Password)  # 密码模式，不直接显示
        tos_layout.addRow("Access Key:", self.ak_input)
        
        # Secret Key
        self.sk_input = QLineEdit()
        self.sk_input.setEchoMode(QLineEdit.Password)
        tos_layout.addRow("Secret Key:", self.sk_input)
        
        # 端点
        self.endpoint_input = QLineEdit()
        tos_layout.addRow("端点 (Endpoint):", self.endpoint_input)
        
        # 区域
        self.region_input = QLineEdit()
        tos_layout.addRow("区域 (Region):", self.region_input)
        
        # 存储桶
        self.bucket_input = QLineEdit()
        tos_layout.addRow("存储桶 (Bucket):", self.bucket_input)
        
        # 测试连接按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        tos_layout.addRow("", self.test_btn)
        
        tos_group.setLayout(tos_layout)
        layout.addWidget(tos_group)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()
        
        # 文件列表
        self.file_list_widget = QListWidget()
        file_layout.addWidget(self.file_list_widget)
        
        # 文件操作按钮
        file_btn_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("添加文件")
        self.add_file_btn.clicked.connect(self.add_files)
        self.add_dir_btn = QPushButton("添加目录")
        self.add_dir_btn.clicked.connect(self.add_directory)
        self.remove_btn = QPushButton("移除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_list)
        file_btn_layout.addWidget(self.add_file_btn)
        file_btn_layout.addWidget(self.add_dir_btn)
        file_btn_layout.addWidget(self.remove_btn)
        file_btn_layout.addWidget(self.clear_btn)
        file_layout.addLayout(file_btn_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始上传")
        self.start_btn.clicked.connect(self.start_upload)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.cancel_task)
        self.cancel_btn.setEnabled(False)
        self.copy_urls_btn = QPushButton("复制所有URL")
        self.copy_urls_btn.clicked.connect(self.copy_urls)
        self.copy_urls_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.copy_urls_btn)
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # 创建分割器，上面是结果显示，下面是日志
        splitter = QSplitter(Qt.Vertical)
        
        # 上传结果显示区域
        result_group = QGroupBox("上传结果")
        result_layout = QVBoxLayout()
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        result_layout.addWidget(self.result_output)
        result_group.setLayout(result_layout)
        splitter.addWidget(result_group)
        
        # 日志输出区域
        log_group = QGroupBox("上传日志")
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
        self.logger = setup_logger(self.log_output, "UploadTab")
        
        # 检查TOS SDK是否可用
        if not HAS_TOS:
            self.logger.error("未安装TOS SDK，上传功能将不可用")
            self.test_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            QMessageBox.warning(
                self,
                "功能不可用",
                "未安装TOS SDK，上传功能不可用。\n请安装tos库: pip install tos"
            )
    
    def update_config(self, config):
        """从配置更新UI控件"""
        self.ak_input.setText(config.get_secret("tos", "ak", ""))
        self.sk_input.setText(config.get_secret("tos", "sk", ""))
        self.endpoint_input.setText(config.get_secret("tos", "endpoint", ""))
        self.region_input.setText(config.get_secret("tos", "region", ""))
        self.bucket_input.setText(config.get_secret("tos", "bucket", ""))
    
    def save_config(self):
        """保存当前设置到配置"""
        # 更新敏感信息
        if "tos" not in self.config.secrets:
            self.config.secrets["tos"] = {}
            
        self.config.secrets["tos"].update({
            "ak": self.ak_input.text(),
            "sk": self.sk_input.text(),
            "endpoint": self.endpoint_input.text(),
            "region": self.region_input.text(),
            "bucket": self.bucket_input.text()
        })
        
        # 保存敏感配置
        self.config.save_secrets()
    
    def test_connection(self):
        """测试TOS连接"""
        # 检查必填字段
        if not all([
            self.ak_input.text(),
            self.sk_input.text(),
            self.endpoint_input.text(),
            self.region_input.text(),
            self.bucket_input.text()
        ]):
            QMessageBox.warning(self, "参数不完整", "请填写所有TOS配置参数")
            return
        
        if not HAS_TOS:
            QMessageBox.warning(self, "功能不可用", "未安装TOS SDK，无法测试连接")
            return
        
        # 禁用按钮
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        
        # 创建上传器并测试连接
        uploader = TosUploader(
            self.ak_input.text(),
            self.sk_input.text(),
            self.endpoint_input.text(),
            self.region_input.text(),
            self.bucket_input.text()
        )
        
        # 创建工作线程
        def test_tos_connection():
            try:
                # 列出存储桶对象，测试连接
                result = uploader.client.list_objects(uploader.bucket, max_keys=1)
                return True, "连接成功"
            except Exception as e:
                return False, str(e)
                
        self.worker = WorkerThread(test_tos_connection)
        
        # 连接信号
        self.worker.task_finished.connect(self.on_test_finished)
        
        # 启动线程
        self.worker.start()
    
    def on_test_finished(self, success, result):
        """测试连接完成处理"""
        # 恢复按钮
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        
        if success:
            self.logger.info("TOS连接测试成功")
            QMessageBox.information(self, "连接成功", "成功连接到TOS存储")
            # 保存配置
            self.save_config()
        else:
            error_msg = str(result) if result else "未知错误"
            self.logger.error(f"TOS连接测试失败: {error_msg}")
            QMessageBox.critical(self, "连接失败", f"连接TOS存储失败:\n{error_msg}")
    
    def add_files(self):
        """添加文件到上传列表"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            self.config.get("last_input_dir", ""),
            "音频文件 (*.mp3 *.wav *.ogg *.flac);;所有文件 (*)"
        )
        
        if file_paths:
            # 更新最后使用的目录
            last_dir = os.path.dirname(file_paths[0])
            self.config.set("last_input_dir", last_dir)
            
            # 添加文件到列表
            for file_path in file_paths:
                if file_path not in self.file_list:
                    self.file_list.append(file_path)
                    item = QListWidgetItem(os.path.basename(file_path))
                    item.setToolTip(file_path)
                    self.file_list_widget.addItem(item)
            
            self.logger.info(f"添加了 {len(file_paths)} 个文件到上传列表")
    
    def add_directory(self):
        """添加目录中的音频文件到上传列表"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择包含音频文件的目录",
            self.config.get("last_input_dir", "")
        )
        
        if dir_path:
            # 更新最后使用的目录
            self.config.set("last_input_dir", dir_path)
            
            # 查找所有音频文件
            audio_extensions = ['.mp3', '.wav', '.ogg', '.flac']
            file_count = 0
            
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in audio_extensions:
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_list:
                            self.file_list.append(file_path)
                            item = QListWidgetItem(os.path.basename(file_path))
                            item.setToolTip(file_path)
                            self.file_list_widget.addItem(item)
                            file_count += 1
            
            if file_count > 0:
                self.logger.info(f"从目录 {dir_path} 添加了 {file_count} 个音频文件")
            else:
                self.logger.warning(f"目录 {dir_path} 中未找到音频文件")
                QMessageBox.information(self, "未找到文件", f"在目录 {dir_path} 中未找到音频文件")
    
    def remove_selected(self):
        """移除选中的文件"""
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.file_list_widget.row(item)
            file_path = self.file_list[row]
            self.file_list.pop(row)
            self.file_list_widget.takeItem(row)
        
        self.logger.info(f"移除了 {len(selected_items)} 个文件")
    
    def clear_list(self):
        """清空文件列表"""
        if self.file_list_widget.count() > 0:
            reply = QMessageBox.question(
                self,
                "确认清空",
                "确定要清空文件列表吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.file_list_widget.clear()
                self.file_list.clear()
                self.logger.info("已清空文件列表")
    
    def start_upload(self):
        """开始上传文件"""
        # 检查文件列表
        if not self.file_list:
            QMessageBox.warning(self, "文件列表为空", "请先添加要上传的文件")
            return
        
        # 检查TOS配置
        if not all([
            self.ak_input.text(),
            self.sk_input.text(),
            self.endpoint_input.text(),
            self.region_input.text(),
            self.bucket_input.text()
        ]):
            QMessageBox.warning(self, "参数不完整", "请填写所有TOS配置参数")
            return
        
        # 检查TOS SDK
        if not HAS_TOS:
            QMessageBox.warning(self, "功能不可用", "未安装TOS SDK，无法上传文件")
            return
        
        # 保存配置
        self.save_config()
        
        # 清空结果
        self.result_output.clear()
        self.upload_results = {}
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.copy_urls_btn.setEnabled(False)
        self.progress.setValue(0)
        self.is_running = True
        
        # 创建上传器
        uploader = TosUploader(
            self.ak_input.text(),
            self.sk_input.text(),
            self.endpoint_input.text(),
            self.region_input.text(),
            self.bucket_input.text()
        )
        
        # 创建工作线程
        self.worker = WorkerThread(uploader.batch_upload, self.file_list.copy())
        
        # 连接信号
        self.worker.progress_update.connect(self.update_progress)
        self.worker.task_finished.connect(self.on_upload_finished)
        self.worker.log_message.connect(self.on_log_message)
        
        # 启动线程
        self.logger.info(f"开始上传 {len(self.file_list)} 个文件")
        self.worker.start()
    
    def cancel_task(self):
        """取消当前任务"""
        if self.worker and self.is_running:
            reply = QMessageBox.question(
                self,
                "确认取消",
                "确定要取消上传吗？这将中断上传过程。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.logger.warning("用户取消了上传")
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
    
    def on_upload_finished(self, success, result):
        """上传完成处理"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success and isinstance(result, dict):
            self.upload_results = result
            
            # 显示上传结果
            success_count = sum(1 for url in result.values() if url)
            fail_count = len(result) - success_count
            
            self.result_output.clear()
            self.result_output.append(f"<h3>上传结果</h3>")
            self.result_output.append(f"<p>总文件数: {len(result)}, 成功: {success_count}, 失败: {fail_count}</p>")
            self.result_output.append("<hr>")
            
            # 按文件名排序
            sorted_items = sorted(result.items(), key=lambda x: os.path.basename(x[0]))
            
            for file_path, url in sorted_items:
                file_name = os.path.basename(file_path)
                if url:
                    self.result_output.append(f"<p><b>{file_name}</b>: <span style='color:green'>上传成功</span></p>")
                    self.result_output.append(f"<p>URL: <a href='{url}'>{url}</a></p>")
                else:
                    self.result_output.append(f"<p><b>{file_name}</b>: <span style='color:red'>上传失败</span></p>")
                self.result_output.append("<hr>")
            
            # 启用复制URL按钮
            if success_count > 0:
                self.copy_urls_btn.setEnabled(True)
            
            # 显示完成消息
            self.logger.info(f"上传完成，总计: {len(result)}，成功: {success_count}，失败: {fail_count}")
            
            QMessageBox.information(
                self,
                "上传完成",
                f"文件上传已完成\n总计: {len(result)} 个文件\n成功: {success_count}\n失败: {fail_count}"
            )
        else:
            error_msg = str(result) if result else "未知错误"
            self.logger.error(f"上传失败: {error_msg}")
            
            QMessageBox.critical(
                self,
                "上传失败",
                f"上传过程中发生错误:\n{error_msg}"
            )
    
    def copy_urls(self):
        """复制所有成功上传的URL到剪贴板"""
        if not self.upload_results:
            return
        
        # 提取成功上传的URL
        urls = [url for url in self.upload_results.values() if url]
        
        if not urls:
            QMessageBox.information(self, "没有可复制的URL", "没有成功上传的文件URL")
            return
        
        # 组合URL文本
        url_text = "\n".join(urls)
        
        # 复制到剪贴板
        try:
            pyperclip.copy(url_text)
            self.logger.info(f"已复制 {len(urls)} 个URL到剪贴板")
            QMessageBox.information(self, "复制成功", f"已复制 {len(urls)} 个URL到剪贴板")
        except Exception as e:
            self.logger.error(f"复制URL失败: {e}")
            QMessageBox.warning(self, "复制失败", f"复制URL到剪贴板失败: {e}")