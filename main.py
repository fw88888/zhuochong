<<<<<<< HEAD

from pynput import keyboard
import threading
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import io
import time
import wave
import requests
import speech_recognition as sr
from tqdm import tqdm
import re
import sys
import random
import winsound
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, 
                            QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtWidgets import QSystemTrayIcon  # 添加到文件顶部的导入部分

# 合并所有导入，删除重复导入

class AudioRecorder:
    def __init__(self, rate=16000):
        """初始化录音器，设置采样率"""
        self.rate = rate
        self.recognizer = sr.Recognizer()
        self.recording = False
        self.audio_data = None
        self.stop_recording = threading.Event()
 
    def record_on_key(self):
        """按住空格键录音的方法"""
        self.stop_recording.clear()
        print("请按住空格键开始录音，松开结束...", flush=True)
        
        # 创建并启动键盘监听线程
        keyboard_thread = threading.Thread(target=self._keyboard_listener)
        keyboard_thread.daemon = True
        keyboard_thread.start()
        
        # 等待录音开始
        while not self.recording and not self.stop_recording.is_set():
            time.sleep(0.1)
        
        # 如果用户取消了录音
        if self.stop_recording.is_set():
            return None
            
        # 开始录音
        with sr.Microphone(sample_rate=self.rate) as source:
            print("正在录音中...", flush=True)
            try:
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)
                self.audio_data = audio.get_wav_data()
                return io.BytesIO(self.audio_data)
            except Exception as e:
                print(f"录音出错: {str(e)}")
                return None
    
    def save_wav(self, audio_data, filename="temp_output.wav"):
        """将音频数据保存为WAV文件"""
        audio_data.seek(0)
        with wave.open(filename, 'wb') as wav_file:
            nchannels = 1
            sampwidth = 2  # 16-bit audio
            framerate = self.rate  # 采样率
            comptype = "NONE"
            compname = "not compressed"
            audio_frames = audio_data.read()
 
            wav_file.setnchannels(nchannels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            wav_file.setcomptype(comptype, compname)
            wav_file.writeframes(audio_frames)
        audio_data.seek(0)  # 重置指针位置，以便后续使用
    
    def _keyboard_listener(self):
        """键盘监听线程"""
        def on_press(key):
            try:
                if key == keyboard.Key.space and not self.recording:
                    self.recording = True
                    print("开始录音...")
            except:
                pass
                
        def on_release(key):
            try:
                if key == keyboard.Key.space and self.recording:
                    self.recording = False
                    print("录音结束")
                    return False  # 停止监听
                elif key == keyboard.Key.esc:
                    self.stop_recording.set()
                    print("已取消录音")
                    return False  # 停止监听
            except:
                pass
                
        # 启动键盘监听
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
 
    def run(self):
        """运行录音功能并保存音频文件"""
        audio_data = self.record_on_key()
        if audio_data:
            self.save_wav(audio_data, "temp_output.wav")
        return audio_data
 
class SenseVoice:
    def __init__(self, api_url, emo=False):
        """初始化语音识别接口，设置API URL和情感识别开关"""
        self.api_url = api_url
        self.emo = emo
 
    def _extract_second_bracket_content(self, raw_text):
        """提取文本中第二对尖括号内的内容"""
        match = re.search(r'<[^<>]*><([^<>]*)>', raw_text)
        if match:
            return match.group(1)
        return None
 
    def _get_speech_text(self, audio_data):
        """将音频数据发送到API并获取识别结果"""
        print('正在进行语音识别')
        files = [('files', audio_data)]
        data = {'keys': 'audio1', 'lang': 'auto'}
 
        response = requests.post(self.api_url, files=files, data=data)
        if response.status_code == 200:
            result_json = response.json()
            if "result" in result_json and len(result_json["result"]) > 0:
                if self.emo:
                    result = self._extract_second_bracket_content(result_json["result"][0]["raw_text"]) + "\n" + result_json["result"][0]["text"]
                    return result
                else:
                    return result_json["result"][0]["text"]
            else:
                return "未识别到有效的文本"
        else:
            return f"请求失败，状态码: {response.status_code}"
 
    def speech_to_text(self, audio_data):
        """调用API进行语音识别并返回结果"""
        return self._get_speech_text(audio_data)

def get_and_play_audio(text, speaker, pet_instance=None):
    """
    从TTS服务获取音频并使用winsound播放，同时在桌宠聊天框显示
    """
    # 构建URL
    base_url = "http://127.0.0.1:9880/"
    params = {
        "text": text,
        "speaker": speaker
    }
    
    try:
        # 发送GET请求
        print("正在请求音频...")
        response = requests.get(base_url, params=params)
        
        # 检查响应状态
        if response.status_code == 200:
            # 保存音频到临时文件
            filename = "temp_audio.wav"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # 使用winsound播放音频，同时显示文本
            print("正在播放音频...")
            # 在开始播放音频时才显示文本
            if pet_instance:
                pet_instance.update_chat(text)
            winsound.PlaySound(filename, winsound.SND_FILENAME)
            print("播放完成")
            
        else:
            print(f"请求失败，状态码: {response.status_code}")
    
    except Exception as e:
        print(f"发生错误: {str(e)}")

def process_voice_interaction(pet):
    """处理完整的语音交互流程"""
    try:
        # 设置桌宠为工作状态
        pet.is_working = True
        
        # 创建录音器并运行
        recorder = AudioRecorder()
        pet.update_chat("请按住空格键说话，松开结束...")
        audio_data = recorder.run()
        
        if audio_data:
            # 语音识别
            api_url = "http://127.0.0.1:8666/api/v1/asr"
            sense_voice = SenseVoice(api_url, emo=True)
            result1 = sense_voice.speech_to_text(audio_data)
            print("识别结果:", result1)
            
            # 过滤掉情感标签和其他标记，只保留实际识别内容
            clean_result = re.sub(r'\|[A-Z_]+\|', '', result1)
            
            # 显示语音识别结果到桌宠
            pet.update_chat(f"您说: {clean_result}")
            time.sleep(2)  # 给用户时间阅读识别结果
            
            # 大模型处理
            model = ChatOllama(
                api_key='ollama',
                base_url='http://127.0.0.1:11434/',
                model = 'gemma3:12b'
            )
            
            prompt_str = """
            #下面我会给你提供一句中文问题，请用中文回答问题！
            提问：{question}
            """
            
            prompt = ChatPromptTemplate.from_template(prompt_str)
            output = StrOutputParser()
            chain = prompt | model | output
            
            pet.update_chat("我正在思考...")
            # 执行构建的chain，获取结果
            result2 = chain.invoke({'question':result1})
            print(result2)
            
            # 语音合成并播放，同时在桌宠显示文本
            text = result2
            speaker = "leijun.pt"
            get_and_play_audio(text, speaker, pet)
        else:
            pet.update_chat("未检测到语音输入")
    finally:
        # 无论是否成功，都将桌宠设置回非工作状态
        pet.is_working = False

class StdoutRedirect(QObject):
    new_output = pyqtSignal(str)  # 新增信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.old_stdout = sys.stdout
        sys.stdout = self
        # 添加需要过滤的输出内容
        self.filter_texts = [
            "正在进行语音识别", 
            "正在请求音频", 
            "正在播放音频",
            "倒计时",
            "请在倒计时",
            "识别结果",  
            "播放完成",   
            "|EMO_",     
            "控制台",
            "请按住空格键",  # 添加新的过滤内容
            "开始录音",      # 添加新的过滤内容
            "录音结束",      # 添加新的过滤内容
            "正在录音中",    # 添加新的过滤内容
            "已取消录音"     # 添加新的过滤内容
        ]

    def write(self, text):
        # 过滤掉不需要显示在聊天框的内容
        if text.strip() and not any(filter_text in text for filter_text in self.filter_texts):
            self.new_output.emit(text.strip())  # 发射信号
        self.old_stdout.write(text)  # 保留控制台输出

    def flush(self):
        self.old_stdout.flush()

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        # 窗口初始化
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(300, 300)  # 放大窗口尺寸
        
        # 初始化组件
        self.init_pet_animation()
        self.init_chat_system()
        self.init_tray_icon()
        
        # 定时器配置 - 将间隔从8000毫秒改为300000毫秒（5分钟）
        self.action_timer = QTimer(self)
        self.action_timer.timeout.connect(self.random_behavior)
        self.action_timer.start(300000)  # 修改为5分钟
        
        # 是否处于工作模式（语音交互中）
        self.is_working = False
        
        # 位置初始化 - 移动到右下角
        screen_geometry = QApplication.desktop().availableGeometry()
        self.move(screen_geometry.width() - self.width(), 
                  screen_geometry.height() - self.height())
                  
        # 添加鼠标拖动相关变量
        self.dragging = False
        self.drag_position = QPoint()
        
    # 添加鼠标事件处理函数
    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            # 更新聊天框位置
            if not self.chat_label.isHidden():
                self.update_chat_position()
            event.accept()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件处理"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        
    def init_pet_animation(self):
        """宠物动画系统"""
        self.pet_label = QLabel(self)
        
        # 使用绝对路径加载GIF文件
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = os.path.join(current_dir, "pet_idle.gif")
        
        # 检查文件是否存在
        if not os.path.exists(gif_path):
            print(f"错误: 找不到GIF文件: {gif_path}")
            # 如果找不到文件，可以使用一个备用图像或显示错误信息
            self.pet_label.setText("找不到图像文件")
            self.pet_label.setStyleSheet("background-color: white; color: red;")
            self.pet_label.setFixedSize(200, 200)
            return
            
        self.movie = QMovie(gif_path)
        
        # 添加错误处理
        if self.movie.isValid():
            # 设置等比例缩放
            self.pet_label.setScaledContents(True)
            self.pet_label.setFixedSize(200, 200)  # 放大尺寸到200x200
            self.movie.setScaledSize(QSize(200, 200))  # 设置GIF缩放尺寸
            
            self.pet_label.setMovie(self.movie)
            self.movie.start()
        else:
            print(f"错误: GIF文件无效: {gif_path}")
            self.pet_label.setText("图像文件无效")
            self.pet_label.setStyleSheet("background-color: white; color: red;")
            self.pet_label.setFixedSize(200, 200)

    def init_chat_system(self):
        """聊天系统"""
        self.chat_label = QLabel(self)
        self.chat_label.setStyleSheet("""
            background: rgb(255, 255, 255);  /* 使用完全不透明的白色 */
            border-radius: 6px;  /* 缩小圆角 */
            padding: 6px;  /* 缩小内边距 */
            color: #333;
            font: 11px 'Microsoft YaHei';  /* 增大字体从9px到11px */
            border: 1px solid #ccc;  /* 加深边框颜色 */
            min-width: 120px;  /* 缩小最小宽度 */
            max-width: 240px;  /* 缩小最大宽度 */
        """)
        self.chat_label.setWordWrap(True)
        self.chat_label.hide()
        
        # 调整初始位置（向右偏移）
        self.chat_label.move(self.width()-150, 10)
        
        # 聊天框定时器
        self.chat_timer = QTimer(self)
        self.chat_timer.timeout.connect(lambda: self.chat_label.hide())

        
    def update_chat(self, text):
        """更新聊天内容（同步位置调整）"""
        # 如果是大模型回答，显示时间更长
        is_model_response = not text.startswith("控制台:") and not text.startswith("请说话") and not text.startswith("我正在思考")
        
        # 每10个字符添加一个换行符，确保文本不会太宽，并居中显示
        lines = []
        current_line = ""
        for i, char in enumerate(text):
            current_line += char
            if (i + 1) % 10 == 0 or i == len(text) - 1:  # 从8改为10
                lines.append(current_line)
                current_line = ""
        
        # 将每行文本居中处理
        formatted_text = ""
        for line in lines:
            # 计算需要添加的空格数以居中显示
            padding = max(0, (10 - len(line)) // 2)  # 从8改为10
            centered_line = " " * padding + line
            formatted_text += centered_line + "\n"
        
        self.chat_label.setText(formatted_text)
        self.chat_label.adjustSize()
        
        # 自动调整聊天框宽度，根据文本内容
        max_line_length = max([len(line) for line in lines], default=0)
        ideal_width = max(120, min(240, max_line_length * 12))  # 根据最长行计算理想宽度
        
        self.chat_label.setFixedWidth(ideal_width)
        self.chat_label.adjustSize()  # 重新调整高度
        
        # 确保聊天框高度足够显示所有文本
        font_metrics = self.chat_label.fontMetrics()
        text_rect = font_metrics.boundingRect(
            0, 0, self.chat_label.width() - 12, 1000,
            Qt.TextWordWrap, formatted_text
        )
        # 增加聊天框的高度，给文本更多空间
        self.chat_label.setMinimumHeight(text_rect.height() + 30)
            
        # 向右偏移调整，但确保不会超出屏幕
        screen_width = QApplication.desktop().availableGeometry().width()
        # 将聊天框位置调整得更靠左一些
        x_pos = min(self.width() - self.chat_label.width() - 20,
                   screen_width - self.chat_label.width() - 10)
        
        self.chat_label.move(x_pos, 10)  # 保持垂直位置不变
        self.chat_label.show()
        
        # 根据文本类型和长度调整显示时间
        if is_model_response:
            display_time = max(10000, len(text) * 200)
        else:
            display_time = max(5000, len(text) * 150)
            
        self.chat_timer.start(display_time)

    def update_chat_position(self):
        """同步更新聊天框位置"""
        # 确保聊天框不会超出屏幕
        screen_width = QApplication.desktop().availableGeometry().width()
        # 将聊天框位置调整得更靠左一些，减小偏移量
        x_pos = min(self.width() - self.chat_label.width() - 20,  # 这里将+50改为-20，向左调整
                   screen_width - self.chat_label.width() - 10)
        
        self.chat_label.move(x_pos, 10)
    def init_tray_icon(self):
        """系统托盘功能"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon("icon.png"))
        
        tray_menu = QMenu()
        tray_menu.addAction(QAction("显示", self, triggered=self.show_normal))
        tray_menu.addAction(QAction("退出", self, triggered=self.clean_exit))
        self.tray.setContextMenu(tray_menu)
        
        self.tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def show_normal(self):
        """显示窗口并激活"""
        self.show()
        self.activateWindow()
        
    def clean_exit(self):
        """安全退出"""
        self.tray.hide()
        QApplication.quit()


    def random_behavior(self):
        """随机行为"""
        # 如果处于工作模式，不执行随机行为
        if self.is_working:
            return
            
        behaviors = [
            ("pet_walk.gif", ["出去散步~", "今天天气不错"]),
            ("pet_eat.gif", ["想吃小鱼干", "肚子饿饿..."]),
            ("pet_sleep.gif", ["Zzzz...", "好困啊"]),
            ("pet_idle.gif", ["主人你好！", "要摸摸吗？"])
        ]
        gif, msgs = random.choice(behaviors)
        self.switch_animation(gif)
        self.update_chat(random.choice(msgs))
        
    def switch_animation(self, gif_path):
        """动画切换"""
        # 使用绝对路径加载GIF文件
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_gif_path = os.path.join(current_dir, gif_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_gif_path):
            print(f"错误: 找不到GIF文件: {full_gif_path}")
            return
            
        self.movie.stop()
        self.movie.setFileName(full_gif_path)
        self.movie.setScaledSize(QSize(200, 200))  # 保持缩放尺寸一致
        self.movie.start()

# 在文件末尾的主程序部分进行修改

if __name__ == "__main__":
    # 首先创建并启动桌面桌宠应用
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet()
    pet.show()
    
    # 创建一个循环语音交互的函数
    def continuous_voice_interaction():
        while True:
            try:
                # 处理一次语音交互
                process_voice_interaction(pet)
                # 交互完成后等待3秒再开始下一轮
                time.sleep(3)
            except Exception as e:
                print(f"语音交互出错: {str(e)}")
                # 出错后等待5秒再重试
                time.sleep(5)
    
    # 延迟1秒后启动循环语音交互线程
    QTimer.singleShot(1000, lambda: threading.Thread(target=continuous_voice_interaction, daemon=True).start())
    
    # 启动事件循环
    sys.exit(app.exec_())


    
=======

from pynput import keyboard
import threading
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import io
import time
import wave
import requests
import speech_recognition as sr
from tqdm import tqdm
import re
import sys
import random
import winsound
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, 
                            QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtWidgets import QSystemTrayIcon  # 添加到文件顶部的导入部分

# 合并所有导入，删除重复导入

class AudioRecorder:
    def __init__(self, rate=16000):
        """初始化录音器，设置采样率"""
        self.rate = rate
        self.recognizer = sr.Recognizer()
        self.recording = False
        self.audio_data = None
        self.stop_recording = threading.Event()
 
    def record_on_key(self):
        """按住空格键录音的方法"""
        self.stop_recording.clear()
        print("请按住空格键开始录音，松开结束...", flush=True)
        
        # 创建并启动键盘监听线程
        keyboard_thread = threading.Thread(target=self._keyboard_listener)
        keyboard_thread.daemon = True
        keyboard_thread.start()
        
        # 等待录音开始
        while not self.recording and not self.stop_recording.is_set():
            time.sleep(0.1)
        
        # 如果用户取消了录音
        if self.stop_recording.is_set():
            return None
            
        # 开始录音
        with sr.Microphone(sample_rate=self.rate) as source:
            print("正在录音中...", flush=True)
            try:
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)
                self.audio_data = audio.get_wav_data()
                return io.BytesIO(self.audio_data)
            except Exception as e:
                print(f"录音出错: {str(e)}")
                return None
    
    def save_wav(self, audio_data, filename="temp_output.wav"):
        """将音频数据保存为WAV文件"""
        audio_data.seek(0)
        with wave.open(filename, 'wb') as wav_file:
            nchannels = 1
            sampwidth = 2  # 16-bit audio
            framerate = self.rate  # 采样率
            comptype = "NONE"
            compname = "not compressed"
            audio_frames = audio_data.read()
 
            wav_file.setnchannels(nchannels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            wav_file.setcomptype(comptype, compname)
            wav_file.writeframes(audio_frames)
        audio_data.seek(0)  # 重置指针位置，以便后续使用
    
    def _keyboard_listener(self):
        """键盘监听线程"""
        def on_press(key):
            try:
                if key == keyboard.Key.space and not self.recording:
                    self.recording = True
                    print("开始录音...")
            except:
                pass
                
        def on_release(key):
            try:
                if key == keyboard.Key.space and self.recording:
                    self.recording = False
                    print("录音结束")
                    return False  # 停止监听
                elif key == keyboard.Key.esc:
                    self.stop_recording.set()
                    print("已取消录音")
                    return False  # 停止监听
            except:
                pass
                
        # 启动键盘监听
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
 
    def run(self):
        """运行录音功能并保存音频文件"""
        audio_data = self.record_on_key()
        if audio_data:
            self.save_wav(audio_data, "temp_output.wav")
        return audio_data
 
class SenseVoice:
    def __init__(self, api_url, emo=False):
        """初始化语音识别接口，设置API URL和情感识别开关"""
        self.api_url = api_url
        self.emo = emo
 
    def _extract_second_bracket_content(self, raw_text):
        """提取文本中第二对尖括号内的内容"""
        match = re.search(r'<[^<>]*><([^<>]*)>', raw_text)
        if match:
            return match.group(1)
        return None
 
    def _get_speech_text(self, audio_data):
        """将音频数据发送到API并获取识别结果"""
        print('正在进行语音识别')
        files = [('files', audio_data)]
        data = {'keys': 'audio1', 'lang': 'auto'}
 
        response = requests.post(self.api_url, files=files, data=data)
        if response.status_code == 200:
            result_json = response.json()
            if "result" in result_json and len(result_json["result"]) > 0:
                if self.emo:
                    result = self._extract_second_bracket_content(result_json["result"][0]["raw_text"]) + "\n" + result_json["result"][0]["text"]
                    return result
                else:
                    return result_json["result"][0]["text"]
            else:
                return "未识别到有效的文本"
        else:
            return f"请求失败，状态码: {response.status_code}"
 
    def speech_to_text(self, audio_data):
        """调用API进行语音识别并返回结果"""
        return self._get_speech_text(audio_data)

def get_and_play_audio(text, speaker, pet_instance=None):
    """
    从TTS服务获取音频并使用winsound播放，同时在桌宠聊天框显示
    """
    # 构建URL
    base_url = "http://127.0.0.1:9880/"
    params = {
        "text": text,
        "speaker": speaker
    }
    
    try:
        # 发送GET请求
        print("正在请求音频...")
        response = requests.get(base_url, params=params)
        
        # 检查响应状态
        if response.status_code == 200:
            # 保存音频到临时文件
            filename = "temp_audio.wav"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # 使用winsound播放音频，同时显示文本
            print("正在播放音频...")
            # 在开始播放音频时才显示文本
            if pet_instance:
                pet_instance.update_chat(text)
            winsound.PlaySound(filename, winsound.SND_FILENAME)
            print("播放完成")
            
        else:
            print(f"请求失败，状态码: {response.status_code}")
    
    except Exception as e:
        print(f"发生错误: {str(e)}")

def process_voice_interaction(pet):
    """处理完整的语音交互流程"""
    try:
        # 设置桌宠为工作状态
        pet.is_working = True
        
        # 创建录音器并运行
        recorder = AudioRecorder()
        pet.update_chat("请按住空格键说话，松开结束...")
        audio_data = recorder.run()
        
        if audio_data:
            # 语音识别
            api_url = "http://127.0.0.1:8666/api/v1/asr"
            sense_voice = SenseVoice(api_url, emo=True)
            result1 = sense_voice.speech_to_text(audio_data)
            print("识别结果:", result1)
            
            # 过滤掉情感标签和其他标记，只保留实际识别内容
            clean_result = re.sub(r'\|[A-Z_]+\|', '', result1)
            
            # 显示语音识别结果到桌宠
            pet.update_chat(f"您说: {clean_result}")
            time.sleep(2)  # 给用户时间阅读识别结果
            
            # 大模型处理
            model = ChatOllama(
                api_key='ollama',
                base_url='http://127.0.0.1:11434/',
                model = 'gemma3:12b'
            )
            
            prompt_str = """
            #下面我会给你提供一句中文问题，请用中文回答问题！
            提问：{question}
            """
            
            prompt = ChatPromptTemplate.from_template(prompt_str)
            output = StrOutputParser()
            chain = prompt | model | output
            
            pet.update_chat("我正在思考...")
            # 执行构建的chain，获取结果
            result2 = chain.invoke({'question':result1})
            print(result2)
            
            # 语音合成并播放，同时在桌宠显示文本
            text = result2
            speaker = "leijun.pt"
            get_and_play_audio(text, speaker, pet)
        else:
            pet.update_chat("未检测到语音输入")
    finally:
        # 无论是否成功，都将桌宠设置回非工作状态
        pet.is_working = False

class StdoutRedirect(QObject):
    new_output = pyqtSignal(str)  # 新增信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.old_stdout = sys.stdout
        sys.stdout = self
        # 添加需要过滤的输出内容
        self.filter_texts = [
            "正在进行语音识别", 
            "正在请求音频", 
            "正在播放音频",
            "倒计时",
            "请在倒计时",
            "识别结果",  
            "播放完成",   
            "|EMO_",     
            "控制台",
            "请按住空格键",  # 添加新的过滤内容
            "开始录音",      # 添加新的过滤内容
            "录音结束",      # 添加新的过滤内容
            "正在录音中",    # 添加新的过滤内容
            "已取消录音"     # 添加新的过滤内容
        ]

    def write(self, text):
        # 过滤掉不需要显示在聊天框的内容
        if text.strip() and not any(filter_text in text for filter_text in self.filter_texts):
            self.new_output.emit(text.strip())  # 发射信号
        self.old_stdout.write(text)  # 保留控制台输出

    def flush(self):
        self.old_stdout.flush()

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        # 窗口初始化
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(300, 300)  # 放大窗口尺寸
        
        # 初始化组件
        self.init_pet_animation()
        self.init_chat_system()
        self.init_tray_icon()
        
        # 定时器配置 - 将间隔从8000毫秒改为300000毫秒（5分钟）
        self.action_timer = QTimer(self)
        self.action_timer.timeout.connect(self.random_behavior)
        self.action_timer.start(300000)  # 修改为5分钟
        
        # 是否处于工作模式（语音交互中）
        self.is_working = False
        
        # 位置初始化 - 移动到右下角
        screen_geometry = QApplication.desktop().availableGeometry()
        self.move(screen_geometry.width() - self.width(), 
                  screen_geometry.height() - self.height())
                  
        # 添加鼠标拖动相关变量
        self.dragging = False
        self.drag_position = QPoint()
        
    # 添加鼠标事件处理函数
    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            # 更新聊天框位置
            if not self.chat_label.isHidden():
                self.update_chat_position()
            event.accept()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件处理"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        
    def init_pet_animation(self):
        """宠物动画系统"""
        self.pet_label = QLabel(self)
        
        # 使用绝对路径加载GIF文件
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        gif_path = os.path.join(current_dir, "pet_idle.gif")
        
        # 检查文件是否存在
        if not os.path.exists(gif_path):
            print(f"错误: 找不到GIF文件: {gif_path}")
            # 如果找不到文件，可以使用一个备用图像或显示错误信息
            self.pet_label.setText("找不到图像文件")
            self.pet_label.setStyleSheet("background-color: white; color: red;")
            self.pet_label.setFixedSize(200, 200)
            return
            
        self.movie = QMovie(gif_path)
        
        # 添加错误处理
        if self.movie.isValid():
            # 设置等比例缩放
            self.pet_label.setScaledContents(True)
            self.pet_label.setFixedSize(200, 200)  # 放大尺寸到200x200
            self.movie.setScaledSize(QSize(200, 200))  # 设置GIF缩放尺寸
            
            self.pet_label.setMovie(self.movie)
            self.movie.start()
        else:
            print(f"错误: GIF文件无效: {gif_path}")
            self.pet_label.setText("图像文件无效")
            self.pet_label.setStyleSheet("background-color: white; color: red;")
            self.pet_label.setFixedSize(200, 200)

    def init_chat_system(self):
        """聊天系统"""
        self.chat_label = QLabel(self)
        self.chat_label.setStyleSheet("""
            background: rgb(255, 255, 255);  /* 使用完全不透明的白色 */
            border-radius: 6px;  /* 缩小圆角 */
            padding: 6px;  /* 缩小内边距 */
            color: #333;
            font: 11px 'Microsoft YaHei';  /* 增大字体从9px到11px */
            border: 1px solid #ccc;  /* 加深边框颜色 */
            min-width: 120px;  /* 缩小最小宽度 */
            max-width: 240px;  /* 缩小最大宽度 */
        """)
        self.chat_label.setWordWrap(True)
        self.chat_label.hide()
        
        # 调整初始位置（向右偏移）
        self.chat_label.move(self.width()-150, 10)
        
        # 聊天框定时器
        self.chat_timer = QTimer(self)
        self.chat_timer.timeout.connect(lambda: self.chat_label.hide())

        
    def update_chat(self, text):
        """更新聊天内容（同步位置调整）"""
        # 如果是大模型回答，显示时间更长
        is_model_response = not text.startswith("控制台:") and not text.startswith("请说话") and not text.startswith("我正在思考")
        
        # 每10个字符添加一个换行符，确保文本不会太宽，并居中显示
        lines = []
        current_line = ""
        for i, char in enumerate(text):
            current_line += char
            if (i + 1) % 10 == 0 or i == len(text) - 1:  # 从8改为10
                lines.append(current_line)
                current_line = ""
        
        # 将每行文本居中处理
        formatted_text = ""
        for line in lines:
            # 计算需要添加的空格数以居中显示
            padding = max(0, (10 - len(line)) // 2)  # 从8改为10
            centered_line = " " * padding + line
            formatted_text += centered_line + "\n"
        
        self.chat_label.setText(formatted_text)
        self.chat_label.adjustSize()
        
        # 自动调整聊天框宽度，根据文本内容
        max_line_length = max([len(line) for line in lines], default=0)
        ideal_width = max(120, min(240, max_line_length * 12))  # 根据最长行计算理想宽度
        
        self.chat_label.setFixedWidth(ideal_width)
        self.chat_label.adjustSize()  # 重新调整高度
        
        # 确保聊天框高度足够显示所有文本
        font_metrics = self.chat_label.fontMetrics()
        text_rect = font_metrics.boundingRect(
            0, 0, self.chat_label.width() - 12, 1000,
            Qt.TextWordWrap, formatted_text
        )
        # 增加聊天框的高度，给文本更多空间
        self.chat_label.setMinimumHeight(text_rect.height() + 30)
            
        # 向右偏移调整，但确保不会超出屏幕
        screen_width = QApplication.desktop().availableGeometry().width()
        # 将聊天框位置调整得更靠左一些
        x_pos = min(self.width() - self.chat_label.width() - 20,
                   screen_width - self.chat_label.width() - 10)
        
        self.chat_label.move(x_pos, 10)  # 保持垂直位置不变
        self.chat_label.show()
        
        # 根据文本类型和长度调整显示时间
        if is_model_response:
            display_time = max(10000, len(text) * 200)
        else:
            display_time = max(5000, len(text) * 150)
            
        self.chat_timer.start(display_time)

    def update_chat_position(self):
        """同步更新聊天框位置"""
        # 确保聊天框不会超出屏幕
        screen_width = QApplication.desktop().availableGeometry().width()
        # 将聊天框位置调整得更靠左一些，减小偏移量
        x_pos = min(self.width() - self.chat_label.width() - 20,  # 这里将+50改为-20，向左调整
                   screen_width - self.chat_label.width() - 10)
        
        self.chat_label.move(x_pos, 10)
    def init_tray_icon(self):
        """系统托盘功能"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon("icon.png"))
        
        tray_menu = QMenu()
        tray_menu.addAction(QAction("显示", self, triggered=self.show_normal))
        tray_menu.addAction(QAction("退出", self, triggered=self.clean_exit))
        self.tray.setContextMenu(tray_menu)
        
        self.tray.activated.connect(lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def show_normal(self):
        """显示窗口并激活"""
        self.show()
        self.activateWindow()
        
    def clean_exit(self):
        """安全退出"""
        self.tray.hide()
        QApplication.quit()


    def random_behavior(self):
        """随机行为"""
        # 如果处于工作模式，不执行随机行为
        if self.is_working:
            return
            
        behaviors = [
            ("pet_walk.gif", ["出去散步~", "今天天气不错"]),
            ("pet_eat.gif", ["想吃小鱼干", "肚子饿饿..."]),
            ("pet_sleep.gif", ["Zzzz...", "好困啊"]),
            ("pet_idle.gif", ["主人你好！", "要摸摸吗？"])
        ]
        gif, msgs = random.choice(behaviors)
        self.switch_animation(gif)
        self.update_chat(random.choice(msgs))
        
    def switch_animation(self, gif_path):
        """动画切换"""
        # 使用绝对路径加载GIF文件
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_gif_path = os.path.join(current_dir, gif_path)
        
        # 检查文件是否存在
        if not os.path.exists(full_gif_path):
            print(f"错误: 找不到GIF文件: {full_gif_path}")
            return
            
        self.movie.stop()
        self.movie.setFileName(full_gif_path)
        self.movie.setScaledSize(QSize(200, 200))  # 保持缩放尺寸一致
        self.movie.start()

# 在文件末尾的主程序部分进行修改

if __name__ == "__main__":
    # 首先创建并启动桌面桌宠应用
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = DesktopPet()
    pet.show()
    
    # 创建一个循环语音交互的函数
    def continuous_voice_interaction():
        while True:
            try:
                # 处理一次语音交互
                process_voice_interaction(pet)
                # 交互完成后等待3秒再开始下一轮
                time.sleep(3)
            except Exception as e:
                print(f"语音交互出错: {str(e)}")
                # 出错后等待5秒再重试
                time.sleep(5)
    
    # 延迟1秒后启动循环语音交互线程
    QTimer.singleShot(1000, lambda: threading.Thread(target=continuous_voice_interaction, daemon=True).start())
    
    # 启动事件循环
    sys.exit(app.exec_())


    
>>>>>>> 1f5a71b254b731076af0649f8dd8e0c228f9094a
