# AI Document Agent 🤖📄

An intelligent document processing agent that receives documents via WhatsApp, processes them using AI, and sends them to a printer. Perfect for students, offices, and anyone who needs automated document improvement and printing.

## ✨ Features

- 📱 **WhatsApp Integration**: Receive documents through WhatsApp messages using Twilio
- 🤖 **AI Processing**: Intelligent document editing and formatting using OpenAI/Anthropic LLMs
- 🖨️ **Automated Printing**: Direct integration with local printers
- 📄 **Multi-format Support**: Handle DOCX, PDF, TXT, and RTF files
- 🔧 **Configurable**: Flexible configuration for different use cases
- 📊 **Comprehensive Logging**: Detailed processing logs and error tracking
- 🧪 **Mock Testing**: Built-in mock LLM for testing without API costs
- 🔄 **Local Mode**: Process files directly from local directories

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Twilio account for WhatsApp integration (optional)
- OpenAI or Anthropic API key (optional for mock testing)
- Local printer setup (optional)

### Installation

1. **Clone and setup**:
```bash
git clone <repository-url>
cd PrintingAgent
```

2. **Automated setup**:
```bash
python setup.py
```
This will:
- Install all dependencies
- Create necessary directories
- Set up environment configuration
- Run basic tests

3. **Manual setup** (alternative):
```bash
pip install -r requirements.txt
cp .env.template .env
# Edit .env with your configuration
```

### Quick Test

Test the system with mock AI (no API keys required):

```bash
# Create a sample document
python create_sample.py

# Run in local mode with mock AI
python main.py --local
```

Place any `.docx` files in `data/incoming/` and watch them get processed!

## 📁 Project Structure

```
ai-doc-agent/
├── main.py                 # Entry point, runs the agent loop
├── config.py               # API keys, printer settings, etc.
├── requirements.txt        # Dependencies
│
├── core/                   # Core logic
│   ├── agent.py            # AI agent logic (LangChain/LLM)
│   ├── document_handler.py # Document parsing, editing, converting
│   ├── printer.py          # Printer integration
│   ├── whatsapp.py         # WhatsApp API integration
│   └── utils.py            # Helper functions
│
├── data/                   # Document storage
│   ├── incoming/           # Raw student uploads
│   ├── processed/          # AI-edited files
│   └── logs/               # Application logs
│
├── tests/                  # Unit tests
│   ├── test_doc_handler.py
│   └── test_agent.py
│
└── README.md               # This file
```

## Setup

### Prerequisites

- Python 3.8+
- Twilio account for WhatsApp integration
- OpenAI or Anthropic API key
- Local printer setup

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-doc-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables

Create a `.env` file with the following variables:

```env
# AI Configuration
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key
MODEL_NAME=gpt-3.5-turbo
MAX_TOKENS=2000
TEMPERATURE=0.7

# WhatsApp (Twilio) Configuration
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
WHATSAPP_NUMBER=whatsapp:+14155238886
WEBHOOK_URL=https://your-domain.com/webhook

# Printer Configuration
PRINTER_NAME=your_printer_name
USE_DEFAULT_PRINTER=true
PRINT_QUALITY=normal
PAPER_SIZE=A4
DUPLEX_PRINTING=false

# Processing Configuration
MAX_FILE_SIZE_MB=10
OUTPUT_FORMAT=pdf
AUTO_PRINT=false
REQUIRE_CONFIRMATION=true
MAX_PROCESSING_TIME=300
```

## Usage

1. Start the agent:
```bash
python main.py
```

2. Send a document via WhatsApp to your configured number

3. The agent will:
   - Receive and process the document
   - Apply AI-powered improvements
   - Send the processed document to the printer
   - Optionally send confirmation back via WhatsApp

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
flake8 .
```

### Type Checking

```bash
mypy .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

For support and questions, please [create an issue](link-to-issues) or contact [your-contact].