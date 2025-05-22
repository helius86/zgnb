#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Claude API服务模块
提供与Claude AI模型交互的功能
"""

import logging
import requests
import json
import time
from typing import Optional, Dict, Any

class ClaudeService:
    """Claude AI API服务类"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """
        初始化Claude服务
        
        参数:
            api_key (str): Claude API密钥
            model (str): Claude模型版本
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.logger = logging.getLogger("ClaudeService")
        
        # 预设的系统提示词
        self.system_prompt = """在这个project中我会每次给你一系列txt文档，这些文档是一个主播录播的文字转录版本，并且伴随着文字会有这句话被说出来的时间戳。

我需要你：
根据txt中的文字内容，根据你对文字的内容理解，将文字内容分成不多于10个的段落。
给每个段落取一个非常简短的概括（最简短的形式）
比如：
*开场（只有p1会有开场环节）
*上周情况调查
*港股
*下周情况
*正题

注意：
*你不需要一定切成10个段落，根据内容的重要程度和显著程度来自行判断；
*主播可能会提到个股的信息，关于这个个股的基本面或者走势等等，需要重点关注一下。个股的词汇我放在了下面热词词库中，请你帮忙留意一下；
*不是提到了关键词就代表这一段内容就可以被总结，你需要去明确观察关键词周围的内容来进行判断这一段具体在讲什么。


着重可以特定标出的地方/关键词是：
* 点名环节
* 净值曲线
* 下周锦囊（这个非常重要，提到的时候一定要单独列出；但是不要以为关于任何股市的技巧都是下周锦囊，一定是在一个区域内提到了这个关键词，以及重复提到下周走势的内容才算下周锦囊）
* SC留言环节
* 股票指标与技法（四分之三阴量线，J值（勾），大风车，主力...)


回答形式：
* 你在回答的时候必须要有：标题，标题对应的时间戳，以及内容总结
* 一定要注意分开的段落不要超过10段


可能有识别不准确的地方，专属的热词词汇如下：
* 四分之三阴量线
* 青花
* 清香型
* 免子、阿免（指的是中国中免）
* 米儿
* 商K
* 迪迪
* 宁子
* 德德
* 浮盈
* z哥
* 赛赛（有时候可能被识别成shanshan）
* 叭（表示语气，经常出现在描述股价上涨过程中的突破）
* 特扑（方言版股价的突破）
* 破净
* 攒局，攒一大局
* 勾，钩，gou的发音（都是指KDJ指标中的J，你可以修复为J这个符号）
* 大富翁"""
        
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
    
    def analyze_transcript(self, transcript_content: str, progress_callback=None) -> Optional[str]:
        """
        分析转录文本
        
        参数:
            transcript_content (str): 转录文本内容
            progress_callback (callable, optional): 进度回调函数
            
        返回:
            str: 分析结果，失败返回None
        """
        if not transcript_content.strip():
            self.logger.error("转录内容为空")
            return None
        
        if progress_callback:
            progress_callback(10, "准备发送请求到Claude API")
        
        # 构建请求数据
        data = {
            "model": self.model,
            "max_tokens": 4000,
            "system": self.system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": transcript_content
                }
            ]
        }
        
        try:
            if progress_callback:
                progress_callback(30, "正在发送请求到Claude API")
            
            self.logger.info(f"发送请求到Claude API，模型: {self.model}")
            
            # 发送请求
            response = requests.post(
                self.base_url,
                headers=self._get_headers(),
                json=data,
                timeout=120  # 2分钟超时
            )
            
            if progress_callback:
                progress_callback(60, "正在等待Claude API响应")
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f", 错误信息: {error_data.get('error', {}).get('message', response.text)}"
                    except:
                        error_msg += f", 响应内容: {response.text}"
                
                self.logger.error(error_msg)
                if progress_callback:
                    progress_callback(100, f"错误: {error_msg}")
                return None
            
            if progress_callback:
                progress_callback(80, "正在解析Claude API响应")
            
            # 解析响应
            result = response.json()
            
            if "content" in result and len(result["content"]) > 0:
                analysis_result = result["content"][0].get("text", "")
                
                if analysis_result:
                    self.logger.info("Claude API分析完成")
                    if progress_callback:
                        progress_callback(100, "分析完成")
                    return analysis_result
                else:
                    self.logger.error("Claude API返回的内容为空")
                    if progress_callback:
                        progress_callback(100, "错误: API返回内容为空")
                    return None
            else:
                self.logger.error(f"Claude API响应格式异常: {result}")
                if progress_callback:
                    progress_callback(100, "错误: API响应格式异常")
                return None
                
        except requests.Timeout:
            error_msg = "Claude API请求超时"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(100, f"错误: {error_msg}")
            return None
            
        except requests.ConnectionError:
            error_msg = "无法连接到Claude API"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(100, f"错误: {error_msg}")
            return None
            
        except Exception as e:
            error_msg = f"Claude API请求异常: {str(e)}"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(100, f"错误: {error_msg}")
            return None
    
    def test_connection(self) -> tuple[bool, str]:
        """
        测试Claude API连接
        
        返回:
            tuple: (是否成功, 消息)
        """
        try:
            # 发送一个简单的测试请求
            data = {
                "model": self.model,
                "max_tokens": 10,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello"
                    }
                ]
            }
            
            response = requests.post(
                self.base_url,
                headers=self._get_headers(),
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return True, "Claude API连接测试成功"
            else:
                error_msg = f"连接失败，状态码: {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f", 错误: {error_data.get('error', {}).get('message', response.text)}"
                    except:
                        error_msg += f", 响应: {response.text}"
                return False, error_msg
                
        except requests.Timeout:
            return False, "连接超时"
        except requests.ConnectionError:
            return False, "无法连接到Claude API"
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"