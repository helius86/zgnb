#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频转录工具 - 主应用程序
集成音频提取、上传和转录功能的桌面应用程序
"""

import sys
import os
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, 
                             QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

# 导入自定义模块
from ui_components.extraction_tab import ExtractionTab
from ui_components.upload_tab import UploadTab
from ui_components.transcription_tab import TranscriptionTab
from ui_components.settings_tab import SettingsTab
from ui_components.split_audio_tab import SplitAudioTab  # 导入新的音频分割选项卡
from utils.config_manager import ConfigManager

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("audio_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AudioApp")

class MainWindow(QMainWindow):
    """主应用程序窗口"""
    def __init__(self):
        super().__init__()
        
        # 加载配置
        self.config = ConfigManager()
        
        # 设置窗口
        self.setup_ui()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("音频转录工具")
        self.setGeometry(100, 100, 1000, 700)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡部件
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # 添加各个功能选项卡
        self.extraction_tab = ExtractionTab(self.config)
        tab_widget.addTab(self.extraction_tab, "音频提取")
        
        # 添加新的音频分割选项卡
        self.split_audio_tab = SplitAudioTab(self.config)
        tab_widget.addTab(self.split_audio_tab, "音频分割")
        
        self.upload_tab = UploadTab(self.config)
        tab_widget.addTab(self.upload_tab, "TOS上传")
        
        self.transcription_tab = TranscriptionTab(self.config)
        tab_widget.addTab(self.transcription_tab, "批量转录")
        
        self.settings_tab = SettingsTab(self.config)
        tab_widget.addTab(self.settings_tab, "设置")
        
        # 底部状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号
        self.settings_tab.config_updated.connect(self.update_config)
        
        # 新增：连接上传选项卡和转录选项卡之间的信号
        self.upload_tab.send_to_transcription_signal.connect(self.handle_send_to_transcription)
        
        logger.info("应用程序界面初始化完成")
    
    def update_config(self):
        """更新所有选项卡的配置"""
        self.extraction_tab.update_config(self.config)
        self.split_audio_tab.update_config(self.config)  # 更新音频分割选项卡配置
        self.upload_tab.update_config(self.config)
        self.transcription_tab.update_config(self.config)
    
    def handle_send_to_transcription(self, urls):
        """处理从上传选项卡发送到转录选项卡的URL"""
        # 将URL传递给转录选项卡
        self.transcription_tab.load_uploaded_urls(urls)
        
        # 切换到转录选项卡
        current_widget = self.centralWidget()
        if current_widget:
            tab_widget = current_widget.findChild(QTabWidget)
            if tab_widget:
                # 查找转录选项卡的索引
                for i in range(tab_widget.count()):
                    if tab_widget.widget(i) == self.transcription_tab:
                        tab_widget.setCurrentIndex(i)
                        break
        
        logger.info(f"已将 {len(urls)} 个URL发送到转录选项卡")
        
    def closeEvent(self, event):
        """关闭窗口前确认是否有正在运行的任务"""
        active_tasks = []
        
        if self.extraction_tab.is_running:
            active_tasks.append("音频提取")
        if self.split_audio_tab.is_running:  # 检查音频分割任务
            active_tasks.append("音频分割")
        if self.upload_tab.is_running:
            active_tasks.append("TOS上传")
        if self.transcription_tab.is_running:
            active_tasks.append("批量转录")
            
        if active_tasks:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText(f"有任务正在运行: {', '.join(active_tasks)}")
            msg.setInformativeText("关闭应用程序将中断这些任务。确定要关闭吗？")
            msg.setWindowTitle("确认关闭")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            
            if msg.exec_() == QMessageBox.Yes:
                # 停止所有运行中的任务
                if self.extraction_tab.is_running:
                    self.extraction_tab.cancel_task()
                if self.split_audio_tab.is_running:  # 取消音频分割任务
                    self.split_audio_tab.cancel_task()
                if self.upload_tab.is_running:
                    self.upload_tab.cancel_task()
                if self.transcription_tab.is_running:
                    self.transcription_tab.cancel_task()
                    
                event.accept()
            else:
                event.ignore()
        else:
            # 保存配置
            self.config.save_config()
            event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()