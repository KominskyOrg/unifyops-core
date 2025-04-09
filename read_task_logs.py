#!/usr/bin/env python3
"""
Terraform Task Log Reader

This script provides a way to read and monitor logs from Terraform background tasks.
It can be used to check the status of running tasks or debug errors in completed tasks.

Usage:
    python read_task_logs.py --type [environment|resource] --id [id] [--follow]
    
Example:
    python read_task_logs.py --type resource --id abc123
    python read_task_logs.py --type environment --id def456 --follow
"""

import os
import json
import argparse
import time
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional

# ANSI color codes for pretty printing
COLORS = {
    "RESET": "\033[0m",
    "INFO": "\033[92m",    # Green
    "DEBUG": "\033[94m",   # Blue
    "WARNING": "\033[93m", # Yellow
    "ERROR": "\033[91m",   # Red
    "CRITICAL": "\033[95m" # Purple
}

def parse_log_line(line: str) -> Dict[str, Any]:
    """Parse a JSON log line"""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"timestamp": datetime.now().isoformat(), "level": "ERROR", "message": line}

def format_log_entry(entry: Dict[str, Any]) -> str:
    """Format a log entry for display with colors"""
    level = entry.get("level", "INFO").upper()
    timestamp = entry.get("timestamp", datetime.now().isoformat())
    message = entry.get("message", "")
    
    # Format timestamp for readability
    try:
        dt = datetime.fromisoformat(timestamp)
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        pass
    
    # Get color for this log level
    color = COLORS.get(level, COLORS["RESET"])
    
    # Format the basic log line
    formatted = f"{timestamp} {color}[{level}]{COLORS['RESET']} {message}"
    
    # Add additional context if available
    context = {}
    for key, value in entry.items():
        if key not in ["timestamp", "level", "message", "service", "environment"]:
            context[key] = value
    
    if context:
        formatted += f"\n  Context: {json.dumps(context, indent=2)}"
    
    return formatted

def find_log_file(task_type: str, task_id: str) -> Optional[str]:
    """Find the log file for a specific task"""
    logs_dir = os.path.join(os.getcwd(), "logs", "background_tasks")
    pattern = os.path.join(logs_dir, f"{task_type}_{task_id}.log")
    
    # Look for exact match first
    if os.path.exists(pattern):
        return pattern
    
    # If not found, try with glob pattern
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    
    # If still not found, check all logs for partial match
    all_logs = glob.glob(os.path.join(logs_dir, "*.log"))
    for log_file in all_logs:
        if task_id in log_file:
            return log_file
    
    return None

def read_log_file(file_path: str, follow: bool = False):
    """Read a log file and print formatted entries"""
    if not os.path.exists(file_path):
        print(f"Log file not found: {file_path}")
        return
    
    # Initial read of the file
    with open(file_path, 'r') as f:
        for line in f:
            entry = parse_log_line(line.strip())
            print(format_log_entry(entry))
    
    # If follow mode is enabled, continue reading new lines
    if follow:
        print(f"\n{COLORS['INFO']}Watching for new log entries... (Ctrl+C to stop){COLORS['RESET']}\n")
        
        # Get current file size
        current_size = os.path.getsize(file_path)
        
        try:
            while True:
                if os.path.getsize(file_path) > current_size:
                    with open(file_path, 'r') as f:
                        f.seek(current_size)
                        for line in f:
                            entry = parse_log_line(line.strip())
                            print(format_log_entry(entry))
                    current_size = os.path.getsize(file_path)
                time.sleep(0.5)
        except KeyboardInterrupt:
            print(f"\n{COLORS['INFO']}Stopped watching log file.{COLORS['RESET']}")

def list_available_logs(task_type: Optional[str] = None):
    """List all available log files"""
    logs_dir = os.path.join(os.getcwd(), "logs", "background_tasks")
    
    if not os.path.exists(logs_dir):
        print(f"No logs directory found at: {logs_dir}")
        return
    
    pattern = f"{task_type}_*.log" if task_type else "*.log"
    log_files = glob.glob(os.path.join(logs_dir, pattern))
    
    if not log_files:
        print(f"No log files found" + (f" for type: {task_type}" if task_type else ""))
        return
    
    print(f"\n{COLORS['INFO']}Available log files:{COLORS['RESET']}")
    for log_file in sorted(log_files):
        file_name = os.path.basename(log_file)
        size = os.path.getsize(log_file)
        modified = os.path.getmtime(log_file)
        modified_str = datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to extract the task type and id from the filename
        parts = file_name.replace(".log", "").split("_")
        task_type = parts[0] if len(parts) > 0 else "unknown"
        task_id = "_".join(parts[1:]) if len(parts) > 1 else "unknown"
        
        # Format size nicely
        if size < 1024:
            size_str = f"{size} bytes"
        elif size < 1024 * 1024:
            size_str = f"{size/1024:.1f} KB"
        else:
            size_str = f"{size/(1024*1024):.1f} MB"
            
        print(f"  {file_name} - Type: {task_type}, ID: {task_id}, Size: {size_str}, Modified: {modified_str}")
    
    print()
    print(f"To view a log file, use: python {os.path.basename(__file__)} --type <type> --id <id>")
    print(f"Example: python {os.path.basename(__file__)} --type {task_type or 'resource'} --id <task_id>")

def main():
    """Main function to parse arguments and execute commands"""
    parser = argparse.ArgumentParser(description="Read and monitor Terraform task logs")
    parser.add_argument("--type", choices=["environment", "resource"], help="Type of task (environment or resource)")
    parser.add_argument("--id", help="Task ID to view logs for")
    parser.add_argument("--follow", "-f", action="store_true", help="Follow logs as they are updated")
    parser.add_argument("--list", "-l", action="store_true", help="List available log files")
    
    args = parser.parse_args()
    
    # If list flag is set, show available logs
    if args.list:
        list_available_logs(args.type)
        return
    
    # If no type or ID is provided, show available logs
    if not args.type or not args.id:
        print("Error: Both --type and --id are required to view logs.")
        list_available_logs()
        return
    
    # Find the log file
    log_file = find_log_file(args.type, args.id)
    if not log_file:
        print(f"Error: No log file found for {args.type} with ID {args.id}")
        list_available_logs(args.type)
        return
    
    # Read the log file
    read_log_file(log_file, args.follow)

if __name__ == "__main__":
    main() 