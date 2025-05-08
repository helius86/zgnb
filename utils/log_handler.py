#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志处理器模块
提供将日志显示到QTextEdit控件的处理器
"""

import logging
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtCore import Qt, QObject, pyqtSlot, pyqtSignal

class ThreadSafeLogHandler(QObject, logging.Handler):
    """线程安全的日志处理器，通过信号机制更新UI"""
    
    log_signal = pyqtSignal(str, QColor)
    
    def __init__(self, text_widget):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 设置不同日志级别的颜色
        self.level_colors = {
            logging.DEBUG: QColor(100, 100, 100),     # 灰色
            logging.INFO: QColor(0, 0, 0),            # 黑色
            logging.WARNING: QColor(200, 150, 0),     # 黄色
            logging.ERROR: QColor(200, 0, 0),         # 红色
            logging.CRITICAL: QColor(255, 0, 0)       # 亮红色
        }
        
        # 连接信号到槽函数
        self.log_signal.connect(self.append_log)

    def emit(self, record):
        """
        发送日志记录
        
        参数:
            record (LogRecord): 日志记录
        """
        try:
            msg = self.formatter.format(record)
            text_color = self.level_colors.get(record.levelno, QColor(0, 0, 0))
            
            # 通过信号发送消息，确保在主线程中处理
            self.log_signal.emit(msg, text_color)
            
        except Exception as e:
            # 如果出现错误，直接输出到控制台
            print(f"日志处理错误: {e}")
            print(record.getMessage())
    
    @pyqtSlot(str, QColor)
    def append_log(self, msg, color):
        """
        在主线程中追加日志消息
        
        参数:
            msg (str): 格式化的日志消息
            color (QColor): 文本颜色
        """
        try:
            # 保存当前光标位置和选择
            cursor = self.text_widget.textCursor()
            cursor_position = cursor.position()
            cursor_anchor = cursor.anchor()
            
            # 移动到文档末尾
            cursor.movePosition(QTextCursor.End)
            
            # 设置文本颜色
            cursor.insertHtml(f'<span style="color:{color.name()}">{msg}</span><br>')
            
            # 如果之前没有选择，恢复光标位置；否则保持在末尾
            if cursor_position == cursor_anchor:
                cursor.setPosition(cursor_position)
                self.text_widget.setTextCursor(cursor)
            
            # 滚动到底部
            self.text_widget.ensureCursorVisible()
            
        except Exception as e:
            # 如果格式化或输出失败，使用简单的方式添加文本
            print(f"UI日志更新错误: {e}")
            try:
                self.text_widget.append(f"日志处理错误: {e}")
                self.text_widget.append(msg)
            except:
                pass

class QTextEditLogger(logging.Handler):
    """将日志消息发送到QTextEdit控件的处理器（传统方式，不推荐在多线程环境中使用）"""
    
    def __init__(self, text_widget):
        """
        初始化日志处理器
        
        参数:
            text_widget (QTextEdit): 用于显示日志的文本编辑器控件
        """
        super().__init__()
        self.text_widget = text_widget
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 设置不同日志级别的颜色
        self.level_colors = {
            logging.DEBUG: QColor(100, 100, 100),     # 灰色
            logging.INFO: QColor(0, 0, 0),            # 黑色
            logging.WARNING: QColor(200, 150, 0),     # 黄色
            logging.ERROR: QColor(200, 0, 0),         # 红色
            logging.CRITICAL: QColor(255, 0, 0)       # 亮红色
        }

    def emit(self, record):
        """
        发送日志记录到文本编辑器
        
        参数:
            record (LogRecord): 日志记录
        """
        try:
            msg = self.formatter.format(record)
            
            # 保存当前光标位置和选择
            cursor = self.text_widget.textCursor()
            cursor_position = cursor.position()
            cursor_anchor = cursor.anchor()
            
            # 移动到文档末尾
            cursor.movePosition(QTextCursor.End)
            
            # 设置文本颜色
            text_color = self.level_colors.get(record.levelno, QColor(0, 0, 0))
            cursor.insertHtml(f'<span style="color:{text_color.name()}">{msg}</span><br>')
            
            # 如果之前没有选择，恢复光标位置；否则保持在末尾
            if cursor_position == cursor_anchor:
                cursor.setPosition(cursor_position)
                self.text_widget.setTextCursor(cursor)
            
            # 滚动到底部
            self.text_widget.ensureCursorVisible()
            
        except Exception as e:
            # 如果格式化或输出失败，使用简单的方式添加文本
            self.text_widget.append(f"日志处理错误: {e}")
            self.text_widget.append(record.getMessage())

def setup_logger(text_widget, logger_name=None, level=logging.INFO):
    """
    设置日志器并添加到文本编辑器
    
    参数:
        text_widget (QTextEdit): 用于显示日志的文本编辑器控件
        logger_name (str): 日志器名称，如果为None则使用根日志器
        level (int): 日志级别
        
    返回:
        logger: 配置好的日志器
    """
    # 获取日志器
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    
    # 创建并添加线程安全的处理器
    handler = ThreadSafeLogHandler(text_widget)
    handler.setLevel(level)
    logger.addHandler(handler)
    
    # 确保日志器级别足够低，以便处理器能接收到消息
    if logger.level > level:
        logger.setLevel(level)
    
    return logger