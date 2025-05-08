#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工作线程模块
提供后台任务处理的线程类，用于长时间运行的操作
"""

import traceback
import logging
from PyQt5.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    """
    通用工作线程，用于在后台执行长时间运行的任务
    
    信号:
        progress_update (int, str): 进度更新信号 (百分比, 状态消息)
        task_finished (bool, object): 任务完成信号 (是否成功, 结果/错误消息)
        log_message (str, int): 日志消息信号 (消息文本, 日志级别)
    """
    progress_update = pyqtSignal(int, str)
    task_finished = pyqtSignal(bool, object)
    log_message = pyqtSignal(str, int)  # 消息和日志级别

    def __init__(self, task_func, *args, **kwargs):
        """
        初始化工作线程
        
        参数:
            task_func (callable): 要执行的任务函数
            *args, **kwargs: 传递给任务函数的参数
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.cancelled = False
        self.logger = logging.getLogger("WorkerThread")
        
        # 创建一个不直接写入UI的logger
        self._setup_thread_logger()

    def _setup_thread_logger(self):
        """设置线程安全的日志记录器"""
        # 这个logger不会直接写入UI，而是通过信号发送日志消息
        self.thread_logger = logging.getLogger(f"WorkerThread_{id(self)}")
        
        # 移除所有可能的处理器，确保不会直接写入UI
        for handler in self.thread_logger.handlers[:]:
            self.thread_logger.removeHandler(handler)
        
        # 添加自定义处理器，将日志消息转发为信号
        handler = logging.Handler()
        handler.emit = lambda record: self.log_message.emit(record.getMessage(), record.levelno)
        self.thread_logger.addHandler(handler)
        
        # 确保日志级别足够低，能捕获所有消息
        self.thread_logger.setLevel(logging.DEBUG)

    def run(self):
        """执行任务"""
        try:
            # 添加进度回调函数到kwargs
            self.kwargs['progress_callback'] = self.update_progress
            
            # 执行任务函数
            self.result = self.task_func(*self.args, **self.kwargs)
            
            # 如果任务未被取消，发出完成信号
            if not self.cancelled:
                self.task_finished.emit(True, self.result)
        except Exception as e:
            # 记录错误并发出失败信号
            error_msg = str(e)
            trace = traceback.format_exc()
            
            # 使用线程安全的方式记录日志
            self.thread_logger.exception("任务执行出错")
            self.log_message.emit(f"错误: {error_msg}", logging.ERROR)
            self.log_message.emit(f"详细错误信息: {trace}", logging.DEBUG)
            
            self.task_finished.emit(False, error_msg)

    def update_progress(self, progress, message=""):
        """
        更新进度信息
        
        参数:
            progress (int): 进度百分比 (0-100)
            message (str): 状态消息
        """
        if not self.cancelled:
            self.progress_update.emit(progress, message)
            
            # 如果消息不为空，也发送到日志
            if message:
                self.log_message.emit(message, logging.INFO)

    def cancel(self):
        """取消任务"""
        self.cancelled = True
        self.log_message.emit("任务已取消", logging.WARNING)
        # 不立即终止线程，让它自然结束，避免资源泄漏