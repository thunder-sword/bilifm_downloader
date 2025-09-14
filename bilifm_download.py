#!/bin/python
#encoding=utf-8
#作用：获取b站的音频并转为mp3格式（真）
#版本：v0.1.0
#最后更新日期：2025-09-14

import os
import re
import logging
import subprocess
from rich.logging import RichHandler
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from typing import List, Optional, Union, Dict
from bilifm.audio import *

#初始化日志模块
logger = logging.getLogger("AppLogger")
logger.setLevel(logging.DEBUG)
#console_handler = logging.StreamHandler()
console_handler = RichHandler(rich_tracebacks=True)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", "%H:%M:%S")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# 自定义日志 Handler，将日志写入 Tkinter 文本框
class TextHandler(logging.Handler):
	def __init__(self, text_widget):
		super().__init__()
		self.text_widget = text_widget

	def emit(self, record):
		msg = self.format(record)
		self.text_widget.configure(state='normal')
		self.text_widget.insert(tk.END, msg + '\n')
		self.text_widget.see(tk.END)  # 自动滚动到底部
		self.text_widget.configure(state='disabled')

class App:
	def __init__(self, root):
		self.root = root
		self.root.title("音频提取工具")
		self.root.geometry("600x400")

		# URL 输入框
		tk.Label(root, text="URL:").pack(anchor="w", padx=10, pady=(10,0))
		self.url_entry = tk.Entry(root, width=80)
		self.url_entry.pack(padx=10, pady=5)

		# 保存路径输入框
		tk.Label(root, text="保存目录:").pack(anchor="w", padx=10, pady=(10,0))
		frame = tk.Frame(root)
		frame.pack(padx=10, pady=5, fill="x")
		self.path_entry = tk.Entry(frame, width=65)
		self.path_entry.pack(side="left", expand=True, fill="x")
		browse_btn = tk.Button(frame, text="选择目录", command=self.browse_directory)
		browse_btn.pack(side="left", padx=5)

		# 提取按钮
		extract_btn = tk.Button(root, text="提取音频", width=20, command=self.extract_action)
		extract_btn.pack(pady=10)

		# 日志框
		tk.Label(root, text="日志:").pack(anchor="w", padx=10, pady=(10,0))
		self.log_text = scrolledtext.ScrolledText(root, width=80, height=10, state='disabled')
		self.log_text.pack(padx=10, pady=5, fill="both", expand=True)

		# 初始化 logger
		text_handler = TextHandler(self.log_text)
		text_handler.setLevel(logging.INFO)
		text_handler.setFormatter(formatter)
		if len(logger.handlers) < 2:
			logger.addHandler(text_handler)

		logger.info("程序已成功启动")

	def browse_directory(self):
		directory = filedialog.askdirectory(title="选择保存目录")
		if directory:
			self.path_entry.delete(0, tk.END)
			self.path_entry.insert(0, directory)

	def extract_action(self):
		url = self.url_entry.get().strip()
		path = self.path_entry.get().strip() or os.getcwd()

		if not url:
			messagebox.showwarning("提示", "请输入 URL")
			return

		logger.debug(f"开始提取 URL: {url}")
		logger.debug(f"保存路径: {path}")

		try:
			os.makedirs(path, exist_ok=True)
			logger.debug("正在执行提取逻辑...")
			# TODO: 在这里实现真正的逻辑
			bvList=getBV(url)
			if bvList:
				logger.info("成功获取到BV号：{}".format('、'.join(bvList)))
			else:
				logger.error("url中不含有效BV号，请检查")
				messagebox.showwarning("提示", "URL不含有效的BV号")
				return
			#将每个bv号分别处理：
			for bv in bvList:
				logger.info("正在处理：{}".format(bv))
				file_name=downloadOne(bv, path)
				if not file_name:
					return
				src=os.path.join(path, file_name)
				logger.info("下载完成，文件位于：{}".format(src))
				
				#下载好了之后转换为mp3格式
				logger.info("正在将【{}】转换为mp3格式".format(file_name))
				dst_name="{}.mp3".format(".".join(file_name.split('.')[:-1]))
				dst=os.path.join(path, dst_name)
				
				if not toMp3(src, dst):
					logger.error("转换失败")
					messagebox.showwarning("提示", "{}转换格式失败".format(file_name))
					return
				
				logger.info("转换成功，最终文件位于：{}".format(dst))
				#如果转换成功就删除原文件
				logger.debug("正在删除原文件：{}".format(src))
				os.remove(src)
				logger.debug("删除结束")
				logger.info("任务完成：{}".format(bv))
				
		except Exception as e:
			logger.exception(f"发生错误: {e}")

# 重载Audio类
class MyAudio(Audio):
	def download(self, path: str = ""):
		start_time = time.time()
		try:
			for cid, part in zip(self.cid_list, self.part_list):
				if len(self.part_list) > 1:
					file_name = f"{self.title}-{part}.mp4"
				else:
					file_name = f"{self.title}.mp4"

				if len(file_name) > 255:
					file_name = file_name[:255]
				
				logger.info("正在下载【{}】".format(file_name))
				file_path = os.path.join(path, file_name)
				
				# 如果文件已存在，则跳过下载
				if os.path.exists(file_path):
					console.print(
						Panel(
							f"{self.title} 已存在，跳过下载",
							style="yellow",
							expand=False,
						)
					)
					logger.warning("此文件已存在，将跳过：{}".format(file_name))
					return

				params = get_signed_params(
					{
						"fnval": 16,
						"bvid": self.bvid,
						"cid": cid,
					}
				)
				res = requests.get(
					self.playUrl, params=params, headers=self.headers, timeout=60
				)

				json = res.json()

				if json["data"] is None:
					console.print(
						Panel(
							f"[bold red]数据字段无效[/bold red]\n"
							f"URL: {self.playUrl}\n"
							f"参数: {params}",
							title="错误",
							expand=False,
						)
					)
					return

				audio = json["data"]["dash"]["audio"]
				if not audio:
					console.print(
						Panel(
							f"[bold red]音频字段为空[/bold red]\n"
							f"URL: {self.playUrl}\n"
							f"参数: {params}",
							title="错误",
							expand=False,
						)
					)
					return

				base_url = None
				for au in audio:
					if au["id"] == self.audio_quality:
						base_url = au["baseUrl"]

				# no audio url corresponding to current audio quality
				if base_url is None:
					base_url = audio[0]["baseUrl"]

				response = requests.get(url=base_url, headers=self.headers, stream=True)

				total_size = int(response.headers.get("content-length", 0))

				with Progress(
					"[progress.description]{task.description}",
					BarColumn(),
					"[progress.percentage]{task.percentage:>3.0f}%",
					"•",
					DownloadColumn(),
					"•",
					TransferSpeedColumn(),
					console=console,
				) as progress:
					task = progress.add_task(
						f"[cyan]下载 {self.title}", total=total_size
					)

					with open(file_path, "wb") as f:
						for chunk in response.iter_content(chunk_size=8192):
							if chunk:
								f.write(chunk)
								progress.update(task, advance=len(chunk))

					# 添加下载完成的提示
					end_time = time.time()
					download_time = round(end_time - start_time, 2)
					console.print(
						Panel(
							f"[bold green]下载完成！[/bold green]用时 {download_time} 秒",
							expand=False,
						)
					)
			return file_name
		except Exception as e:
			console.print(
				Panel(
					f"[bold red]下载失败[/bold red]\n Code: {res.status_code} 错误: {str(e)}",
					title="异常",
					expand=False,
				)
			)
			raise e

# 将aac格式mp4文件转换为mp3文件
def toMp3(infile: str, outfile: str) -> bool:
	# 这样转换码率更加接近，近乎无损转换
	#infile="微信朋友圈刷屏的拆螺丝，究竟有多么垃圾？！.mp3"; ffmpeg -i "$infile" -c:a libmp3lame -b:a $(ffprobe -v error -select_streams a:0 -show_entries stream=max_bit_rate -of default=noprint_wrappers=1:nokey=1 "$infile") output.mp3
	
	#如果文件存在，则开始转换
	if not os.path.exists(infile):
		logger.error("原文件【{}】不存在，无法进行转换".format(infile))
		return False
	
	#####这条命令在windows上不可行，会返回N/A，所以干脆用固定码率192k
	# 1. 先获取 ffprobe 的结果（音频比特率）
	#probe_cmd = [
	#	"ffprobe", "-v", "error",
	#	"-select_streams", "a:0",
	#	"-show_entries", "stream=max_bit_rate",
	#	"-of", "default=noprint_wrappers=1:nokey=1",
	#	infile
	#	]
	
	#logger.debug("probe_cmd:")
	#logger.debug(' '.join(probe_cmd))
	
	#probe = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
	#if 0!=probe.returncode:
	#	logger.error("获取音频比特率失败，报错信息为：\n{}".format(probe.stderr))
	#	return False
	#bitrate = probe.stdout.strip()
	
	#logger.info("检测到比特率：【{}】bps".format(bitrate))
	
	####直接使用固定码率192k
	bitrate="192k"
	logger.info("目前转换音频码率为【{}】bps".format(bitrate))
	
	# 2. 拼接 ffmpeg 命令（转换格式为mp3）
	ffmpeg_cmd = [
		"ffmpeg",
		"-i", infile,
		"-c:a", "libmp3lame",
		"-b:a", bitrate,
		outfile
	]
	
	logger.debug("ffmpeg_cmd:")
	logger.debug(' '.join(ffmpeg_cmd))
	
	logger.info("开始转换文件格式")
	
	# 3. 用 Popen 执行并实时打印日志
	process = subprocess.Popen(
		ffmpeg_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		encoding="utf-8",   # 强制用 UTF-8 解码
		errors="replace"    # 出错时用  替代，不会抛异常
	)
	
	for line in process.stderr:  # ffmpeg 的输出大多在 stderr
		logger.debug(line.strip())
	
	process.wait()
	if 0!=process.returncode:
		logger.error("转换mp3格式失败")
		return False
	return True

# 下载一个BV号的相关音频
def downloadOne(bv: str, path: str="") -> str:
	audio=MyAudio(bv, AudioQualityEnums.k192)
	return audio.download(path)

# 提取 BV 号
def getBV(url: str) -> List[str]:
	return re.findall(r'BV[a-zA-Z0-9]{10}', url)

def main():
	root = tk.Tk()
	app = App(root)
	root.mainloop()

if __name__ == "__main__":
	main()
	#downloadOne("BV166YizqEjc")
	#toMp3("(AAC)妖怪.mp3", "妖怪.mp3")





