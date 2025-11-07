"""
Module for getting answers from models.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import config
import openrouter_client

# Set up logging
logger = logging.getLogger(__name__)


def find_assignment_images(assignment_num: int) -> List[Path]:
    """
    Find all images for a given assignment number.
    Returns images in sorted order: N.png, N.1.png, N.2.png, etc.

    Args:
        assignment_num: Assignment number (e.g., 1, 2, 4)

    Returns:
        List of Path objects for matching images
    """
    # Find all matching images: {N}.png, {N}.1.png, {N}.2.png, etc.
    pattern = f"{assignment_num}.*.png"
    all_matches = list(config.IMAGES_DIR.glob(pattern))

    # Also check for the base image without sub-number
    base_image = config.IMAGES_DIR / f"{assignment_num}.png"
    if base_image.exists():
        all_matches.append(base_image)

    # Sort to ensure consistent order: N.png, N.1.png, N.2.png, etc.
    all_matches.sort(key=lambda p: p.name)

    return all_matches


def get_response_path(model_id: str, assignment_num: int, trial_num: int) -> Path:
    """
    Get the file path where a response should be saved/loaded.

    Args:
        model_id: OpenRouter model ID
        assignment_num: Assignment number
        trial_num: Trial number

    Returns:
        Path object for the response file
    """
    model_name = model_id.replace("/", "_")
    trial_dir = config.RESPONSES_DIR / model_name / f"trial_{trial_num}"
    return trial_dir / f"assignment_{assignment_num}_answer.json"


def load_existing_response(model_id: str, assignment_num: int, trial_num: int) -> Dict | None:
    """
    Load an existing response from disk if it exists.

    Args:
        model_id: OpenRouter model ID
        assignment_num: Assignment number
        trial_num: Trial number

    Returns:
        Response dict if file exists, None otherwise
    """
    response_path = get_response_path(model_id, assignment_num, trial_num)
    if response_path.exists():
        with open(response_path, "r") as f:
            return json.load(f)
    return None


def get_answer(
    model_id: str,
    assignment_num: int,
    trial_num: int = 0,
    verbose: bool = True
) -> Dict:
    """
    Get an answer from a model for a specific assignment.
    If a response already exists on disk, it will be loaded instead of calling the API.

    Args:
        model_id: OpenRouter model ID
        assignment_num: Assignment number (e.g., 1, 2, 4, ...)
        trial_num: Trial number (default 0)

    Returns:
        Dict containing the response and metadata
    """
    logger.info(f"Processing: model={model_id}, assignment={assignment_num}, trial={trial_num}")

    # Check if we already have a response for this
    existing_response = load_existing_response(model_id, assignment_num, trial_num)
    if existing_response is not None:
        logger.info(f"Using cached response for assignment {assignment_num}")
        if verbose:
            print(f"  ✓ Using cached response for assignment {assignment_num}")
        return existing_response

    # Find all images for this assignment (e.g., 1.png, 1.1.png, 1.2.png)
    image_paths = find_assignment_images(assignment_num)

    if not image_paths:
        logger.warning(f"No images found for assignment {assignment_num}")
        return {
            "success": False,
            "error": f"No images found for assignment {assignment_num}",
            "model_id": model_id,
            "assignment_num": assignment_num,
            "trial_num": trial_num,
        }

    logger.info(f"Found {len(image_paths)} image(s) for assignment {assignment_num}: {[p.name for p in image_paths]}")
    if verbose:
        print(f"  Sending assignment {assignment_num} ({len(image_paths)} image(s)) to {model_id}...")

    # Call the model
    logger.info(f"Calling OpenRouter API with timeout={config.DEFAULT_TIMEOUT}s")
    result = openrouter_client.call_model(
        model_id=model_id,
        prompt=config.ANSWERING_PROMPT,
        image_paths=image_paths,
        timeout=config.DEFAULT_TIMEOUT,
    )

    # Build response object
    response_data = {
        "model_id": model_id,
        "assignment_num": assignment_num,
        "trial_num": trial_num,
        "timestamp": datetime.now().isoformat(),
        "success": result["error"] is None,
    }

    if result["error"]:
        response_data["error"] = result["error"]
        response_data["answer"] = None
        logger.error(f"Assignment {assignment_num} failed: {result['error']}")
        if verbose:
            print(f"  ❌ Error: {result['error']}")
    else:
        response_data["answer"] = result["content"]
        response_data["usage"] = result.get("usage", {})
        logger.info(f"Assignment {assignment_num} succeeded: {len(result['content'])} chars, usage={result.get('usage', {})}")
        if verbose:
            print(f"  ✓ Got response ({len(result['content'])} chars)")

    # Save response
    save_answer(response_data, verbose=verbose)

    return response_data


def save_answer(response_data: Dict, verbose: bool = True):
    """Save answer to disk."""
    model_id = response_data["model_id"]
    assignment_num = response_data["assignment_num"]
    trial_num = response_data["trial_num"]

    # Get output file path
    output_file = get_response_path(model_id, assignment_num, trial_num)

    # Create directory structure: responses/{model_name}/trial_{n}/
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to file
    with open(output_file, "w") as f:
        json.dump(response_data, f, indent=2)

    logger.info(f"Saved response to: {output_file}")
    if verbose:
        print(f"  Saved to: {output_file}")
