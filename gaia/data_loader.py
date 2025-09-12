#!/usr/bin/env python3
"""
GAIA Data Loader - Minimal JSONL parser for GAIA dataset
Loads tasks from GAIA JSONL format with exact field names and permanent file exclusion.
"""

import json
from typing import List, Dict


def load_tasks(path: str) -> List[Dict]:
    """
    Load tasks from GAIA JSONL format with exact field names
    
    Expected GAIA format fields:
    - task_id: Task identifier
    - Question: Task question/query (capital Q)
    - Final answer: Ground truth answer (space, capital F)
    - Level: Difficulty level (1, 2, or 3, capital L)
    - file_name: File attachment (lowercase with underscore)
    
    Args:
        path: Path to JSONL file
        
    Returns:
        List of normalized task dictionaries
    """
    tasks = []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at line {line_num}: {e}")
                    continue

                # Extract GAIA format fields with exact names
                task_id = obj.get('task_id')
                question = obj.get('Question')  # Capital Q
                final_answer = obj.get('Final answer')  # Space, capital F
                level = obj.get('Level')  # Capital L
                file_name = obj.get('file_name', '')  # lowercase with underscore

                # Skip malformed entries
                if not task_id or not question or level is None:
                    print(f"Warning: Missing required fields at line {line_num}")
                    continue

                # Normalize and validate
                try:
                    level_int = int(level)
                    if level_int not in [1, 2, 3]:
                        print(f"Warning: Invalid level {level} at line {line_num}")
                        continue
                except (ValueError, TypeError):
                    print(f"Warning: Invalid level format at line {line_num}")
                    continue

                tasks.append({
                    'task_id': str(task_id),
                    'question': str(question),
                    'ground_truth': str(final_answer) if final_answer else '',
                    'level': level_int,
                    'has_file': bool(file_name and str(file_name).strip()),
                })
                
    except FileNotFoundError:
        raise FileNotFoundError(f"Data file not found: {path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load data from {path}: {e}")
    
    return tasks


def filter_tasks(tasks: List[Dict], level: str = 'all', limit: int = 0) -> List[Dict]:
    """
    Filter tasks by level and apply permanent file exclusion
    
    Args:
        tasks: List of task dictionaries
        level: Level filter ('1', '2', '3', or 'all')
        limit: Maximum number of tasks to return (0 = no limit)
        
    Returns:
        Filtered list of tasks
    """
    filtered = tasks.copy()
    
    # Filter by level if specified
    if level != 'all':
        try:
            level_int = int(level)
            filtered = [t for t in filtered if t['level'] == level_int]
        except ValueError:
            raise ValueError(f"Invalid level filter: {level}. Must be '1', '2', '3', or 'all'")
    
    # PERMANENT exclusion of tasks requiring files (no override ever)
    filtered = [t for t in filtered if not t['has_file']]
    
    # Apply limit if specified
    if limit > 0:
        filtered = filtered[:limit]
    
    return filtered


def get_task_stats(tasks: List[Dict]) -> Dict[str, int]:
    """
    Get basic statistics about the task list
    
    Args:
        tasks: List of task dictionaries
        
    Returns:
        Dictionary with task statistics
    """
    if not tasks:
        return {'total': 0, 'level_1': 0, 'level_2': 0, 'level_3': 0, 'with_files': 0}
    
    stats = {
        'total': len(tasks),
        'level_1': len([t for t in tasks if t['level'] == 1]),
        'level_2': len([t for t in tasks if t['level'] == 2]),
        'level_3': len([t for t in tasks if t['level'] == 3]),
        'with_files': len([t for t in tasks if t['has_file']]),
    }
    
    return stats
