import speech_recognition as sr
import requests
import google.generativeai as genai
import pygame
import tempfile
import logging
import pyautogui
import psutil
import subprocess
import os
import shutil
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
from kivy.uix.scrollview import ScrollView
import platform
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.clock import Clock
from threading import Thread, Lock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from decouple import config

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Load environment variables
try:
    GEMINI_API_KEY = config("GEMINI_API_KEY")
    WEATHER_API_KEY = config("WEATHER_FORECAST_API_KEY")
    WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
except Exception as e:
    logging.error(f"Environment error: {e}")
    raise

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class PCAutomation:
    def open_application(self, app_name):
        """Automatically search & open an application without manually giving path"""
        try:
            system = platform.system()

            if system == "Windows":
                special_apps = {
                    "notepad": "notepad.exe",
                    "calculator": "calc.exe",
                    "task manager": "taskmgr.exe",
                    "paint":"mspaint.exe",
                    "media":"MediaPlayer.exe"
                }

                if app_name.lower() in special_apps:
                    subprocess.Popen(special_apps[app_name.lower()], shell=True)
                    return f"Opening {app_name} "

                # Check if the app exists in system PATH
                exe_path = shutil.which(app_name)
                if exe_path:
                    subprocess.Popen(app_name, shell=True)
                    return f"Opening {app_name} "

                # Try PowerShell
                process = subprocess.run(
                    ["powershell", "Get-Command", app_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if process.stdout:
                    subprocess.Popen(["powershell", "Start-Process", app_name], shell=True)
                    return f"Opening {app_name} "

                return f"❌ Application '{app_name}' not found!"

            elif system == "Darwin":  # macOS
                process = subprocess.run(["mdfind", app_name], stdout=subprocess.PIPE, text=True)
                if process.stdout:
                    subprocess.Popen(["open", "-a", app_name])
                    return f"Opening {app_name} "
                return f"❌ Application '{app_name}' not found!"

            elif system == "Linux":
                exe_path = shutil.which(app_name)
                if exe_path:
                    subprocess.Popen([app_name])
                    return f"Opening {app_name} "
                return f"❌ Application '{app_name}' not found!"

        except Exception as e:
            return f"❌ Error: {str(e)}"

    def close_application(self, app_name):
        """Close an application by name"""
        for proc in psutil.process_iter(['name']):
            if app_name.lower() in proc.info['name'].lower():
                proc.terminate()
                return f"Closed {app_name}"
        return f"Could not find {app_name} to close"

    def system_info(self):
        """Get basic system information"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)  # ✅ Real-time CPU usage
            memory = psutil.virtual_memory()
            battery = psutil.sensors_battery()

            battery_status = f"Battery: {battery.percent}% {'(Plugged in)' if battery.power_plugged else '(Not Charging)'}" if battery else "Battery info not available"

            return (f"🔹 **System Info:**\n"
                    f"OS: {platform.system()} {platform.release()}\n"
                    f"CPU Usage: {cpu_usage}%\n"
                    f"Memory: {memory.percent}% used\n"
                    f"{battery_status}")
        except Exception as e:
            return f"❌ System info error: {str(e)}"
        
    def take_screenshot(self, filename=None):
        """Take a screenshot"""
        if not filename:
            filename = f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
        
        try:
            screenshot = pyautogui.screenshot()
            screenshots_dir = os.path.join(os.path.expanduser("~"), "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            full_path = os.path.join(screenshots_dir, filename)
            screenshot.save(full_path)
            return f"Screenshot saved as {full_path}"
        except Exception as e:
            return f"Screenshot error: {str(e)}"

    def search_web(self, query):
        """Open default web browser and search"""
        try:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(search_url)
            return f"Searching web for: {query}"
        except Exception as e:
            return f"Web search error: {str(e)}"    

class VeronicaAI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', spacing=10, padding=20, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.speech_lock = Lock()
        self.pc_automation = PCAutomation()

        # Caching mechanisms
        self.audio_cache = {}
        self.gemini_cache = {}

        # UI Setup
        Window.size = (800, 500)
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        self._init_ui()

        # Audio Setup
        pygame.init()
        pygame.mixer.init()

        # Speech Recognition
        self.recognizer = sr.Recognizer()
        self.wake_phrase = "hey veronica"

        # Time Update
        Clock.schedule_interval(self._update_clock, 1)

        # Background Resource Loading
        Thread(target=self._load_resources, daemon=True).start()

    def _init_ui(self):
        """Initialize a simple user interface"""
        # Header with center alignment
        header_box = BoxLayout(size_hint=(1, 0.1), orientation='horizontal')
        self.header = Label(text="Veronica AI - Ready", font_size=24, halign='center')
        header_box.add_widget(Label(size_hint=(0.2, 1)))  # Spacer
        header_box.add_widget(self.header)
        header_box.add_widget(Label(size_hint=(0.2, 1)))  # Spacer
        self.add_widget(header_box)

        # Center content BoxLayout
        content_box = BoxLayout(orientation='vertical', size_hint=(0.8, 0.7), pos_hint={'center_x': 0.5})
        
        # Properly centered ScrollView
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        
        # Response display with proper bindings
        self.response_display = Label(
            text="Hello! How can I help?", 
            font_size=30, 
            halign='center', 
            valign='middle',
            size_hint_y=None,
            # text_size=(Window.width * 0.7, None)
        )
        self.response_display.bind(texture_size=self._adjust_label_height)
        self.scroll_view.add_widget(self.response_display)
        content_box.add_widget(self.scroll_view)
        
        self.add_widget(content_box)

        # Control Buttons centered at bottom
        btn_row = BoxLayout(size_hint=(0.4, 0.08), spacing=20, pos_hint={'center_x': 0.5})
        self.listen_btn = Button(text="Start Listening", on_press=self._toggle_listening, size_hint=(0.5, 1))
        self.quit_btn = Button(text="Exit", on_press=self.stop, size_hint=(0.5, 1))
        btn_row.add_widget(self.listen_btn)
        btn_row.add_widget(self.quit_btn)
        self.add_widget(btn_row)

    def _adjust_label_height(self, instance, value):
        """Adjust label height based on text size dynamically"""
        instance.height = max(instance.texture_size[1], 200)  # Minimum height to ensure visibility
        self.scroll_view.scroll_y = 1  # Scroll to top after content update

    def _toggle_listening(self, instance):
        """Toggle voice recognition"""
        if self.listen_btn.text == "Start Listening":
            self.listen_btn.text = "Stop Listening"
            Thread(target=self._voice_loop, daemon=True).start()
        else:
            self.listen_btn.text = "Start Listening"

    def _voice_loop(self):
        """Voice recognition loop"""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            while self.listen_btn.text == "Stop Listening":
                try:
                    audio = self.recognizer.listen(source, timeout=5)
                    text = self.recognizer.recognize_google(audio).lower()
                    self._process_command(text)
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    logging.error(f"Voice error: {e}")

    def _load_resources(self):
        """Simulated resource loading"""
        Clock.schedule_once(lambda dt: self._set_status("Initializing..."))
        Clock.schedule_once(lambda dt: self._set_status("Ready"), 2)

    def _update_clock(self, dt):
        """Update time on UI"""
        now = datetime.now()
        self.header.text = f"Veronica AI - {now.strftime('%H:%M:%S')}"

    def _get_voice_input(self):
        """Get voice input from user"""
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio).lower()
                return text
            except Exception as e:
                logging.error(f"Voice input error: {e}")
                return None

    def _handle_weather(self):
        """Fetch weather details"""
        self._speak("Which city should I check?")
        city = self._get_voice_input()
        if not city:
            return

        try:
            response = requests.get(WEATHER_API_URL, params={'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric'})
            data = response.json()
            report = f"Weather in {city}: {data['weather'][0]['description']}, {data['main']['temp']}°C"
            self._speak(report)
            self._update_display(report)
        except Exception as e:
            logging.error(f"Weather error: {e}")
            self._speak("Sorry, I couldn't fetch the weather.")

    def _cached_query(self, query):
        """
        Cached query method with timeout and fast response strategy
        
        Args:
            query (str): Input query to Gemini
        
        Returns:
            str: Response text or error message
        """
        # Check cache first for instant response
        if query in self.gemini_cache:
            return self.gemini_cache[query]
        
        try:
            # Use Gemini 2.0 Flash model - fastest available
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Optimized generation config for speed
            generation_config = {
                'max_output_tokens': 250,  # Reduced to increase speed
                'temperature': 0.5,  # More deterministic
            }
            
            # Generate content with quick timeout strategy
            response = model.generate_content(
                query, 
                generation_config=generation_config
            )
            
            # Extract and cache response
            response_text = response.text.strip()
            self.gemini_cache[query] = response_text
            
            return response_text
        
        except Exception as e:
            error_msg = f"Quick query error: {str(e)}"
            logging.error(error_msg)
            return error_msg
    
    def _ask_gemini(self, query, timeout=3):
        """
        Asynchronous Gemini query with timeout
        
        Args:
            query (str): Input query
            timeout (int): Maximum wait time in seconds
        """
        try:
            # Submit query to executor with timeout
            future = self.executor.submit(self._cached_query, query)
            
            # Wait for response with timeout
            response = future.result(timeout=timeout)
            
            # Process and display response
            self._speak(response)
            self._update_display(response)
        
        except TimeoutError:
            error_msg = "Query timed out. Please try again."
            self._speak(error_msg)
            logging.warning("Gemini query timed out")
        except Exception as e:
            error_msg = f"Query processing error: {str(e)}"
            self._speak(error_msg)
            logging.error(error_msg)

    def _process_response(self, text):
        """Process Gemini response"""
        self._speak(text)
        self._update_display(text)

    def _process_command(self, command):
        """Enhanced command processing with PC automation"""
        self._set_status(f"Processing: {command[:30]}...")
        
        # PC Automation Commands
        pc_commands = {
            "open": self.pc_automation.open_application,
            "close": self.pc_automation.close_application,
            "volume up": lambda: self.pc_automation.adjust_volume("up"),
            "volume down": lambda: self.pc_automation.adjust_volume("down"),
            "mute": lambda: self.pc_automation.adjust_volume("mute"),
            "brightness up": lambda: self.pc_automation.adjust_brightness("up"),
            "brightness down": lambda: self.pc_automation.adjust_brightness("down"),
            "take screenshot": self.pc_automation.take_screenshot,
            "system info": self.pc_automation.system_info
        }

        # Check for PC automation commands
        for trigger, action in pc_commands.items():
            if trigger in command.lower():
                response = action(command.replace(trigger, '').strip() if trigger not in ["take screenshot", "system info"] else None)
                self._speak(response)
                self._update_display(response)
                return

        # Web search and Gemini AI fallback
        if "search web" in command.lower():
            query = command.lower().replace("search web", '').strip()
            response = self.pc_automation.search_web(query)
            self._speak(response)
            self._update_display(response)
        elif "lock the computer" in command:
            os.system("rundll32.exe user32.dll,LockWorkStation")
            self._speak("Computer is locked.", lang='en')
        elif "weather" in command.lower():
            self._handle_weather()
        else:
            self._ask_gemini(command)

    def _speak(self, text):
        """Text-to-speech with caching"""
        with self.speech_lock:
            if not text.strip():
                return
            
            cache_key = hash(text)
            if cache_key in self.audio_cache:
                play(self.audio_cache[cache_key])
                return

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                    gTTS(text=text, lang='en').save(f.name)
                    audio = AudioSegment.from_mp3(f.name)
                    self.audio_cache[cache_key] = audio
                    play(audio)
            except Exception as e:
                logging.error(f"Speech error: {e}")

    def _update_display(self, text):
        """Thread-based update for response display"""
        def update_text():
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: setattr(self.response_display, 'text', text))

            # Auto-adjust font size based on content
            font_size = min(30, max(16, int(600 / max(1, len(text) / 20))))
            Clock.schedule_once(lambda dt: setattr(self.response_display, 'font_size', font_size))

        # Start background thread
        threading.Thread(target=update_text, daemon=True).start()

    def _make_scrollable(self):
        """This method is no longer needed as we already use ScrollView from the beginning"""
        pass

    def _set_status(self, text):
        """Update status message"""
        Clock.schedule_once(lambda dt: setattr(self.header, 'text', f"Veronica AI - {text}"))

    def stop(self, instance=None):
        """Exit the application"""
        pygame.quit()
        App.get_running_app().stop()

class VeronicaApp(App):
    def build(self):
        return VeronicaAI()

if __name__ == "__main__":
    try:
        VeronicaApp().run()
    except Exception as e:
        logging.critical(f"Fatal error: {e}")