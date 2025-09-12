#!/usr/bin/env python3
"""
GAIA Runner - Minimal LLM judge with function calling
Implements 0-5 scoring system with unit/format awareness.
"""

import json
import time
from typing import Tuple, Dict, Any
from ck_pro.core import CognitiveKernel
from ck_pro.agents.model import LLM


def judge_answer(kernel: CognitiveKernel, question: str, answer: str, ground_truth: str) -> Tuple[int, str]:
    """
    Judge model answer against ground truth using LLM with function calling
    
    Args:
        kernel: CognitiveKernel instance (for accessing model config)
        question: Original task question
        answer: Model's answer to evaluate
        ground_truth: Expected correct answer
        
    Returns:
        Tuple of (score: int 0-5, reason: str)
    """
    # Handle edge cases
    if not ground_truth or not ground_truth.strip():
        return 0, 'empty-ground-truth'
    
    if not answer or not str(answer).strip():
        return 0, 'empty-answer'
    
    # Create LLM instance using same config as kernel
    cfg = kernel.settings.ck.model
    judge_llm = LLM(
        call_target=cfg.call_target,
        api_key=cfg.api_key,
        model=cfg.model,
        extract_body=cfg.extract_body.copy()  # Start with base config
    )
    
    # Prepare judge prompt
    system_prompt = (
        "You are a strict evaluator. Use the provided function `grade(score:int, reason:str)` "
        "to score the model answer against the ground truth. Consider units, conversions, "
        "and format requirements carefully."
    )
    
    user_prompt = f"""Task: {question}

Expected Answer (ground truth): {ground_truth}
Model Answer: {answer}

Guidelines:
- Score from 0 to 5 (integers only), where 5 = fully correct and compliant; 0 = wrong/irrelevant.
- Pay special attention to units, numerical conversions, and precision (e.g., 17 thousand hours ≠ 17000 hours if context implies unit mismatch).
- Enforce format requirements explicitly stated in the query (unit, casing, output schema, etc.).
- Penalize partial or ambiguous answers accordingly.

Use the provided function `grade(score:int, reason:str)` to return the result; do NOT output free text."""

    # Function calling schema for grading
    function_schema = {
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "grade",
                    "description": "Return a 0-5 integer score and a brief justification.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "integer", "minimum": 0, "maximum": 5},
                            "reason": {"type": "string"}
                        },
                        "required": ["score", "reason"]
                    }
                }
            }
        ],
        "tool_choice": {"type": "function", "function": {"name": "grade"}}
    }
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        # Call LLM with function calling
        response = judge_llm(messages, extract_body=function_schema)
        
        # Parse the response (should be JSON from function call)
        try:
            result = json.loads(response)
            score = int(result.get('score', 0))
            reason = str(result.get('reason', '')).strip()
            
            # Validate score range
            score = max(0, min(5, score))
            
            # Ensure reason is not empty
            if not reason:
                reason = 'llm-judge-no-reason'
                
            return score, reason
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # Fallback: try to extract score from text response
            return _fallback_parse_score(response), f'parse-error: {str(e)}'
            
    except Exception as e:
        # Last resort: exact match fallback
        if str(answer).strip().lower() == str(ground_truth).strip().lower():
            return 5, 'fallback-exact-match'
        return 0, f'judge-failed: {str(e)}'


def _fallback_parse_score(response: str) -> int:
    """
    Fallback parser to extract score from text response
    
    Args:
        response: Raw LLM response text
        
    Returns:
        Extracted score (0-5)
    """
    import re
    
    # Try to find score patterns
    patterns = [
        r'"score":\s*(\d+)',
        r'score:\s*(\d+)',
        r'Score:\s*(\d+)',
        r'(\d+)/5',
        r'(\d+)\s*out\s*of\s*5'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            try:
                score = int(match.group(1))
                return max(0, min(5, score))
            except ValueError:
                continue
    
    # No score found
    return 0


def run_single_task(kernel: CognitiveKernel, task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a single task through the complete pipeline
    
    Args:
        kernel: CognitiveKernel instance
        task: Task dictionary from data_loader
        
    Returns:
        Result dictionary with all fields
    """
    start_time = time.time()
    
    try:
        # Execute reasoning via CognitiveKernel
        result = kernel.reason(task['question'])
        
        if not result.success:
            # Fail fast on execution errors
            return {
                **task,
                'answer': None,
                'success': False,
                'error': f'kernel-failed: {getattr(result, "error", "unknown")}',
                'execution_time': time.time() - start_time,
                'reasoning_steps': 0,
                'score': 0,
                'judge_reason': 'execution-failed'
            }
        
        # Judge the answer
        score, judge_reason = judge_answer(
            kernel, 
            task['question'], 
            result.answer, 
            task['ground_truth']
        )
        
        return {
            **task,
            'answer': result.answer,
            'success': True,
            'error': None,
            'execution_time': time.time() - start_time,
            'reasoning_steps': result.reasoning_steps,
            'score': score,
            'judge_reason': judge_reason
        }
        
    except Exception as e:
        return {
            **task,
            'answer': None,
            'success': False,
            'error': f'unexpected-error: {str(e)}',
            'execution_time': time.time() - start_time,
            'reasoning_steps': 0,
            'score': 0,
            'judge_reason': 'execution-failed'
        }
