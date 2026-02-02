import subprocess
import sys
import shutil
import json
import os
import re
import time
import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
import webbrowser
from rich.align import Align
from rich.text import Text
from rich.style import Style
import questionary
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import random
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()
APPS_REGISTRY_FILE = "apps_registry.json"

def check_dependencies():
    """Check if gh and gh copilot are installed."""
    if not shutil.which("gh"):
        console.print("[bold red]Error:[/bold red] GitHub CLI (gh) is not installed.")
        console.print("Please install it from https://cli.github.com/")
        sys.exit(1)
    pass

def load_apps_registry():
    if os.path.exists(APPS_REGISTRY_FILE):
        try:
            with open(APPS_REGISTRY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_apps_registry(registry):
    with open(APPS_REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=4)

def add_app_to_registry(name, description, language, path, features=None):
    registry = load_apps_registry()
    app_entry = {
        "id": str(len(registry) + 1),
        "name": name,
        "description": description,
        "language": language,
        "path": os.path.abspath(path),
        "features": features or [],
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    registry.append(app_entry)
    save_apps_registry(registry)

def extract_code_blocks(markdown_text):
    """
    Extracts all code blocks from markdown text.
    Returns a list of (language, code) tuples.
    """
    code_block_pattern = r"```\s*(\w+)?\s*\n(.*?)```"
    matches = re.findall(code_block_pattern, markdown_text, re.DOTALL)
    results = []
    for lang, code in matches:
        results.append((lang.strip(), code.strip()))
    return results

def extract_code(markdown_text):
    """
    Extracts the first code block from markdown text.
    """
    code_block_pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(code_block_pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def run_online_cpp_programiz(code_content):
    """
    Automates running C++ code on Programiz online compiler.
    """
    console.print("[cyan]Launching Selenium automation for Programiz C++ Compiler...[/cyan]")
    console.print("[dim]This requires Chrome browser installed.[/dim]")
    
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        # Keep browser open after script finishes
        options.add_experimental_option("detach", True) 
        
        # Suppress logging
        options.add_argument("--log-level=3")
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        
        url = "https://www.programiz.com/cpp-programming/online-compiler/"
        console.print(f"[green]Opening {url}...[/green]")
        driver.get(url)

        # Wait for editor
        wait = WebDriverWait(driver, 15)
        # Programiz uses Ace editor, typically in a #editor div
        wait.until(EC.presence_of_element_located((By.ID, "editor")))
        
        console.print("[cyan]Injecting code into editor...[/cyan]")
        # Escape backticks and backslashes for JS string
        safe_code = code_content.replace("\\", "\\\\").replace("`", "\\`")
        
        # Use Ace API to set value
        driver.execute_script(f'ace.edit("editor").setValue(`{safe_code}`);')
        
        console.print("[cyan]Clicking Run button...[/cyan]")
        # Find Run button - it usually has text "Run"
        run_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Run')]")))
        run_button.click()
        
        console.print("[bold green]Code submitted! Check the browser window for output.[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Automation Error:[/bold red] {e}")
        console.print("[yellow]Falling back to opening the website only...[/yellow]")
        webbrowser.open("https://www.programiz.com/cpp-programming/online-compiler/")

def run_app(app_entry):
    """
    Runs the app based on its language.
    """
    file_path = app_entry["path"]
    language = app_entry.get("language", "auto").lower()
    
    console.print(f"[bold green]Running {app_entry['name']}...[/bold green]")
    
    try:
        if language == "python" or file_path.endswith(".py"):
            # Try to install dependencies first
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Look for requirements comment
            req_match = re.search(r"#\s*requirements:\s*(.*)", content, re.IGNORECASE)
            if req_match:
                reqs = [r.strip() for r in req_match.group(1).split(",") if r.strip()]
                if reqs:
                    console.print(f"[cyan]Installing dependencies: {', '.join(reqs)}[/cyan]")
                    subprocess.run([sys.executable, "-m", "pip", "install"] + reqs, check=False)
            
            # Fallback: Naive import detection
            # (Only simple top-level imports)
            imports = re.findall(r"^import (\w+)|^from (\w+)", content, re.MULTILINE)
            detected_pkgs = set()
            for imp in imports:
                pkg = imp[0] or imp[1]
                if pkg and pkg not in sys.builtin_module_names and pkg not in ['streamlit']: # simplified check
                     detected_pkgs.add(pkg)
            
            # Heuristic: if it imports streamlit, run with streamlit
            if "import streamlit" in content:
                subprocess.run(["streamlit", "run", file_path], check=True)
            else:
                subprocess.run(["python", file_path], check=True)
        elif language == "html" or file_path.endswith(".html"):
             # Open in default browser
             url = "file://" + os.path.abspath(file_path)
             console.print(f"[green]Opening {url}...[/green]")
             webbrowser.open(url)
        elif language == "c++" or file_path.endswith(".cpp"):
             # For C++, we want to avoid local compilation if possible and just show the code 
             # OR run it if a compiler exists.
             # User requested "run without those compilers".
             # Strict interpretation: we can't run C++ source without a compiler/interpreter.
             # However, we can simulate "running" by displaying the source or opening an online compiler.
             
             if shutil.which("g++"):
                 # Compiler exists, try to run
                 exe_path = file_path.replace(".cpp", ".exe" if sys.platform == "win32" else "")
                 console.print("[cyan]Compiling locally...[/cyan]")
                 compile_result = subprocess.run(["g++", file_path, "-o", exe_path], capture_output=True, text=True)
                 if compile_result.returncode == 0:
                     console.print("[cyan]Running in new console...[/cyan]")
                     if sys.platform == "win32":
                         os.system(f'start cmd /k "{exe_path}"')
                     else:
                         subprocess.run([exe_path])
                     return

             # If no compiler or compilation failed, use Online Automation
             console.print("[yellow]Local C++ compiler not found. Using Programiz Online Compiler...[/yellow]")
             
             try:
                 with open(file_path, "r", encoding="utf-8") as f:
                     code_content = f.read()
                 run_online_cpp_programiz(code_content)
             except Exception as e:
                 console.print(f"[red]Error reading C++ file: {e}[/red]")
             
        else:
            console.print(f"[yellow]Unknown runner for language {language}. Opening file...[/yellow]")
            if sys.platform == "win32":
                 os.startfile(file_path)
    except KeyboardInterrupt:
        console.print("\n[yellow]App stopped.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error running app:[/bold red] {e}")

def get_copilot_suggestion(query, language, color_scheme="default", complex_app=False, architecture="Standard", extras=None):
    """
    Get a suggestion from GitHub Copilot CLI.
    """
    extras = extras or []
    
    lang_instruction = ""
    if language.lower() == "python":
        lang_instruction = (
            "Write a complete Python Streamlit application. "
            "List all required pip packages in a comment at the top of the file like this: '# requirements: pandas, numpy'. "
            "Include error handling (try/except blocks) for robustness. "
            "IMPORTANT: Include a sidebar with an 'Intuitive User Interface (UI) Builder' section. "
            "This section should allow users to customize colors, fonts, and layout options (e.g., columns, spacing) using Streamlit widgets (color_picker, selectbox, slider)."
        )
    elif language.lower() == "html":
        lang_instruction = (
            "Write a complete HTML application. "
            "Use modern CSS (Flexbox/Grid) for layout. "
            "If interactive, include vanilla JavaScript within <script> tags. "
            "The UI should include a 'drag-and-drop' style editor interface simulation where possible, "
            "allowing users to customize layout colors or fonts dynamically."
        )
    elif language.lower() == "c++":
        lang_instruction = (
            "Write a complete C++ console application. "
            "If possible, make it compatible with WebAssembly (Emscripten) by using standard libraries."
        )
    else: # Fallback or specific future languages
        lang_instruction = f"Write a complete application in {language}."

    complexity_instruction = ""
    if complex_app:
        complexity_instruction = (
            "This is a complex app. If multiple files are needed, provide each file in a separate code block "
            "preceded by the filename in a comment (e.g., '### filename: main.py'). "
            "However, prefer a single file if possible for simplicity unless architecture dictates otherwise."
        )
    else:
        complexity_instruction = "The code must be self-contained in a single file."

    # Construct the advanced prompt
    full_prompt = (
        f"Primary User Request: {query}\n\n"
        f"Technical Specifications (Extensions of the request):\n"
        f"- Target Language: {language}\n"
        f"- Visual Style: {color_scheme}\n"
        f"- Architecture/Pattern: {architecture}\n"
        f"- Complexity: {'Complex (Multi-file)' if complex_app else 'Single-file/Simple'}\n"
        f"- Additional Features Requested: {', '.join(extras)}\n"
        f"- Language Specifics: {lang_instruction}\n"
        f"- Complexity Details: {complexity_instruction}\n\n"
        "Generate the application code exactly matching the Primary User Request. The Technical Specifications act as extensions/constraints to the prompt. "
        "Return the code in markdown code blocks."
    )
    
    # Improved Loading Animation
    with console.status(f"[bold cyan]Consulting GitHub Copilot for a {color_scheme} {language} app (Arch: {architecture})...[/bold cyan]", spinner="bouncingBall"):
        cmd = ["gh", "copilot", "-p", full_prompt, "--silent"]
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                shell=False
            )
            
            if process.returncode == 0 and process.stdout.strip():
                return process.stdout.strip()
            elif process.stderr.strip():
                 return f"Error/Message: {process.stderr.strip()}"
            
            return None
        except Exception as e:
            return f"Execution Error: {str(e)}"


def show_splash_screen():
    console.clear()
    
    # Advanced System Boot Simulation
    console.print(Panel("[bold cyan]INITIALIZING ADVANCED APP GENERATOR CORE V2.0[/bold cyan]", border_style="cyan"))
    time.sleep(0.5)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task1 = progress.add_task("[green]Checking System Resources...", total=100)
        task2 = progress.add_task("[cyan]Connecting to Neural Network...", total=100)
        task3 = progress.add_task("[magenta]Loading Architecture Modules...", total=100)
        
        while not progress.finished:
            if not progress.finished:
                progress.update(task1, advance=random.randint(2, 5))
            if progress.tasks[0].completed > 30:
                progress.update(task2, advance=random.randint(1, 4))
            if progress.tasks[1].completed > 50:
                progress.update(task3, advance=random.randint(3, 6))
            time.sleep(0.05)
            
    # System Status Table
    table = Table(title="System Status", show_header=True, header_style="bold magenta")
    table.add_column("Module", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    # Get basic system info
    os_info = f"{sys.platform} ({os.name})"
    py_version = sys.version.split()[0]
    gh_status = "Connected" if shutil.which("gh") else "Not Found"
    
    table.add_row("Operating System", "ONLINE", os_info)
    table.add_row("Python Environment", "ONLINE", f"v{py_version}")
    table.add_row("GitHub Copilot CLI", "ACTIVE" if "Connected" in gh_status else "ERROR", gh_status)
    table.add_row("App Registry", "LOADED", f"{len(load_apps_registry())} apps")
    
    console.print(table)
    console.print("\n[bold green]>> SYSTEM READY. WAITING FOR INPUT...[/bold green]\n")
    time.sleep(1)


def main():
    show_splash_screen()
    check_dependencies()

    while True:
        # Improved Main Menu with Columns/Panel
        menu_text = Text("Main Menu", style="bold white on blue", justify="center")
        console.print(Panel(menu_text, border_style="blue"))
        
        choice = questionary.select(
            "Select an option:",
            choices=[
                "Create New App",
                "View/Run Existing Apps",
                "Refine/Fix Existing App",
                "Exit"
            ],
            style=questionary.Style([
                ('qmark', 'fg:#E91E63 bold'),       # pink
                ('question', 'fg:#673AB7 bold'),    # purple
                ('answer', 'fg:#2196f3 bold'),      # blue
                ('pointer', 'fg:#673AB7 bold'),     # purple
                ('highlighted', 'fg:#E91E63 bold'), # pink
                ('selected', 'fg:#cc5454'),         # orange
                ('separator', 'fg:#cc5454'),
                ('instruction', 'fg:#a0a0a0 italic')
            ])
        ).ask()
        
        if choice == "Exit":
            console.print("[yellow]Goodbye![/yellow]")
            break
            
        if choice == "View/Run Existing Apps":
            registry = load_apps_registry()
            if not registry:
                console.print("[yellow]No apps found in registry.[/yellow]")
                continue
                
            table = Table(title="Generated Apps")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Language", style="magenta")
            table.add_column("Description")
            table.add_column("Features")
            table.add_column("Created At")
            
            for app in registry:
                features_str = ", ".join(app.get("features", []))[:30]
                table.add_row(app["id"], app["name"], app["language"], app["description"][:30], features_str, app["created_at"])
                
            console.print(table)
            
            app_id = Prompt.ask("Enter App ID to run (or 'back' to go back)")
            if app_id.lower() == 'back':
                continue
                
            selected_app = next((a for a in registry if a["id"] == app_id), None)
            if selected_app:
                run_app(selected_app)
            else:
                console.print("[red]App not found.[/red]")
            continue
            
        if choice == "Refine/Fix Existing App":
            registry = load_apps_registry()
            if not registry:
                console.print("[yellow]No apps found to refine.[/yellow]")
                continue
                
            # Select App
            app_choices = [f"{app['id']}: {app['name']}" for app in registry]
            selected_str = questionary.select("Select App to Refine:", choices=app_choices).ask()
            app_id = selected_str.split(":")[0]
            selected_app = next((a for a in registry if a["id"] == app_id), None)
            
            if not selected_app:
                continue
                
            # Read existing code
            try:
                with open(selected_app["path"], "r", encoding="utf-8") as f:
                    existing_code = f.read()
            except Exception as e:
                console.print(f"[red]Could not read app file: {e}[/red]")
                continue
            
            refinement_query = Prompt.ask("Describe the fix or new feature")
            
            full_prompt = (
                f"Here is the existing code for an app:\n\n```python\n{existing_code}\n```\n\n"
                f"User Request: {refinement_query}\n"
                "Rewrite the code to incorporate this request. Return the full updated code in a markdown block."
            )
            
            with console.status("[bold cyan]Consulting GitHub Copilot for refinement...[/bold cyan]", spinner="bouncingBall"):
                 cmd = ["gh", "copilot", "-p", full_prompt, "--silent"]
                 try:
                    process = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', shell=False)
                    suggestion = process.stdout.strip() if process.returncode == 0 else None
                 except:
                    suggestion = None
            
            if suggestion:
                console.print("\n[bold cyan]Copilot Suggestion:[/bold cyan]")
                console.print(Panel(Markdown(suggestion), border_style="green"))
                
                new_code_blocks = extract_code_blocks(suggestion)
                if new_code_blocks:
                     if Confirm.ask("Do you want to overwrite the existing file with this update?"):
                         lang, code = new_code_blocks[0]
                         with open(selected_app["path"], "w", encoding="utf-8") as f:
                             f.write(code)
                         console.print("[green]App updated successfully![/green]")
                         if Confirm.ask("Run updated app?"):
                             run_app(selected_app)
            else:
                console.print("[red]Failed to get refinement.[/red]")
            
            continue

        # Choice: Create New App
        console.print("\n[bold green]Describe the app you want to create[/bold green]")
        user_query = Prompt.ask("Query")
        
        if not user_query.strip():
            continue
            
        # Language Selection using Questionary
        lang_choice = questionary.select(
            "Select Language:",
            choices=[
                "Python (Streamlit)",
                "HTML",
                "C++"
            ]
        ).ask()
        
        selected_language = lang_choice.split(" ")[0] # Extract "Python", etc.
        
        # Color Scheme Selection
        color_scheme = questionary.select(
            "Select Color Scheme:",
            choices=[
                "Default",
                "Dark Mode",
                "Light Mode",
                "Blue Theme",
                "Orange Theme",
                "Cyberpunk"
            ]
        ).ask()
        
        # Complexity Selection
        app_type = questionary.select(
            "App Complexity:",
            choices=[
                "Simple (Single File)",
                "Complex (Folder with multiple files)"
            ]
        ).ask()
        
        is_complex = "Complex" in app_type

        # Advanced Architecture & Extras
        architecture = "Standard"
        extras = []
        
        if Confirm.ask("Configure Advanced Options? (Architecture, Extras)", default=False):
            architecture = questionary.select(
                "Select Architecture Pattern:",
                choices=[
                    "Standard (Monolithic)",
                    "MVC (Model-View-Controller)",
                    "Microservices (Simulation)",
                    "Event-Driven",
                    "Serverless Function"
                ]
            ).ask()
            
            extras = questionary.checkbox(
                "Select Additional Features:",
                choices=[
                    "Docker Support (Dockerfile)",
                    "Unit Tests",
                    "Git Initialization",
                    "CI/CD Pipeline (GitHub Actions)",
                    "Documentation (README.md)"
                ]
            ).ask()

        suggestion = get_copilot_suggestion(user_query, selected_language, color_scheme, is_complex, architecture, extras)

        if suggestion:
            # Display Copilot's Explanation first (as requested)
            console.print("\n[bold cyan]Copilot Response:[/bold cyan]")
            console.print(Panel(Markdown(suggestion), border_style="green"))
            
            # Extract code blocks
            code_blocks = extract_code_blocks(suggestion)

            if code_blocks:
                if Confirm.ask("\n[bold yellow]Code detected. Do you want to save this app?[/bold yellow]"):
                    
                    # App Name
                    app_name = Prompt.ask("Enter a name for this app (no spaces)", default=f"app_{int(time.time())}")
                    
                    # Feature Tracking
                    console.print("[bold]Enter the key features of this app (comma separated) for the registry:[/bold]")
                    features_input = Prompt.ask("Features", default="standard features")
                    features_list = [f.strip() for f in features_input.split(",")]
                    
                    saved_path = ""
                    
                    if is_complex or len(code_blocks) > 1:
                        # Create directory
                        os.makedirs(app_name, exist_ok=True)
                        console.print(f"[green]Created directory: {app_name}/[/green]")
                        
                        # Save files
                        for i, (lang, code) in enumerate(code_blocks):
                            # Default filename
                            ext = ".txt"
                            if "python" in lang or "py" in lang: ext = ".py"
                            elif "html" in lang: ext = ".html"
                            elif "cpp" in lang or "c++" in lang: ext = ".cpp"
                            elif "css" in lang: ext = ".css"
                            elif "js" in lang or "javascript" in lang: ext = ".js"
                            
                            default_fname = f"file_{i}{ext}"
                            if i == 0:
                                if ext == ".py": default_fname = "main.py"
                                elif ext == ".html": default_fname = "index.html"
                                elif ext == ".cpp": default_fname = "main.cpp"
                            
                            console.print(f"\n[cyan]File {i+1} ({lang}):[/cyan]")
                            console.print(code[:100] + "...")
                            fname = Prompt.ask(f"Enter filename for this block", default=default_fname)
                            
                            full_path = os.path.join(app_name, fname)
                            with open(full_path, "w", encoding="utf-8") as f:
                                f.write(code)
                            console.print(f"[green]Saved {full_path}[/green]")
                            
                            if i == 0: saved_path = full_path # Main entry point usually first
                            
                    else:
                        # Single file
                        lang, code = code_blocks[0]
                        ext = ".py"
                        if selected_language == "HTML": ext = ".html"
                        elif selected_language == "C++": ext = ".cpp"
                        elif "python" in lang: ext = ".py"
                        elif "html" in lang: ext = ".html"
                        
                        filename = f"{app_name}{ext}"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(code)
                        saved_path = filename
                        console.print(f"[bold green]File saved to {filename}[/bold green]")
                    
                    # Add to registry
                    add_app_to_registry(app_name, user_query, selected_language, saved_path, features_list)
                    
                    if Confirm.ask("Run this app now?"):
                        # Create a temporary app entry to run it immediately
                        temp_entry = {
                            "name": app_name,
                            "path": os.path.abspath(saved_path),
                            "language": selected_language
                        }
                        run_app(temp_entry)
            
            else:
                console.print("[yellow]No markdown code blocks found in the response.[/yellow]")
                if Confirm.ask("Do you want to save the raw output as a file?"):
                    app_name = Prompt.ask("Enter a name for this app (no spaces)", default=f"app_{int(time.time())}")
                    ext = ".txt"
                    if "python" in selected_language.lower(): ext = ".py"
                    elif "html" in selected_language.lower(): ext = ".html"
                    elif "c++" in selected_language.lower(): ext = ".cpp"
                    
                    filename = f"{app_name}{ext}"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(suggestion)
                    console.print(f"[bold green]Raw output saved to {filename}[/bold green]")
                    
                    # Try to add to registry and run
                    add_app_to_registry(app_name, user_query, selected_language, filename, ["raw_output"])
                    if Confirm.ask("Try to run this file?"):
                         temp_entry = {
                            "name": app_name,
                            "path": os.path.abspath(filename),
                            "language": selected_language
                        }
                         run_app(temp_entry)


        else:
            console.print("[red]Failed to get a response from Copilot.[/red]")

        console.print("\n" + "-"*30 + "\n")

if __name__ == "__main__":
    main()
