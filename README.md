# zgnb

项目根目录/
├── main_app.py              # 主应用程序
├── run.py                   # 启动脚本
├── requirements.txt         # 项目依赖
├── README.md                # 使用说明
├── ui_components/           # UI组件目录
│   ├── __init__.py          # UI组件包初始化文件
│   ├── extraction_tab.py    # 音频提取选项卡
│   ├── upload_tab.py        # TOS上传选项卡
│   ├── transcription_tab.py # 批量转录选项卡
│   └── settings_tab.py      # 设置选项卡
└── utils/                   # 工具目录
    ├── __init__.py          # 工具包初始化文件
    ├── audio_processor.py   # 音频处理器
    ├── config_manager.py    # 配置管理器
    ├── log_handler.py       # 日志处理器
    ├── tos_uploader.py      # TOS上传器
    ├── transcription_service.py # 转录服务
    └── worker_thread.py     # 工作线程



主程序:
- main_app.py - 主应用程序
- run.py - 启动脚本

UI组件:
- ui_components/extraction_tab.py - 音频提取选项卡
- ui_components/upload_tab.py - TOS上传选项卡
- ui_components/transcription_tab.py - 批量转录选项卡
- ui_components/settings_tab.py - 设置选项卡

工具类:
- utils/audio_processor.py - 音频处理器
- utils/config_manager.py - 配置管理器
- utils/log_handler.py - 日志处理器
- utils/tos_uploader.py - TOS上传器
- utils/transcription_service.py - 转录服务
- utils/worker_thread.py - 工作线程
