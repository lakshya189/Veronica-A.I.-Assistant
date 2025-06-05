# Veronica AI Assistant

A voice-controlled AI assistant with PC automation capabilities, built with Python and Kivy.

## Features

- 🎙️ Voice recognition with wake word ("Hey Veronica")
- 💻 PC automation (open/close applications, system info)
- 🌦️ Weather information
- 🔍 Web search
- 🤖 AI-powered responses using Google's Gemini API
- 🎙️ Text-to-speech feedback
- 🖥️ Cross-platform support (Windows, macOS, Linux)

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Microphone (for voice commands)
- Internet connection (for AI and weather features)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/veronica-ai.git
   cd veronica-ai
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   WEATHER_FORECAST_API_KEY=your_openweather_api_key_here
   ```

## Usage

1. Run the application:
   ```bash
   python main.py
   ```

2. Click "Start Listening" or say "Hey Veronica"

3. Try commands like:
   - "Open notepad"
   - "What's the weather in [city]?"
   - "Search web for [query]"
   - "System info"
   - "Take screenshot"

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Google Gemini API for AI capabilities
- Kivy for the cross-platform GUI
- gTTS for text-to-speech functionality
