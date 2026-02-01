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
from rich.text import Text
from rich.style import Style

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

def add_app_to_registry(name, description, language, path):
    registry = load_apps_registry()
    app_entry = {
        "id": str(len(registry) + 1),
        "name": name,
        "description": description,
        "language": language,
        "path": os.path.abspath(path),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    registry.append(app_entry)
    save_apps_registry(registry)

def extract_code(markdown_text):
    """
    Extracts the first code block from markdown text.
    """
    code_block_pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(code_block_pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def run_app(app_entry):
    """
    Runs the app based on its language.
    """
    file_path = app_entry["path"]
    language = app_entry.get("language", "auto").lower()
    
    console.print(f"[bold green]Running {app_entry['name']}...[/bold green]")
    
    try:
        if language == "python" or file_path.endswith(".py"):
             # Heuristic: if it imports streamlit, run with streamlit
             with open(file_path, "r", encoding="utf-8") as f:
                 content = f.read()
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
             # Compile and run
             if not shutil.which("g++"):
                 console.print("[bold red]Error:[/bold red] g++ compiler not found. Please install MinGW or similar to run C++ code.")
                 return

             exe_path = file_path.replace(".cpp", ".exe" if sys.platform == "win32" else "")
             console.print("[cyan]Compiling...[/cyan]")
             
             compile_result = subprocess.run(["g++", file_path, "-o", exe_path], capture_output=True, text=True)
             
             if compile_result.returncode != 0:
                 console.print("[bold red]Compilation Failed:[/bold red]")
                 console.print(compile_result.stderr)
                 return

             console.print("[cyan]Running in new console...[/cyan]")
             
             if sys.platform == "win32":
                 os.system(f'start cmd /k "{exe_path}"')
             else:
                 # Linux/Mac
                 subprocess.run([exe_path])
        else:
            console.print(f"[yellow]Unknown runner for language {language}. Opening file...[/yellow]")
            if sys.platform == "win32":
                 os.startfile(file_path)
    except KeyboardInterrupt:
        console.print("\n[yellow]App stopped.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error running app:[/bold red] {e}")

def get_copilot_suggestion(query, language):
    """
    Get a suggestion from GitHub Copilot CLI.
    """
    lang_instruction = ""
    if language.lower() == "python":
        lang_instruction = "Write a complete, single-file Python Streamlit application."
    elif language.lower() == "html":
        lang_instruction = "Write a complete, single-file HTML application (with embedded CSS/JS if needed)."
    elif language.lower() == "c++":
        lang_instruction = "Write a complete, single-file C++ console application."
    else: # Auto
        lang_instruction = "Write a complete, single-file application in the most suitable language (Python Streamlit, HTML, or C++)."

    full_prompt = (
        f"{lang_instruction} Request: {query}. "
        "The code must be self-contained. "
        "Return the code in a single markdown code block."
    )
    
    cmd = ["gh", "copilot", "-p", full_prompt, "--silent"]
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=True
        )
        
        if process.returncode == 0 and process.stdout.strip():
            return process.stdout.strip()
        elif process.stderr.strip():
             return f"Error/Message: {process.stderr.strip()}"
        
        return None
    except Exception as e:
        return f"Execution Error: {str(e)}"

def show_splash_screen():
    
    title = Text("Github Copilot CLI App Generator", style="bold blue")
    credits = Text("\nMade with GitHub Copilot CLI\nin cooperation with\nLegendsDaD and Amit Manna 99", style="dim", justify="center")
    credits.stylize("magenta", 48, 58) # LegendsDaD
    credits.stylize("cyan", 63) # Amit Manna 99

    panel = Panel(
        Text.assemble(title, "\n", credits, justify="center"),
        border_style="blue",
        padding=(1, 2)
    )
    
    # Dynamic animation effect
    colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
    with Live(panel, refresh_per_second=10) as live:
        for i in range(20): 
            # Cycle border color
            panel.border_style = colors[i % len(colors)]
            
            # Cycle title color
            title.style = Style(color=colors[(i + 1) % len(colors)], bold=True)
            panel.renderable = Text.assemble(title, "\n", credits, justify="center")
            
            live.update(panel)
            time.sleep(0.1)
            
    console.clear()
    console.print(panel)

def main():
    show_splash_screen()
    check_dependencies()

    while True:
        console.print("\n[bold]Main Menu[/bold]")
        console.print("1. Create New App")
        console.print("2. View/Run Existing Apps")
        console.print("3. Exit")
        
        choice = Prompt.ask("Select an option", choices=["1", "2", "3"], default="1")
        
        if choice == "3":
            console.print("[yellow]Goodbye![/yellow]")
            break
            
        if choice == "2":
            registry = load_apps_registry()
            if not registry:
                console.print("[yellow]No apps found in registry.[/yellow]")
                continue
                
            table = Table(title="Generated Apps")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Language", style="magenta")
            table.add_column("Description")
            table.add_column("Created At")
            
            for app in registry:
                table.add_row(app["id"], app["name"], app["language"], app["description"][:50], app["created_at"])
                
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

        # Choice 1: Create New App
        console.print("\n[bold green]Describe the app you want to create[/bold green]")
        user_query = Prompt.ask("Query")
        
        if not user_query.strip():
            continue
            
        # Language Selection
        console.print("\n[bold]Select Language:[/bold]")
        console.print("1. Python (Streamlit)")
        console.print("2. HTML")
        console.print("3. C++")
        console.print("4. Auto (Suggested)")
        
        lang_choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="4")
        lang_map = {"1": "Python", "2": "HTML", "3": "C++", "4": "Auto"}
        selected_language = lang_map[lang_choice]

        with console.status("[bold cyan]Consulting GitHub Copilot...[/bold cyan]", spinner="dots"):
            suggestion = get_copilot_suggestion(user_query, selected_language)

        if suggestion:
            extracted_code = extract_code(suggestion)
            
            console.print("\n[bold cyan]Copilot Response:[/bold cyan]")
            console.print(Panel(Markdown(suggestion), border_style="green"))

            if extracted_code:
                if Confirm.ask("\n[bold yellow]Code detected. Do you want to save and run this app?[/bold yellow]"):
                    # Determine extension
                    ext = ".py"
                    if selected_language == "HTML": ext = ".html"
                    elif selected_language == "C++": ext = ".cpp"
                    elif selected_language == "Auto":
                        if "def " in extracted_code or "import " in extracted_code: ext = ".py"
                        elif "<html>" in extracted_code.lower(): ext = ".html"
                        elif "#include" in extracted_code: ext = ".cpp"
                    
                    default_filename = f"generated_app_{int(time.time())}{ext}"
                    filename = Prompt.ask("Enter filename to save", default=default_filename)
                    
                    # Force correct extension if user didn't provide one or provided wrong one
                    if not filename.endswith(ext):
                        # If it has no extension, append it
                        if "." not in filename:
                             filename += ext
                        # If it has a different extension but we are sure about the type, warn or append
                        # For now, let's trust the user if they typed an extension, 
                        # but if they typed a name like 'myapp' we ensure it is 'myapp.py'
                    
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(extracted_code)
                        console.print(f"[bold green]File saved to {filename}[/bold green]")
                        
                        # Add to registry
                        add_app_to_registry(filename, user_query, selected_language, filename)
                        
                        if Confirm.ask("Run this app now?"):
                            # Create a temporary app entry to run it immediately
                            temp_entry = {
                                "name": filename,
                                "path": os.path.abspath(filename),
                                "language": selected_language
                            }
                            run_app(temp_entry)
                    except Exception as e:
                        console.print(f"[bold red]Error saving file:[/bold red] {e}")

        else:
            console.print("[red]Failed to get a response from Copilot.[/red]")

        console.print("\n" + "-"*30 + "\n")

if __name__ == "__main__":
    main()
