#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
转录服务模块
提供音频文件转录为文本的功能
"""

import os
import time
import json
import uuid
import requests
import logging
from datetime import datetime
import traceback

class TranscriptionService:
    """音频文件转录服务，使用火山引擎API"""
    
    def __init__(self, app_id, access_token):
        """
        初始化转录服务
        
        参数:
            app_id (str): 火山引擎APP ID
            access_token (str): 火山引擎Access Token
        """
        self.app_id = app_id
        self.access_token = access_token
        self.logger = logging.getLogger("TranscriptionService")
        
        # API相关常量
        self.SUBMIT_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
        self.QUERY_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"
        self.RESOURCE_ID = "volc.bigasr.auc"
        
    def _get_headers(self, request_id=None):
        """
        获取API请求头
        
        参数:
            request_id (str, optional): 请求ID，不指定时自动生成
            
        返回:
            tuple: (headers, request_id)
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.RESOURCE_ID,
            "X-Api-Request-Id": request_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json"
        }
        return headers, request_id
        
    def submit_task(self, file_url, audio_format=None):
        """
        提交转录任务
        
        参数:
            file_url (str): 音频文件URL
            audio_format (str, optional): 音频格式，不指定时自动从URL推断
            
        返回:
            tuple: (task_id, x_tt_logid) 或失败时返回 (None, None)
        """
        headers, request_id = self._get_headers()
        
        # 如果未指定音频格式，从URL中推断
        if audio_format is None:
            file_ext = os.path.splitext(file_url)[1].lower().lstrip('.')
            # 检查扩展名是否为已知格式
            if file_ext in ['mp3', 'wav', 'ogg', 'flac', 'pcm']:
                audio_format = file_ext
            else:
                # 默认为mp3
                audio_format = 'mp3'
        
        data = {
            "user": {
                "uid": str(uuid.uuid4().int)
            },
            "audio": {
                "url": file_url,
                "format": audio_format
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,  # 启用文本规范化
                "enable_punc": True,  # 启用标点
                "enable_speaker_info": True,  # 启用说话人信息
                "show_utterances": True  # 启用分句信息
            }
        }
        
        try:
            self.logger.debug(f"提交任务请求: URL={file_url}, headers={headers}")
            response = requests.post(self.SUBMIT_URL, headers=headers, json=data, timeout=30)
            x_tt_logid = response.headers.get("X-Tt-Logid", "")
            status_code = response.headers.get("X-Api-Status-Code", "")
            message = response.headers.get("X-Api-Message", "")
            
            self.logger.debug(f"提交任务响应: status_code={status_code}, message={message}, x_tt_logid={x_tt_logid}")
            
            if status_code != "20000000":
                self.logger.error(f"任务提交失败: {status_code}, {message}")
                return None, None
                
            return request_id, x_tt_logid
            
        except requests.Timeout:
            self.logger.error("提交任务超时")
            return None, None
        except requests.ConnectionError:
            self.logger.error("提交任务连接错误")
            return None, None
        except Exception as e:
            self.logger.error(f"提交任务异常: {e}")
            self.logger.debug(traceback.format_exc())
            return None, None
            
    def query_task(self, task_id, x_tt_logid):
        """
        查询转录任务状态和结果
        
        参数:
            task_id (str): 任务ID
            x_tt_logid (str): 日志ID
            
        返回:
            tuple: (response, status_code)
        """
        headers = {
            "X-Api-App-Key": self.app_id,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.RESOURCE_ID,
            "X-Api-Request-Id": task_id,
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.debug(f"查询任务请求: task_id={task_id}, x_tt_logid={x_tt_logid}")
            response = requests.post(self.QUERY_URL, headers=headers, json={}, timeout=30)
            status_code = response.headers.get("X-Api-Status-Code", "")
            message = response.headers.get("X-Api-Message", "")
            
            self.logger.debug(f"查询任务响应: status_code={status_code}, message={message}")
            
            return response, status_code
            
        except requests.Timeout:
            self.logger.error("查询任务超时")
            return None, "超时"
        except requests.ConnectionError:
            self.logger.error("查询任务连接错误")
            return None, "连接错误"
        except Exception as e:
            self.logger.error(f"查询任务异常: {e}")
            self.logger.debug(traceback.format_exc())
            return None, f"异常: {str(e)}"
    
    def transcribe_audio(self, file_url, max_wait_time=1800, wait_interval=5, max_retries=3, progress_callback=None):
        """
        转录单个音频文件
        
        参数:
            file_url (str): 音频文件URL
            max_wait_time (int): 最大等待时间(秒)
            wait_interval (int): 查询间隔时间(秒)
            max_retries (int): 提交任务最大重试次数
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            dict: 转录结果，失败返回None
        """
        self.logger.info(f"开始转录音频: {file_url}")
        
        if progress_callback:
            progress_callback(0, "准备提交转录任务")
        
        # 提交任务，添加重试机制
        retry_count = 0
        task_id = None
        tt_logid = None
        
        while retry_count < max_retries and not task_id:
            # 每次尝试间增加短暂延迟
            if retry_count > 0:
                retry_delay = 2 ** retry_count  # 指数退避策略
                self.logger.info(f"第 {retry_count} 次重试，等待 {retry_delay} 秒...")
                if progress_callback:
                    progress_callback(0, f"提交任务失败，第 {retry_count} 次重试...")
                time.sleep(retry_delay)
                
            task_id, tt_logid = self.submit_task(file_url)
            if task_id:
                self.logger.info(f"任务已提交，ID: {task_id}")
                if progress_callback:
                    progress_callback(5, f"任务已提交，正在等待处理")
                break
                
            retry_count += 1
            self.logger.warning(f"提交失败，尝试重试 ({retry_count}/{max_retries})")
        
        # 所有重试均失败
        if not task_id:
            self.logger.error("所有重试均失败，无法提交任务")
            if progress_callback:
                progress_callback(100, "错误: 无法提交转录任务")
            return None
        
        # 等待并查询结果
        start_time = time.time()
        query_retry_count = 0
        max_query_retries = 3
        result = None
        
        # 计算查询次数以更新进度
        expected_queries = max_wait_time // wait_interval
        query_count = 0
        
        while time.time() - start_time < max_wait_time:
            try:
                query_count += 1
                
                # 更新进度，任务提交占5%，查询和处理占90%，最终处理占5%
                if progress_callback:
                    # 进度从5%到95%
                    progress = min(95, 5 + int(90 * query_count / expected_queries))
                    elapsed_time = int(time.time() - start_time)
                    progress_callback(progress, f"正在处理转录，已等待 {elapsed_time} 秒")
                
                # 查询任务状态
                response, status_code = self.query_task(task_id, tt_logid)
                
                # 重置查询重试计数
                query_retry_count = 0
                
                # 检查任务状态
                if status_code == '20000000':  # 任务完成
                    result = response.json()
                    self.logger.info(f"转录完成")
                    
                    # 记录音频时长
                    if 'audio_info' in result and 'duration' in result['audio_info']:
                        duration_ms = result['audio_info']['duration']
                        self.logger.info(f"音频时长: {duration_ms / 1000:.2f}秒")
                    
                    if progress_callback:
                        progress_callback(95, "转录完成，正在处理结果")
                    
                    break
                        
                elif status_code in ['20000001', '20000002']:  # 任务处理中或排队中
                    self.logger.debug(f"任务处理中，状态码: {status_code}")
                else:  # 任务失败
                    status_message = f"失败({status_code})"
                    self.logger.error(f"转录失败! 状态码: {status_code}")
                    
                    if progress_callback:
                        progress_callback(100, f"错误: 转录失败，状态码: {status_code}")
                    
                    return None
            
            except Exception as e:
                query_retry_count += 1
                self.logger.warning(f"查询状态发生异常: {e}, 重试 ({query_retry_count}/{max_query_retries})")
                
                if query_retry_count >= max_query_retries:
                    self.logger.error(f"查询重试次数过多，放弃处理")
                    
                    if progress_callback:
                        progress_callback(100, "错误: 查询任务状态失败")
                    
                    return None
            
            # 等待指定时间后继续查询
            time.sleep(wait_interval)
        
        # 超时或有结果
        if not result:  # 超时
            self.logger.warning(f"转录超时，超过 {max_wait_time} 秒")
            
            if progress_callback:
                progress_callback(100, f"错误: 转录超时，超过 {max_wait_time} 秒")
            
            return None
        
        # 处理并保存结果
        if progress_callback:
            progress_callback(100, "转录完成")
        
        return result
    
    def save_transcript(self, result, output_path=None, include_timestamps=True):
        """
        保存转录结果
        
        参数:
            result (dict): 转录结果
            output_path (str, optional): 输出文件路径，不指定时使用时间戳生成
            include_timestamps (bool): 是否包含时间戳
            
        返回:
            tuple: (json_path, text_path) 保存的文件路径
        """
        if not result:
            self.logger.error("没有可保存的结果")
            return None, None
        
        # 如果未指定输出文件名，使用时间戳生成一个
        if not output_path:
            timestamp = int(time.time())
            output_path = f"transcript_{timestamp}"
        
        # 去除扩展名
        output_base = os.path.splitext(output_path)[0]
        
        # 保存JSON文件
        json_file = f"{output_base}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"JSON结果已保存至: {json_file}")
        
        # 保存文本文件
        text_file = f"{output_base}.txt"
        
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                # 添加标题和时间
                f.write(f"# 语音识别结果\n\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                if include_timestamps and 'result' in result and 'utterances' in result['result']:
                    utterances = result['result']['utterances']
                    
                    f.write("## 带时间戳的文本\n\n")
                    for utterance in utterances:
                        start_ms = utterance.get('start_time', 0)
                        end_ms = utterance.get('end_time', 0)
                        
                        # 转换为秒，并格式化
                        start_sec = start_ms / 1000
                        end_sec = end_ms / 1000
                        
                        start_time = self._format_time(start_sec)
                        end_time = self._format_time(end_sec)
                        
                        # 写入时间戳和文本
                        f.write(f"[{start_time} --> {end_time}] {utterance.get('text', '')}\n")
                    
                    f.write("\n")
                
                # 写入完整文本
                if 'result' in result and 'text' in result['result']:
                    f.write("## 完整文本\n\n")
                    f.write(result['result']['text'])
                else:
                    f.write("## 未找到完整文本\n")
            
            self.logger.info(f"文本结果已保存至: {text_file}")
            
        except Exception as e:
            self.logger.error(f"保存文本结果失败: {e}")
            text_file = None
        
        return json_file, text_file
    
    def _format_time(self, seconds):
        """将秒数格式化为时:分:秒格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def batch_transcribe(self, file_urls, output_dir=None, max_workers=3, start_time=None, progress_callback=None):
        """
        批量转录音频文件
        
        参数:
            file_urls (list): 音频文件URL列表
            output_dir (str, optional): 输出目录，不指定时在当前目录创建
            max_workers (int): 并行处理的工作线程数
            start_time (str, optional): 基准时间，用于计算绝对时间戳
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            dict: 批量转录结果
        """
        if not file_urls:
            self.logger.error("没有要处理的文件URL")
            return {"status": "error", "message": "没有要处理的文件URL"}
        
        # 如果未指定输出目录，使用默认目录
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "transcripts")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 如果未指定开始时间，使用当前时间
        if start_time is None:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建结果结构
        result = {
            "status": "success",
            "start_time": start_time,
            "files": [],
            "output_dir": output_dir
        }
        
        # 按顺序处理每个文件
        total_files = len(file_urls)
        
        # 处理进度的分块：每个文件的分量
        file_weight = 100 / total_files
        
        for i, file_url in enumerate(file_urls):
            file_name = os.path.basename(file_url)
            self.logger.info(f"处理文件 {i+1}/{total_files}: {file_name}")
            
            # 初始化文件结果
            file_result = {
                "url": file_url,
                "name": file_name,
                "status": "pending",
                "output_files": {"json": None, "text": None}
            }
            
            # 更新总体进度
            if progress_callback:
                progress_callback(int(i * file_weight), f"开始处理 {i+1}/{total_files}: {file_name}")
            
            # 文件进度回调
            def file_progress(percent, message):
                if progress_callback:
                    # 计算总体进度：当前文件的进度 * 文件权重 + 已完成文件的总权重
                    overall_progress = int(i * file_weight + percent * file_weight / 100)
                    progress_callback(overall_progress, f"[{i+1}/{total_files}] {message}")
            
            # 转录音频
            try:
                transcript = self.transcribe_audio(file_url, progress_callback=file_progress)
                
                if transcript:
                    file_result["status"] = "success"
                    
                    # 保存转录结果
                    output_base = os.path.join(output_dir, os.path.splitext(file_name)[0])
                    json_path, text_path = self.save_transcript(transcript, output_base)
                    
                    file_result["output_files"]["json"] = json_path
                    file_result["output_files"]["text"] = text_path
                    
                    # 记录音频时长
                    if 'audio_info' in transcript and 'duration' in transcript['audio_info']:
                        file_result["duration_ms"] = transcript['audio_info']['duration']
                else:
                    file_result["status"] = "failed"
                
            except Exception as e:
                self.logger.error(f"处理文件 {file_name} 时出错: {e}")
                file_result["status"] = "error"
                file_result["error_message"] = str(e)
            
            # 添加到结果列表
            result["files"].append(file_result)
        
        # 生成汇总转录文件
        try:
            self._generate_summary(result, start_time)
        except Exception as e:
            self.logger.error(f"生成汇总转录失败: {e}")
            result["summary_error"] = str(e)
        
        # 最终进度
        if progress_callback:
            progress_callback(100, f"批量转录完成")
        
        return result
    
    def _generate_summary(self, batch_result, start_time):
        """
        为批量转录生成汇总文件
        
        参数:
            batch_result (dict): 批量转录结果
            start_time (str): 基准时间
        """
        output_dir = batch_result["output_dir"]
        summary_filename = os.path.join(output_dir, "all_transcripts.txt")
        
        with open(summary_filename, 'w', encoding='utf-8') as f:
            f.write(f"# 所有音频文件转录汇总\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"基准时间: {start_time}\n")
            f.write(f"文件数量: {len(batch_result['files'])}\n\n")
            
            f.write("## 每个文件的完整文本\n\n")
            
            for file_result in batch_result["files"]:
                file_name = file_result["name"]
                text_path = file_result["output_files"]["text"]
                
                f.write(f"### {file_name}\n\n")
                
                if file_result["status"] == "success" and text_path and os.path.exists(text_path):
                    try:
                        with open(text_path, 'r', encoding='utf-8') as text_file:
                            # 查找完整文本部分
                            complete_text = ""
                            in_complete_section = False
                            
                            for line in text_file:
                                if "## 完整文本" in line:
                                    in_complete_section = True
                                    continue
                                
                                if in_complete_section:
                                    complete_text += line
                        
                        f.write(complete_text.strip() + "\n\n")
                        
                    except Exception as e:
                        f.write(f"读取文件失败: {e}\n\n")
                else:
                    f.write(f"转录失败或文件不存在\n\n")
            
            # 打开文件仅保存路径
            batch_result["summary_file"] = summary_filename
        
        self.logger.info(f"汇总转录已保存至: {summary_filename}")
        return summary_filename