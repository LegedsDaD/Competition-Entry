import subprocess
import sys
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()

def check_dependencies():
    """Check if gh and gh copilot are installed."""
    if not shutil.which("gh"):
        console.print("[bold red]Error:[/bold red] GitHub CLI (gh) is not installed.")
        console.print("Please install it from https://cli.github.com/")
        sys.exit(1)
    
    # Check if copilot extension is installed
    # This is a loose check, as 'gh copilot' might be a built-in command in newer versions
    # or an extension. We'll assume if 'gh' exists we can try running it.
    pass

import re

def extract_code(markdown_text):
    """
    Extracts the first code block from markdown text.
    """
    code_block_pattern = r"```(?:\w+)?\n(.*?)```"
    match = re.search(code_block_pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def run_streamlit_app(file_path):
    """
    Runs the streamlit app.
    """
    console.print(f"[bold green]Running Streamlit App: {file_path}[/bold green]")
    try:
        # Using subprocess to run streamlit
        subprocess.run(["streamlit", "run", file_path], check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]App stopped.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error running app:[/bold red] {e}")

def get_copilot_suggestion(query):
    """
    Get a suggestion from GitHub Copilot CLI.
    """
    # The installed copilot CLI is an agentic version that uses -p for prompts
    # and does not have a 'suggest' subcommand.
    # We append instructions to get a full single-file app if possible.
    full_prompt = (
        f"Write a complete, single-file Python Streamlit application that fulfills this request: {query}. "
        "The code must be self-contained. "
        "Return the code in a single markdown code block."
    )
    
    cmd = ["gh", "copilot", "-p", full_prompt, "--silent"]
    
    try:
        # Attempt to capture output first
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

def main():
    console.print(Panel.fit(
        "[bold blue]AI App Generator[/bold blue]\n[dim]Powered by GitHub Copilot CLI & Rich[/dim]", 
        border_style="blue",
        padding=(1, 2)
    ))
    
    check_dependencies()

    while True:
        console.print("\n[bold green]Describe the app you want to create[/bold green]")
        console.print("[dim](e.g., 'app to manage and categorize files', 'data visualization dashboard')[/dim]")
        user_query = Prompt.ask("Query", default="exit")
        
        if user_query.lower() in ('exit', 'quit'):
            console.print("[yellow]Goodbye![/yellow]")
            break
            
        if not user_query.strip():
            continue

        with console.status("[bold cyan]Consulting GitHub Copilot...[/bold cyan]", spinner="dots"):
            suggestion = get_copilot_suggestion(user_query)

        if suggestion:
            # Check if there is code to extract
            extracted_code = extract_code(suggestion)
            
            console.print("\n[bold cyan]Copilot Response:[/bold cyan]")
            console.print(Panel(Markdown(suggestion), border_style="green"))

            if extracted_code:
                if Confirm.ask("\n[bold yellow]Code detected. Do you want to save and run this app?[/bold yellow]"):
                    filename = Prompt.ask("Enter filename to save", default="generated_app.py")
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(extracted_code)
                        console.print(f"[bold green]File saved to {filename}[/bold green]")
                        
                        if Confirm.ask("Run this app now?"):
                            run_streamlit_app(filename)
                    except Exception as e:
                        console.print(f"[bold red]Error saving file:[/bold red] {e}")

        else:
            # If capture failed (common with interactive CLI tools), run interactively
            console.print("\n[bold yellow]Launching interactive Copilot session...[/bold yellow]")
            # ... fallback ...
            try:
                subprocess.run(["gh", "copilot", "-i", user_query], shell=True)
            except Exception as e:
                console.print(f"[bold red]Failed to run interactive mode:[/bold red] {e}")

        console.print("\n" + "-"*30 + "\n")

if __name__ == "__main__":
    main()
