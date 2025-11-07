"""
Simple OpenRouter API client.
"""

import base64
import logging
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional

import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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

    # Log request details
    image_count = len(image_paths) if image_paths else 0
    logger.info(f"Starting API request: model={model_id}, images={image_count}, timeout={timeout}s")
    start_time = time.time()

    try:
        response = requests.post(
            f"{config.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Got HTTP response: status={response.status_code}, elapsed={elapsed_time:.1f}s")

        # Log response body for debugging (first 500 chars)
        response_preview = response.text[:500] if len(response.text) > 500 else response.text
        logger.debug(f"Response preview: {response_preview}")

        response.raise_for_status()

        data = response.json()

        # Check for errors in the response choices
        choice = data["choices"][0]
        if "error" in choice and choice["error"]:
            error_msg = choice["error"].get("message", "Unknown error")
            error_code = choice["error"].get("code", "unknown")
            logger.error(f"Model returned error: code={error_code}, message={error_msg}")
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
            logger.info(f"Using reasoning field as content (length={len(content)} chars)")

        content_length = len(content) if content else 0
        usage = data.get("usage", {})
        logger.info(f"Success: content_length={content_length} chars, usage={usage}")

        return {
            "content": content,
            "error": None,
            "usage": usage,
        }

    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        logger.error(f"Request timed out after {elapsed_time:.1f}s (timeout={timeout}s)")
        return {
            "content": None,
            "error": f"Request timed out after {timeout} seconds",
        }
    except requests.exceptions.RequestException as e:
        elapsed_time = time.time() - start_time
        logger.error(f"API request failed after {elapsed_time:.1f}s: {str(e)}")
        # Try to log response details if available
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text[:500]}")
        return {
            "content": None,
            "error": f"API request failed: {str(e)}",
        }
    except (KeyError, IndexError) as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Failed to parse response after {elapsed_time:.1f}s: {str(e)}")
        logger.error(f"Response data structure: {data if 'data' in locals() else 'N/A'}")
        return {
            "content": None,
            "error": f"Failed to parse response: {str(e)}",
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Unexpected error after {elapsed_time:.1f}s: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "content": None,
            "error": f"Unexpected error: {str(e)}",
        }
