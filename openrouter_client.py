"""
Simple OpenRouter API client.
"""

import base64
import requests
from pathlib import Path
from typing import List, Dict, Optional

import config


def encode_image(image_path: Path) -> str:
    """Encode image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def call_model(
    model_id: str,
    prompt: str,
    image_paths: Optional[List[Path]] = None,
    max_tokens: int = 10000,
    temperature: float = 1.0,
    timeout: int = 120,
) -> Dict:
    """
    Call an OpenRouter model with text and optional images.

    Args:
        model_id: OpenRouter model ID (e.g., "anthropic/claude-sonnet-4.5")
        prompt: Text prompt to send
        image_paths: Optional list of image file paths
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0=deterministic, 1=creative)

    Returns:
        Dict with 'content' (response text) and 'error' (if any)
    """
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Build messages
    messages = []
    content_parts = []

    # Add images if provided
    if image_paths:
        for img_path in image_paths:
            # All images are .png format
            encoded = encode_image(img_path)
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded}"
                }
            })

    # Add text prompt
    content_parts.append({
        "type": "text",
        "text": prompt
    })

    messages.append({
        "role": "user",
        "content": content_parts
    })

    # Make API request
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        response = requests.post(
            f"{config.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()

        data = response.json()

        # Check for errors in the response choices
        choice = data["choices"][0]
        if "error" in choice and choice["error"]:
            error_msg = choice["error"].get("message", "Unknown error")
            error_code = choice["error"].get("code", "unknown")
            return {
                "content": None,
                "error": f"Model error ({error_code}): {error_msg}",
            }

        message = choice["message"]
        # For reasoning models (like GPT-5), check for reasoning field first
        # If reasoning exists and content is empty, use reasoning as the content
        content = message.get("content", "")
        if not content and "reasoning" in message:
            content = message["reasoning"]

        return {
            "content": content,
            "error": None,
            "usage": data.get("usage", {}),
        }

    except requests.exceptions.Timeout:
        return {
            "content": None,
            "error": f"Request timed out after {timeout} seconds",
        }
    except requests.exceptions.RequestException as e:
        return {
            "content": None,
            "error": f"API request failed: {str(e)}",
        }
    except (KeyError, IndexError) as e:
        return {
            "content": None,
            "error": f"Failed to parse response: {str(e)}",
        }
    except Exception as e:
        return {
            "content": None,
            "error": f"Unexpected error: {str(e)}",
        }
