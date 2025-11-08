import os
import sys
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Ensure project root on path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from core.agent import DocumentAgent
from core.document_handler import DocumentHandler
from core.printer import PrinterManager
from core.utils import get_timestamp
from main import setup_logging, process_document_pipeline


ENV_KEYS = [
    # Provider & API keys
    "LLM_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "MODEL_NAME",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "GROQ_API_KEY",
    "GROQ_BASE_URL",
    # AI params
    "TEMPERATURE",
    "MAX_TOKENS",
    # WhatsApp/Twilio
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "WHATSAPP_NUMBER",
    "WEBHOOK_URL",
    # Printer
    "OUTPUT_FORMAT",
    "PRINTER_NAME",
    "USE_DEFAULT_PRINTER",
    "PRINT_QUALITY",
    "PAPER_SIZE",
    "DUPLEX_PRINTING",
    # Agent
    "AGENT_NAME",
    "PROCESSING_INSTRUCTIONS",
    "OUTPUT_LANGUAGE",
    "ACADEMIC_STYLE",
    "PRESERVE_FORMATTING",
    "MAX_SUGGESTIONS",
    # Agent behavior
    "AUTO_PRINT",
    "REQUIRE_CONFIRMATION",
    # Document settings
    "SUPPORTED_FORMATS",
    "MAX_FILE_SIZE_MB",
    # App settings
    "LOG_LEVEL",
    "DEBUG_MODE",
]


def load_env(env_path: Path) -> dict:
    values = {}
    source = env_path if env_path.exists() else project_root / ".env.template"
    if source.exists():
        for line in source.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


def save_env(env_path: Path, values: dict) -> None:
    lines = []
    for k in ENV_KEYS:
        if k in values and values[k] is not None:
            lines.append(f"{k}={values[k]}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable frame using a Canvas + Scrollbar."""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Mouse wheel scrolling support (Windows/Mac) and Linux buttons
        self._mousewheel_bound = False

        def bind_mousewheel(_event=None):
            if not self._mousewheel_bound:
                # Windows & MacOS
                self.canvas.bind_all("<MouseWheel>", on_mousewheel)
                # Linux
                self.canvas.bind_all("<Button-4>", on_button4)
                self.canvas.bind_all("<Button-5>", on_button5)
                self._mousewheel_bound = True

        def unbind_mousewheel(_event=None):
            if self._mousewheel_bound:
                try:
                    self.canvas.unbind_all("<MouseWheel>")
                    self.canvas.unbind_all("<Button-4>")
                    self.canvas.unbind_all("<Button-5>")
                except Exception:
                    pass
                self._mousewheel_bound = False

        def on_mousewheel(event):
            try:
                # On Windows, event.delta is multiples of 120
                delta = int(-1 * (event.delta / 120))
                self.canvas.yview_scroll(delta, "units")
            except Exception:
                self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

        def on_button4(_event):
            self.canvas.yview_scroll(-1, "units")

        def on_button5(_event):
            self.canvas.yview_scroll(1, "units")

        # Bind when cursor enters the inner frame; unbind when it leaves
        self.inner.bind("<Enter>", bind_mousewheel)
        self.inner.bind("<Leave>", unbind_mousewheel)


class AgentUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Document Agent — UI")
        self.geometry("820x600")
        self.resizable(True, True)

        setup_logging()
        self.logger = logging.getLogger("AgentUI")

        self.env_path = project_root / ".env"
        self.env = load_env(self.env_path)

        # Variables
        self.llm_provider = tk.StringVar(value=self.env.get("LLM_PROVIDER", "mock"))
        self.openai_api_key = tk.StringVar(value=self.env.get("OPENAI_API_KEY", ""))
        self.openai_model = tk.StringVar(value=self.env.get("OPENAI_MODEL", "gpt-3.5-turbo"))
        self.anthropic_api_key = tk.StringVar(value=self.env.get("ANTHROPIC_API_KEY", ""))
        self.anthropic_model = tk.StringVar(value=self.env.get("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"))
        # Generic model for OpenAI-compatible providers
        self.model_name = tk.StringVar(value=self.env.get("MODEL_NAME", "openai/gpt-4o-mini"))
        # Additional providers
        self.openrouter_api_key = tk.StringVar(value=self.env.get("OPENROUTER_API_KEY", ""))
        self.openrouter_base_url = tk.StringVar(value=self.env.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
        self.deepseek_api_key = tk.StringVar(value=self.env.get("DEEPSEEK_API_KEY", ""))
        self.deepseek_base_url = tk.StringVar(value=self.env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
        self.groq_api_key = tk.StringVar(value=self.env.get("GROQ_API_KEY", ""))
        self.groq_base_url = tk.StringVar(value=self.env.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
        # AI params
        self.temperature = tk.StringVar(value=self.env.get("TEMPERATURE", "0.3"))
        self.max_tokens = tk.StringVar(value=self.env.get("MAX_TOKENS", "2000"))
        self.twilio_sid = tk.StringVar(value=self.env.get("TWILIO_ACCOUNT_SID", ""))
        self.twilio_token = tk.StringVar(value=self.env.get("TWILIO_AUTH_TOKEN", ""))
        self.whatsapp_number = tk.StringVar(value=self.env.get("WHATSAPP_NUMBER", "whatsapp:+14155238886"))
        self.webhook_url = tk.StringVar(value=self.env.get("WEBHOOK_URL", ""))
        self.output_format = tk.StringVar(value=self.env.get("OUTPUT_FORMAT", "docx"))
        self.printer_name = tk.StringVar(value=self.env.get("PRINTER_NAME", ""))
        self.use_default_printer = tk.BooleanVar(value=self.env.get("USE_DEFAULT_PRINTER", "true").lower() == "true")
        self.print_quality = tk.StringVar(value=self.env.get("PRINT_QUALITY", "normal"))
        self.paper_size = tk.StringVar(value=self.env.get("PAPER_SIZE", "A4"))
        self.duplex_printing = tk.BooleanVar(value=self.env.get("DUPLEX_PRINTING", "false").lower() == "true")
        # Agent behavior
        self.agent_name = tk.StringVar(value=self.env.get("AGENT_NAME", "AI Document Assistant"))
        self.processing_instructions = tk.StringVar(value=self.env.get("PROCESSING_INSTRUCTIONS", "Improve grammar, clarity, and formatting"))
        self.output_language = tk.StringVar(value=self.env.get("OUTPUT_LANGUAGE", "English"))
        self.academic_style = tk.BooleanVar(value=self.env.get("ACADEMIC_STYLE", "true").lower() == "true")
        self.preserve_formatting = tk.BooleanVar(value=self.env.get("PRESERVE_FORMATTING", "true").lower() == "true")
        self.max_suggestions = tk.StringVar(value=self.env.get("MAX_SUGGESTIONS", "5"))
        self.auto_print = tk.BooleanVar(value=self.env.get("AUTO_PRINT", "false").lower() == "true")
        self.require_confirmation = tk.BooleanVar(value=self.env.get("REQUIRE_CONFIRMATION", "true").lower() == "true")
        # Document settings
        self.supported_formats = tk.StringVar(value=self.env.get("SUPPORTED_FORMATS", ".docx,.pdf,.txt"))
        self.max_file_size_mb = tk.StringVar(value=self.env.get("MAX_FILE_SIZE_MB", "25"))
        # App settings
        self.log_level = tk.StringVar(value=self.env.get("LOG_LEVEL", "INFO"))
        self.debug_mode = tk.BooleanVar(value=self.env.get("DEBUG_MODE", "false").lower() == "true")

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tabs
        self.config_tab = ttk.Frame(notebook)
        self.test_tab = ttk.Frame(notebook)
        self.process_tab = ttk.Frame(notebook)

        notebook.add(self.config_tab, text="Config")
        notebook.add(self.test_tab, text="Test")
        notebook.add(self.process_tab, text="Process")

        self._build_config_tab()
        self._build_test_tab()
        self._build_process_tab()

    def _build_config_tab(self):
        # Make the tab expandable
        self.config_tab.rowconfigure(0, weight=1)
        self.config_tab.columnconfigure(0, weight=1)
        # Wrap content in a scrollable frame
        sf = ScrollableFrame(self.config_tab)
        sf.grid(row=0, column=0, sticky="nsew")
        frame = sf.inner

        # Provider section
        provider_box = ttk.LabelFrame(frame, text="Provider & API Keys")
        provider_box.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(provider_box, text="LLM Provider").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(provider_box, textvariable=self.llm_provider, values=["mock", "openai", "anthropic", "openrouter", "deepseek", "groq"], state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        # OpenAI
        ttk.Label(provider_box, text="OpenAI API Key").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.openai_api_key, width=52).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="OpenAI Model").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.openai_model).grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        # Anthropic
        ttk.Label(provider_box, text="Anthropic API Key").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.anthropic_api_key, width=52).grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="Anthropic Model").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.anthropic_model).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

        # OpenAI-compatible providers
        ttk.Label(provider_box, text="General Model (MODEL_NAME)").grid(row=5, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.model_name).grid(row=5, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="OpenRouter API Key").grid(row=6, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.openrouter_api_key, width=52).grid(row=6, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="OpenRouter Base URL").grid(row=7, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.openrouter_base_url).grid(row=7, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="DeepSeek API Key").grid(row=8, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.deepseek_api_key, width=52).grid(row=8, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="DeepSeek Base URL").grid(row=9, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.deepseek_base_url).grid(row=9, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="Groq API Key").grid(row=10, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.groq_api_key, width=52).grid(row=10, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(provider_box, text="Groq Base URL").grid(row=11, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(provider_box, textvariable=self.groq_base_url).grid(row=11, column=1, sticky="ew", padx=8, pady=6)

        provider_box.columnconfigure(1, weight=1)

        # AI parameters
        params_box = ttk.LabelFrame(frame, text="AI Parameters")
        params_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(params_box, text="Temperature").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(params_box, textvariable=self.temperature).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(params_box, text="Max Tokens").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(params_box, textvariable=self.max_tokens).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        params_box.columnconfigure(1, weight=1)

        # WhatsApp / Twilio
        twilio_box = ttk.LabelFrame(frame, text="WhatsApp / Twilio")
        twilio_box.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(twilio_box, text="Twilio Account SID").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(twilio_box, textvariable=self.twilio_sid, width=52).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(twilio_box, text="Twilio Auth Token").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(twilio_box, textvariable=self.twilio_token, width=52, show="•").grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(twilio_box, text="WhatsApp Number (whatsapp:+...)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(twilio_box, textvariable=self.whatsapp_number).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(twilio_box, text="Webhook URL").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(twilio_box, textvariable=self.webhook_url).grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        twilio_box.columnconfigure(1, weight=1)

        # Printer
        printer_box = ttk.LabelFrame(frame, text="Printer")
        printer_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(printer_box, text="Printer Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(printer_box, textvariable=self.printer_name).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Checkbutton(printer_box, text="Use Default Printer", variable=self.use_default_printer).grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(printer_box, text="Print Quality").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(printer_box, textvariable=self.print_quality).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(printer_box, text="Paper Size").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(printer_box, textvariable=self.paper_size).grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(printer_box, text="Duplex Printing").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(printer_box, variable=self.duplex_printing, text="Enable").grid(row=4, column=1, sticky="w", padx=8, pady=6)
        printer_box.columnconfigure(1, weight=1)

        # Agent behavior
        agent_box = ttk.LabelFrame(frame, text="Agent Behavior")
        agent_box.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(agent_box, text="Agent Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(agent_box, textvariable=self.agent_name).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(agent_box, text="Processing Instructions").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(agent_box, textvariable=self.processing_instructions).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(agent_box, text="Output Language").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(agent_box, textvariable=self.output_language).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Checkbutton(agent_box, text="Academic Style", variable=self.academic_style).grid(row=3, column=1, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(agent_box, text="Preserve Formatting", variable=self.preserve_formatting).grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(agent_box, text="Max Suggestions").grid(row=5, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(agent_box, textvariable=self.max_suggestions).grid(row=5, column=1, sticky="ew", padx=8, pady=6)
        ttk.Checkbutton(agent_box, text="Auto Print if allowed", variable=self.auto_print).grid(row=6, column=1, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(agent_box, text="Require confirmation before printing", variable=self.require_confirmation).grid(row=7, column=1, sticky="w", padx=8, pady=6)
        agent_box.columnconfigure(1, weight=1)

        # Document settings
        doc_box = ttk.LabelFrame(frame, text="Document Settings")
        doc_box.grid(row=5, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(doc_box, text="Output Format").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(doc_box, textvariable=self.output_format, values=["docx", "txt", "pdf"], state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(doc_box, text="Supported Formats (.docx,.pdf,.txt)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(doc_box, textvariable=self.supported_formats).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Label(doc_box, text="Max File Size (MB)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(doc_box, textvariable=self.max_file_size_mb).grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        doc_box.columnconfigure(1, weight=1)

        # App settings
        app_box = ttk.LabelFrame(frame, text="App Settings")
        app_box.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        ttk.Label(app_box, text="Log Level (INFO/DEBUG)").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(app_box, textvariable=self.log_level).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Checkbutton(app_box, text="Debug Mode", variable=self.debug_mode).grid(row=1, column=1, sticky="w", padx=8, pady=6)
        app_box.columnconfigure(1, weight=1)

        # Save
        save_btn = ttk.Button(frame, text="Save .env", command=self.on_save_env)
        save_btn.grid(row=7, column=1, sticky="e", padx=8, pady=14)
        frame.columnconfigure(1, weight=1)

    def _build_test_tab(self):
        frame = self.test_tab

        ttk.Label(frame, text="Quick Tests").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.btn_test_llm = ttk.Button(frame, text="Test LLM", command=self.on_test_llm)
        self.btn_test_llm.grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.btn_list_printers = ttk.Button(frame, text="List Printers", command=self.on_list_printers)
        self.btn_list_printers.grid(row=2, column=0, sticky="w", padx=8, pady=6)

        # Loading indicator for tests
        self.test_status = ttk.Label(frame, text="")
        self.test_status.grid(row=1, column=1, sticky="w", padx=8, pady=6)
        self.test_progress = ttk.Progressbar(frame, mode="indeterminate", length=160)
        self.test_progress.grid(row=2, column=1, sticky="w", padx=8, pady=6)

        self.test_output = tk.Text(frame, height=22, wrap="word")
        self.test_output.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=8, pady=8)
        frame.rowconfigure(3, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_process_tab(self):
        frame = self.process_tab

        ttk.Label(frame, text="Selected file:").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.selected_file_var = tk.StringVar(value="")
        ttk.Entry(frame, textvariable=self.selected_file_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(frame, text="Choose…", command=self._on_choose_file).grid(row=0, column=2, sticky="w", padx=8, pady=8)
        ttk.Button(frame, text="Open file location", command=self._on_open_selected_location).grid(row=0, column=3, sticky="w", padx=8, pady=8)

        ttk.Label(frame, text="Save to folder:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        default_save_dir = str((project_root / "data" / "processed").resolve())
        self.save_dir_var = tk.StringVar(value=default_save_dir)
        ttk.Entry(frame, textvariable=self.save_dir_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(frame, text="Browse…", command=self._on_browse_save_dir).grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Button(frame, text="Open output folder", command=self._on_open_output_folder).grid(row=1, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(frame, text="Output format:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(frame, textvariable=self.output_format, values=["docx", "txt", "pdf"], state="readonly").grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        ttk.Checkbutton(frame, text="Review before printing", variable=self.require_confirmation).grid(row=2, column=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(frame, text="Auto print if allowed", variable=self.auto_print).grid(row=2, column=3, sticky="w", padx=8, pady=6)

        self.btn_process = ttk.Button(frame, text="Process", command=self._on_process_selected)
        self.btn_process.grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self.process_status = ttk.Label(frame, text="")
        self.process_status.grid(row=3, column=1, sticky="w", padx=8, pady=6)
        self.process_progress = ttk.Progressbar(frame, mode="indeterminate", length=160)
        self.process_progress.grid(row=3, column=2, sticky="w", padx=8, pady=6)

        self.process_output = tk.Text(frame, height=18, wrap="word")
        self.process_output.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=8, pady=8)
        frame.rowconfigure(4, weight=1)
        frame.columnconfigure(1, weight=1)

    def _reload_env(self):
        """Reload .env into process environment so Config sees latest values."""
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=self.env_path, override=True)
        except Exception:
            # Fallback: apply values manually
            values = load_env(self.env_path)
            for k, v in values.items():
                os.environ[k] = v

    def on_save_env(self):
        values = {
            # Provider & API keys
            "LLM_PROVIDER": self.llm_provider.get(),
            "OPENAI_API_KEY": self.openai_api_key.get(),
            "OPENAI_MODEL": self.openai_model.get(),
            "ANTHROPIC_API_KEY": self.anthropic_api_key.get(),
            "ANTHROPIC_MODEL": self.anthropic_model.get(),
            "MODEL_NAME": self.model_name.get(),
            "OPENROUTER_API_KEY": self.openrouter_api_key.get(),
            "OPENROUTER_BASE_URL": self.openrouter_base_url.get(),
            "DEEPSEEK_API_KEY": self.deepseek_api_key.get(),
            "DEEPSEEK_BASE_URL": self.deepseek_base_url.get(),
            "GROQ_API_KEY": self.groq_api_key.get(),
            "GROQ_BASE_URL": self.groq_base_url.get(),
            # AI params
            "TEMPERATURE": self.temperature.get(),
            "MAX_TOKENS": self.max_tokens.get(),
            # WhatsApp/Twilio
            "TWILIO_ACCOUNT_SID": self.twilio_sid.get(),
            "TWILIO_AUTH_TOKEN": self.twilio_token.get(),
            "WHATSAPP_NUMBER": self.whatsapp_number.get(),
            "WEBHOOK_URL": self.webhook_url.get(),
            # Printer
            "OUTPUT_FORMAT": self.output_format.get(),
            "PRINTER_NAME": self.printer_name.get(),
            "USE_DEFAULT_PRINTER": "true" if self.use_default_printer.get() else "false",
            "PRINT_QUALITY": self.print_quality.get(),
            "PAPER_SIZE": self.paper_size.get(),
            "DUPLEX_PRINTING": "true" if self.duplex_printing.get() else "false",
            # Agent
            "AGENT_NAME": self.agent_name.get(),
            "PROCESSING_INSTRUCTIONS": self.processing_instructions.get(),
            "OUTPUT_LANGUAGE": self.output_language.get(),
            "ACADEMIC_STYLE": "true" if self.academic_style.get() else "false",
            "PRESERVE_FORMATTING": "true" if self.preserve_formatting.get() else "false",
            "MAX_SUGGESTIONS": self.max_suggestions.get(),
            "AUTO_PRINT": "true" if self.auto_print.get() else "false",
            "REQUIRE_CONFIRMATION": "true" if self.require_confirmation.get() else "false",
            # Document settings
            "SUPPORTED_FORMATS": self.supported_formats.get(),
            "MAX_FILE_SIZE_MB": self.max_file_size_mb.get(),
            # App settings
            "LOG_LEVEL": self.log_level.get(),
            "DEBUG_MODE": "true" if self.debug_mode.get() else "false",
        }
        save_env(self.env_path, values)
        # Ensure runtime environment matches saved .env
        self._reload_env()
        self.logger.info(f"Saved .env to {self.env_path}")
        messagebox.showinfo("Saved", "Environment variables saved to .env")

    def on_test_llm(self):
        # Show loading indicator and run test in background to keep UI responsive
        self._start_test_loading()
        def worker():
            try:
                self._reload_env()
                config = Config()
                agent = DocumentAgent(config)
                result = agent.process_document_content("This is a short sample to improve.", "general")
                def finalize():
                    if result.get("success"):
                        msg = f"LLM OK — provider: {config.llm_provider}, model: {result.get('model_used', 'unknown')}\nSummary: {result.get('changes_summary', 'n/a')}"
                        self.test_output.insert("end", msg + "\n\n")
                        messagebox.showinfo("LLM Test", "LLM test succeeded.")
                    else:
                        self.test_output.insert("end", f"LLM Error: {result.get('error')}\n\n")
                        messagebox.showwarning("LLM Test", "LLM test failed.")
                    self._stop_test_loading()
                self.after(0, finalize)
            except Exception as e:
                def finalize_err():
                    self.test_output.insert("end", f"LLM Exception: {e}\n\n")
                    messagebox.showerror("LLM Test", str(e))
                    self._stop_test_loading()
                self.after(0, finalize_err)
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _on_browse_save_dir(self):
        directory = filedialog.askdirectory(title="Choose output folder")
        if directory:
            self.save_dir_var.set(directory)

    def _on_open_output_folder(self):
        try:
            target = Path(self.save_dir_var.get())
            if target.exists():
                os.startfile(str(target))
        except Exception as e:
            messagebox.showerror("Open Output Folder", str(e))

    def _on_choose_file(self):
        path = filedialog.askopenfilename(
            title="Select document",
            filetypes=[("Documents", "*.docx *.pdf *.txt"), ("All Files", "*.*")]
        )
        if path:
            self.selected_file_var.set(path)

    def _on_open_selected_location(self):
        try:
            p = Path(self.selected_file_var.get())
            if p.exists():
                os.startfile(str(p.parent))
        except Exception as e:
            messagebox.showerror("Open File Location", str(e))

    def on_list_printers(self):
        try:
            pm = PrinterManager(Config())
            info = pm.list_printers()
            default = info.get("default")
            lines = [f"Total: {info.get('count')}, Default: {default or 'None'}"]
            for p in info.get("printers", []):
                lines.append(f"- {p.get('name')} (default={p.get('is_default', False)})")
            output = "\n".join(lines)
            self.test_output.insert("end", output + "\n\n")
            messagebox.showinfo("Printers", "Listed printers in the Test output.")
        except Exception as e:
            self.test_output.insert("end", f"Printer Error: {e}\n\n")
            messagebox.showerror("Printers", str(e))

    def on_choose_and_process(self):
        """Legacy handler: choose and process immediately with defaults."""
        path = filedialog.askopenfilename(
            title="Select document",
            filetypes=[("Documents", "*.docx *.pdf *.txt"), ("All Files", "*.*")]
        )
        if not path:
            return
        self.selected_file_var.set(path)
        self._on_process_selected()

    def _on_process_selected(self):
        path = self.selected_file_var.get()
        if not path:
            messagebox.showwarning("Process", "Please choose a file first.")
            return

        self._start_process_loading()
        def worker():
            try:
                self._reload_env()
                config = Config()
                agent = DocumentAgent(config)
                doc_handler = DocumentHandler(config)
                printer_manager = PrinterManager(config)

                logger = logging.getLogger("AgentUI.Process")

                result = process_document_pipeline(
                    path, config, agent, doc_handler, printer_manager, logger,
                    save_dir=self.save_dir_var.get(),
                    review_before_print=self.require_confirmation.get(),
                    auto_print=self.auto_print.get(),
                    output_format_override=self.output_format.get()
                )

                processed_path = Path(result.get("processed_file", config.processed_dir))

                def finalize():
                    log_line = f"Processed '{Path(path).name}'. Saved to {processed_path}"
                    self.process_output.insert("end", log_line + "\n\n")
                    if self.require_confirmation.get():
                        if messagebox.askyesno("Review", "Open processed document for review?"):
                            try:
                                os.startfile(str(processed_path))
                            except Exception:
                                pass
                        if messagebox.askyesno("Print", "Print the processed document now?"):
                            pr = printer_manager.print_document(processed_path)
                            if pr.get("success"):
                                messagebox.showinfo("Printed", f"Sent to printer: {pr.get('printer')}")
                            else:
                                messagebox.showerror("Print Failed", pr.get("error"))
                    else:
                        if result.get("printed"):
                            messagebox.showinfo("Printed", "Document was printed automatically.")
                        else:
                            messagebox.showinfo("Saved", f"Document saved to {processed_path}")
                    self._stop_process_loading()
                self.after(0, finalize)
            except Exception as e:
                def finalize_err():
                    self.process_output.insert("end", f"Processing Error: {e}\n\n")
                    messagebox.showerror("Process File", str(e))
                    self._stop_process_loading()
                self.after(0, finalize_err)
        import threading
        threading.Thread(target=worker, daemon=True).start()

    # Loading helpers
    def _start_test_loading(self):
        try:
            self.test_status.configure(text="Testing…")
            self.test_progress.start(10)
            self.btn_test_llm.configure(state="disabled")
            self.btn_list_printers.configure(state="disabled")
        except Exception:
            pass

    def _stop_test_loading(self):
        try:
            self.test_progress.stop()
            self.test_status.configure(text="")
            self.btn_test_llm.configure(state="normal")
            self.btn_list_printers.configure(state="normal")
        except Exception:
            pass

    def _start_process_loading(self):
        try:
            self.process_status.configure(text="Processing…")
            self.process_progress.start(10)
            self.btn_process.configure(state="disabled")
        except Exception:
            pass

    def _stop_process_loading(self):
        try:
            self.process_progress.stop()
            self.process_status.configure(text="")
            self.btn_process.configure(state="normal")
        except Exception:
            pass


if __name__ == "__main__":
    app = AgentUI()
    app.mainloop()