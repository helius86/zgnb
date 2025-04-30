#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频处理器模块
提供从视频中提取音频和音频分割功能
"""

import os
import subprocess
import json
import logging
import time
from datetime import datetime
import tempfile
import shutil

class AudioProcessor:
    """音频处理类，用于从视频中提取音频并分割"""
    
    def __init__(self, 
                 ffmpeg_path='ffmpeg', 
                 segment_duration=3600, 
                 output_dir=None,
                 audio_format='mp3',
                 audio_bitrate='128k',
                 audio_channels=1,
                 audio_sample_rate=16000,
                 noise_reduction=False,
                 normalize_volume=True):
        """
        初始化音频处理器
        
        参数:
            ffmpeg_path (str): FFmpeg可执行文件的路径
            segment_duration (int): 分段时长（秒）
            output_dir (str): 输出目录
            audio_format (str): 音频格式
            audio_bitrate (str): 音频比特率
            audio_channels (int): 音频通道数
            audio_sample_rate (int): 音频采样率
            noise_reduction (bool): 是否降噪
            normalize_volume (bool): 是否音量归一化
        """
        self.ffmpeg_path = ffmpeg_path
        self.segment_duration = segment_duration
        self.output_dir = output_dir
        self.audio_format = audio_format
        self.audio_bitrate = audio_bitrate
        self.audio_channels = audio_channels
        self.audio_sample_rate = audio_sample_rate
        self.noise_reduction = noise_reduction
        self.normalize_volume = normalize_volume
        self.logger = logging.getLogger("AudioProcessor")
        
        # 检查ffmpeg是否可用
        self._check_ffmpeg()
        
    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode != 0:
                self.logger.error("FFmpeg检查失败，请确认FFmpeg已正确安装")
                raise RuntimeError("FFmpeg不可用")
            
            self.logger.info(f"FFmpeg可用: {result.stdout.splitlines()[0] if result.stdout else ''}")
            return True
        except FileNotFoundError:
            self.logger.error(f"找不到FFmpeg，请安装FFmpeg或提供正确的路径（当前路径: {self.ffmpeg_path}）")
            raise
            
    def get_video_duration(self, video_path):
        """
        获取视频时长（秒）
        
        参数:
            video_path (str): 视频文件路径
            
        返回:
            float: 视频时长（秒）
        """
        try:
            cmd = [
                self.ffmpeg_path, 
                "-i", video_path, 
                "-v", "quiet", 
                "-show_entries", "format=duration", 
                "-of", "json"
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                self.logger.error(f"获取视频时长失败: {result.stderr}")
                return 0
            
            output = json.loads(result.stdout)
            duration = float(output['format']['duration'])
            self.logger.debug(f"视频 {os.path.basename(video_path)} 时长: {duration} 秒")
            return duration
        except Exception as e:
            self.logger.error(f"获取视频 {os.path.basename(video_path)} 时长时出错: {str(e)}")
            return 0
            
    def extract_audio(self, video_path, output_path=None, progress_callback=None):
        """
        从视频文件提取音频
        
        参数:
            video_path (str): 视频文件路径
            output_path (str, optional): 输出音频文件路径
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            str: 提取的音频文件路径，失败返回None
        """
        if not os.path.exists(video_path):
            self.logger.error(f"视频文件不存在: {video_path}")
            return None
        
        # 如果未指定输出路径，生成默认路径
        if output_path is None:
            # 确保输出目录存在
            if self.output_dir is None:
                # 在视频所在目录创建一个audio_output子目录
                video_dir = os.path.dirname(video_path)
                self.output_dir = os.path.join(video_dir, "audio_output")
            
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 生成输出文件路径
            video_basename = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(self.output_dir, f"{video_basename}.{self.audio_format}")
        
        # 构建FFmpeg命令
        cmd = [self.ffmpeg_path, "-y", "-i", video_path]
        
        # 添加音频处理选项
        filter_options = []
        
        if self.noise_reduction:
            # 使用基本的降噪过滤器
            filter_options.append("afftdn=nf=-20")
        
        if self.normalize_volume:
            # 归一化音量
            filter_options.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        
        # 合并音频过滤器
        if filter_options:
            cmd.extend(["-af", ",".join(filter_options)])
        
        # 添加音频编码选项
        cmd.extend([
            "-vn",  # 不包含视频
            "-ar", str(self.audio_sample_rate),  # 设置采样率
            "-ac", str(self.audio_channels),  # 设置通道数
            "-b:a", self.audio_bitrate,  # 设置比特率
            output_path  # 输出文件
        ])
        
        self.logger.info(f"提取音频: {os.path.basename(video_path)} -> {os.path.basename(output_path)}")
        
        try:
            # 启动FFmpeg进程
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # 监控进度
            duration = self.get_video_duration(video_path)
            if duration <= 0:
                self.logger.warning("无法获取视频时长，将无法显示进度百分比")
            
            # 实时获取处理进度
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # 从FFmpeg输出中提取时间信息
                if "time=" in line and duration > 0 and progress_callback:
                    # 提取时间戳
                    time_parts = line.split("time=")[1].split()[0].split(":")
                    if len(time_parts) == 3:
                        hours, minutes, seconds = time_parts
                        current_time = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
                        progress = int(min(100, current_time / duration * 100))
                        progress_callback(progress, f"正在提取音频: {progress}%")
            
            # 检查处理结果
            return_code = process.poll()
            if return_code != 0:
                _, stderr = process.communicate()
                self.logger.error(f"提取音频失败: {stderr}")
                return None
            
            self.logger.info(f"成功提取音频: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"提取音频时出错: {str(e)}")
            return None
            
    def split_audio(self, audio_path, progress_callback=None):
        """
        将长音频文件分割为指定时长的片段
        
        参数:
            audio_path (str): 音频文件路径
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            list: 分割后的音频片段路径列表
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return []
        
        # 如果分段时长为0，则不分割
        if self.segment_duration <= 0:
            self.logger.info(f"分段时长为0，不分割音频文件: {os.path.basename(audio_path)}")
            return [audio_path]
        
        # 获取音频时长
        cmd = [
            self.ffmpeg_path, 
            "-i", audio_path, 
            "-v", "quiet", 
            "-show_entries", "format=duration", 
            "-of", "json"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            self.logger.error(f"获取音频时长失败: {result.stderr}")
            return [audio_path]  # 返回原始文件
        
        output = json.loads(result.stdout)
        duration = float(output['format']['duration'])
        
        # 如果音频时长小于分段时长，不需要分割
        if duration <= self.segment_duration:
            self.logger.info(f"音频文件 {os.path.basename(audio_path)} 无需分割 (时长: {duration:.2f}秒)")
            return [audio_path]
        
        # 计算需要分割的片段数
        segment_count = int(duration / self.segment_duration) + (1 if duration % self.segment_duration > 0 else 0)
        self.logger.info(f"音频文件 {os.path.basename(audio_path)} 将分割为 {segment_count} 个片段")
        
        if progress_callback:
            progress_callback(0, f"准备分割音频为 {segment_count} 个片段")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(audio_path)
        
        # 分割音频
        audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
        segments = []
        
        for i in range(segment_count):
            start_time = i * self.segment_duration
            segment_path = os.path.join(output_dir, f"{audio_basename}_segment_{i+1}.{self.audio_format}")
            
            cmd = [
                self.ffmpeg_path,
                "-y",  # 覆盖输出文件
                "-i", audio_path,
                "-ss", str(start_time),  # 开始时间
                "-t", str(self.segment_duration),  # 片段时长
                "-c:a", "copy",  # 直接复制音频流，不重新编码
                segment_path
            ]
            
            if progress_callback:
                progress = int((i / segment_count) * 100)
                progress_callback(progress, f"分割片段 {i+1}/{segment_count}")
            
            self.logger.info(f"分割音频片段 {i+1}/{segment_count}: {os.path.basename(segment_path)}")
            
            try:
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode != 0:
                    self.logger.error(f"分割音频片段失败: {result.stderr}")
                    continue
                
                segments.append(segment_path)
                self.logger.info(f"成功分割音频片段: {segment_path}")
                
            except Exception as e:
                self.logger.error(f"分割音频片段时出错: {str(e)}")
        
        if progress_callback:
            progress_callback(100, f"完成分割，共 {len(segments)} 个片段")
        
        return segments
        
    def process_video(self, video_path, progress_callback=None):
        """
        处理单个视频：提取音频并根据需要分割
        
        参数:
            video_path (str): 视频文件路径
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            dict: 处理结果，包含原始视频信息、提取的音频和分割的片段
        """
        video_basename = os.path.basename(video_path)
        self.logger.info(f"开始处理视频: {video_basename}")
        
        if progress_callback:
            progress_callback(0, f"开始处理视频: {video_basename}")
        
        # 准备输出目录
        video_dir = os.path.dirname(video_path)
        output_dir = os.path.join(video_dir, "audio_output")
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        
        result = {
            "video": {
                "path": video_path,
                "name": video_basename,
                "duration": self.get_video_duration(video_path)
            },
            "audio": None,
            "segments": [],
            "output_dir": output_dir,
            "metadata": {
                "processed_time": datetime.now().isoformat(),
                "settings": {
                    "segment_duration": self.segment_duration,
                    "audio_format": self.audio_format,
                    "audio_bitrate": self.audio_bitrate,
                    "audio_channels": self.audio_channels,
                    "audio_sample_rate": self.audio_sample_rate,
                    "noise_reduction": self.noise_reduction,
                    "normalize_volume": self.normalize_volume
                }
            }
        }
        
        # 提取音频，进度占50%
        def extract_progress(p, msg):
            if progress_callback:
                # 音频提取占总进度的50%
                progress_callback(p // 2, msg)
        
        audio_path = self.extract_audio(video_path, progress_callback=extract_progress)
        if not audio_path:
            self.logger.error(f"提取音频失败，跳过视频: {video_basename}")
            if progress_callback:
                progress_callback(100, f"处理失败: 无法提取音频")
            return result
        
        result["audio"] = audio_path
        
        # 分割音频，进度占50%
        def split_progress(p, msg):
            if progress_callback:
                # 分割从50%开始，占总进度的50%
                progress_callback(50 + p // 2, msg)
        
        # 根据需要分割音频
        audio_segments = self.split_audio(audio_path, progress_callback=split_progress)
        result["segments"] = audio_segments
        
        # 生成每个片段的时间信息
        segment_info = []
        for i, segment_path in enumerate(audio_segments):
            start_time = i * self.segment_duration
            end_time = min((i + 1) * self.segment_duration, result["video"]["duration"])
            
            segment_info.append({
                "path": segment_path,
                "name": os.path.basename(segment_path),
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "index": i + 1
            })
        
        result["segment_info"] = segment_info
        
        # 保存元数据
        metadata_path = os.path.join(output_dir, f"{os.path.splitext(video_basename)[0]}_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"视频处理完成: {video_basename}")
        if progress_callback:
            progress_callback(100, f"处理完成: {video_basename}")
        
        return result
        
    def process_directory(self, input_dir, video_extensions=None, progress_callback=None):
        """
        批量处理目录中的所有视频文件
        
        参数:
            input_dir (str): 输入目录路径
            video_extensions (list, optional): 视频文件扩展名列表
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            list: 所有处理结果的列表
        """
        if not os.path.isdir(input_dir):
            self.logger.error(f"输入目录不存在: {input_dir}")
            return []
        
        if video_extensions is None:
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        
        video_extensions = [ext.lower() for ext in video_extensions]
        
        # 查找所有符合条件的视频文件
        video_files = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in video_extensions:
                    video_files.append(file_path)
        
        self.logger.info(f"在目录 {input_dir} 中找到 {len(video_files)} 个视频文件")
        
        if not video_files:
            self.logger.warning(f"在目录 {input_dir} 中未找到视频文件")
            return []
        
        # 创建输出目录
        output_dir = os.path.join(input_dir, "audio_output")
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir
        
        # 处理所有视频
        results = []
        total_videos = len(video_files)
        
        for i, video_path in enumerate(video_files):
            # 更新总体进度
            if progress_callback:
                overall_progress = int(100 * i / total_videos)
                progress_callback(overall_progress, f"处理视频 {i+1}/{total_videos}: {os.path.basename(video_path)}")
            
            # 单个视频进度回调
            def video_progress(percent, message):
                if progress_callback:
                    # 计算总体进度：当前视频的进度占比为 1/total_videos
                    video_contribution = percent / total_videos
                    overall_progress = int(100 * i / total_videos + video_contribution)
                    progress_callback(overall_progress, message)
            
            # 处理视频
            result = self.process_video(video_path, progress_callback=video_progress)
            results.append(result)
        
        # 保存处理结果摘要
        summary_path = os.path.join(output_dir, f"extraction_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "processed_time": datetime.now().isoformat(),
                "input_directory": input_dir,
                "output_directory": output_dir,
                "video_count": len(video_files),
                "results": [
                    {
                        "video": r["video"],
                        "audio": r["audio"],
                        "segments_count": len(r["segments"])
                    } for r in results
                ]
            }, f, ensure_ascii=False, indent=2)
        
        # 最终进度
        if progress_callback:
            progress_callback(100, f"处理完成，共处理 {total_videos} 个视频")
        
        self.logger.info(f"处理摘要已保存至: {summary_path}")
        return results