#!/usr/bin/env python3
"""
Test client for the LLMOps Instruction Tuning Workshop LLM serving endpoint.
This script tests the vLLM server deployment by sending inference requests.
"""

import argparse
import json
import time
import sys
import requests
from typing import Dict, Any, Optional


def parse_args():
    parser = argparse.ArgumentParser(description="Test LLM serving endpoint")
    parser.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8000/v1/chat/completions",
        help="URL of the vLLM server endpoint"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="TinyLlama-1.1B-Chat-v1.0",
        help="Model name to use for inference"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="Explain the concept of MLOps in simple terms.",
        help="Prompt to send to the model"
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100,
        help="Maximum number of tokens to generate"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature"
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=1,
        help="Number of requests to send"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Whether to stream the response"
    )
    return parser.parse_args()


def test_health_check(endpoint: str) -> bool:
    """Test the health check endpoint."""
    health_url = endpoint.replace("/v1/chat/completions", "/health")
    try:
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def send_request(
    endpoint: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    stream: bool = False
) -> Optional[Dict[str, Any]]:
    """Send a request to the LLM endpoint."""
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        if stream:
            response = requests.post(
                endpoint, 
                json=payload, 
                headers=headers, 
                stream=True,
                timeout=30
            )
            if response.status_code != 200:
                print(f"Request failed with status {response.status_code}")
                print(response.text)
                return None
                
            print("Streaming response:")
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith("data: "):
                        data = line_text[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                print(content, end="", flush=True)
                                full_response += content
                        except json.JSONDecodeError:
                            pass  # Ignore non-JSON lines
            print()  # New line after streaming
            return {"response": full_response}
        else:
            response = requests.post(
                endpoint, 
                json=payload, 
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Request failed with status {response.status_code}")
                print(response.text)
                return None
                
            return response.json()
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def main():
    args = parse_args()
    
    print(f"Testing LLM endpoint: {args.endpoint}")
    print(f"Model: {args.model}")
    print(f"Prompt: {args.prompt}")
    print("-" * 50)
    
    # Test health check first
    print("Performing health check...")
    if not test_health_check(args.endpoint):
        print("Health check failed. Make sure the vLLM server is running.")
        sys.exit(1)
    print("Health check passed!")
    print("-" * 50)
    
    # Send requests
    start_time = time.time()
    for i in range(args.num_requests):
        print(f"Sending request {i+1}/{args.num_requests}...")
        result = send_request(
            endpoint=args.endpoint,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            stream=args.stream
        )
        
        if result is not None:
            if not args.stream:
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0]["message"]["content"]
                    print(f"Response: {message}")
                else:
                    print(f"Full response: {json.dumps(result, indent=2)}")
            print("-" * 30)
        else:
            print(f"Request {i+1} failed!")
            print("-" * 30)
    
    end_time = time.time()
    total_time = end_time - start_time
    print(f"Completed {args.num_requests} request(s) in {total_time:.2f} seconds")
    if args.num_requests > 0:
        print(f"Average time per request: {total_time/args.num_requests:.2f} seconds")


if __name__ == "__main__":
    main()