#!/usr/bin/env python3
"""
Mermaid Diagram Converter

This script extracts Mermaid diagrams from markdown files and converts them to PNG or SVG images.
It requires Node.js and the @mermaid-js/mermaid-cli package to be installed.

Installation:
    npm install -g @mermaid-js/mermaid-cli

Usage:
    python mermaid_converter.py input.md [--output-dir ./diagrams] [--format png]
"""

import os
import re
import argparse
import subprocess
import tempfile
from pathlib import Path

def extract_mermaid_diagrams(markdown_content):
    """Extract Mermaid diagrams from markdown content."""
    pattern = r"```mermaid\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, markdown_content)
    return matches

def save_diagram_to_temp_file(diagram_content):
    """Save diagram content to a temporary file."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mmd')
    temp_file.write(diagram_content.encode('utf-8'))
    temp_file.close()
    return temp_file.name

def convert_diagram(diagram_content, output_path, diagram_format='png'):
    """Convert a Mermaid diagram to the specified format using mermaid-cli."""
    temp_file_path = save_diagram_to_temp_file(diagram_content)
    
    try:
        # Use mmdc command-line tool from mermaid-cli
        cmd = [
            'mmdc',
            '-i', temp_file_path,
            '-o', output_path,
            '-b', 'transparent'
        ]
        
        # Run the command
        process = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        if process.returncode == 0:
            print(f"Successfully created {output_path}")
            return True
        else:
            print(f"Error creating {output_path}")
            print(f"stderr: {process.stderr.decode('utf-8')}")
            return False
    
    except subprocess.CalledProcessError as e:
        print(f"Error executing mmdc: {e}")
        print(f"stderr: {e.stderr.decode('utf-8') if e.stderr else ''}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def process_markdown_file(input_file, output_dir, diagram_format='png'):
    """Process a markdown file, extracting and converting all Mermaid diagrams."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read markdown content
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Extract diagrams
    diagrams = extract_mermaid_diagrams(content)
    
    if not diagrams:
        print(f"No Mermaid diagrams found in {input_file}")
        return []
    
    # Convert each diagram
    output_files = []
    base_filename = os.path.splitext(os.path.basename(input_file))[0]
    
    for i, diagram in enumerate(diagrams):
        output_filename = f"{base_filename}_diagram_{i+1}.{diagram_format}"
        output_path = os.path.join(output_dir, output_filename)
        
        success = convert_diagram(diagram, output_path, diagram_format)
        if success:
            output_files.append(output_path)
    
    return output_files

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        subprocess.run(['mmdc', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        print("Error: mermaid-cli not found.")
        print("Please install it using: npm install -g @mermaid-js/mermaid-cli")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert Mermaid diagrams in markdown files to images.')
    parser.add_argument('input_file', help='Input markdown file containing Mermaid diagrams')
    parser.add_argument('--output-dir', default='./diagrams', help='Directory to save output images')
    parser.add_argument('--format', choices=['png', 'svg'], default='png', help='Output image format')
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Process the file
    output_files = process_markdown_file(args.input_file, args.output_dir, args.format)
    
    if output_files:
        print(f"\nSuccessfully converted {len(output_files)} diagrams:")
        for file in output_files:
            print(f"  - {file}")
    else:
        print("No diagrams were converted. Check if your markdown file contains valid Mermaid diagrams.")

if __name__ == "__main__":
    main() 