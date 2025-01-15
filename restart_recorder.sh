#!/bin/bash

# 脚本参数：Python 脚本的完整路径
PYTHON_SCRIPT="/home/ubuntu/liveRecorder/main.py"

# 检查是否提供了Python脚本路径
if [ -z "$PYTHON_SCRIPT" ]; then
    echo "Usage: $0 <path_to_python_script>"
    exit 1
fi

# 确认文件存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "File not found: $PYTHON_SCRIPT"
    exit 1
fi

# 获取脚本的名称（不包括路径）
SCRIPT_NAME=$(basename "$PYTHON_SCRIPT")

# 查找并杀死进程
echo "Stopping $SCRIPT_NAME..."
pkill -f "$SCRIPT_NAME"

# 等待一段时间确保进程已经停止
sleep 2

# 检查进程是否仍然存在
if pgrep -f "$SCRIPT_NAME" > /dev/null; then
    echo "Failed to stop $SCRIPT_NAME"
    exit 1
else
    echo "$SCRIPT_NAME stopped successfully."
fi
# 结束chrome进程
killall -9 chrome
if [ $? -eq 0 ]; then
  echo "已成功结束chrome进程。"
else
  echo "没有找到chrome进程或结束失败。"
fi

# 结束ffmpeg进程
pkill -9 ffmpeg
if [ $? -eq 0 ]; then
  echo "已成功结束ffmpeg进程。"
else
  echo "没有找到ffmpeg进程或结束失败。"
fi
# 启动进程
echo "Starting $SCRIPT_NAME..."
# 使用 nohup 让程序在后台运行，并将输出重定向到日志文件
nohup /usr/bin/python3 "$PYTHON_SCRIPT" > /dev/null 2>&1 &
# 获取新进程的PID
NEW_PID=$!

# 检查进程是否成功启动
sleep 2
if ps -p $NEW_PID > /dev/null; then
    echo "$SCRIPT_NAME started successfully with PID $NEW_PID."
else
    echo "Failed to start $SCRIPT_NAME"
    exit 1
fi

exit 0
