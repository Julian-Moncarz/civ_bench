#!/usr/bin/env python3
"""
Main benchmark orchestrator.
Run with: python run_bench.py
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

import config
import answerer


def main():
    """Run the benchmark."""
    print("=" * 60)
    print("Civil Engineering Benchmark")
    print("=" * 60)
    print()

    # Check that images directory exists
    if not config.IMAGES_DIR.exists():
        print(f"❌ Images directory not found: {config.IMAGES_DIR}")
        print("Please create it and add assignment screenshots.")
        return

    # Check for image files
    image_files = list(config.IMAGES_DIR.glob("*.png"))
    if not image_files:
        print(f"❌ No assignment images found in {config.IMAGES_DIR}")
        print("Please add screenshots named: 1.png, 1.1.png, 2.png, etc.")
        return

    print(f"Found {len(image_files)} image file(s)")
    print(f"Testing {len(config.TEST_MODELS)} model(s)")
    print(f"Number of trials per model: {config.NUM_TRIALS}")
    print(f"Parallel workers: {config.MAX_WORKERS}")
    print()

    # Run benchmark
    total_calls = 0
    successful_calls = 0
    failed_calls = 0

    for model_id in config.TEST_MODELS:
        print(f"\n{'='*60}")
        print(f"Model: {model_id}")
        print('='*60)

        for trial_num in range(config.NUM_TRIALS):
            if config.NUM_TRIALS > 1:
                print(f"\nTrial {trial_num + 1}/{config.NUM_TRIALS}")

            # Build list of assignments to process
            assignments_to_process = []
            for assignment_num in config.ASSIGNMENTS_TO_TEST:
                # Check if images exist for this assignment
                image_paths = answerer.find_assignment_images(assignment_num)
                if not image_paths:
                    print(f"  Skipping assignment {assignment_num} (no images found)")
                    continue
                assignments_to_process.append(assignment_num)

            if not assignments_to_process:
                continue

            # Process assignments in parallel
            print(f"\n  Processing {len(assignments_to_process)} assignment(s) with {config.MAX_WORKERS} workers...")
            with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
                # Submit all tasks (verbose=False for cleaner output)
                future_to_assignment = {
                    executor.submit(
                        answerer.get_answer,
                        model_id,
                        assignment_num,
                        trial_num,
                        verbose=False
                    ): assignment_num
                    for assignment_num in assignments_to_process
                }

                # Process results as they complete with progress bar
                with tqdm(total=len(assignments_to_process), desc="  Progress", unit="assignment") as pbar:
                    for future in as_completed(future_to_assignment):
                        assignment_num = future_to_assignment[future]
                        total_calls += 1

                        try:
                            result = future.result()
                            if result["success"]:
                                successful_calls += 1
                                pbar.set_postfix_str(f"Assignment {assignment_num} ✓")
                            else:
                                failed_calls += 1
                                pbar.set_postfix_str(f"Assignment {assignment_num} ✗")
                        except Exception as e:
                            failed_calls += 1
                            tqdm.write(f"  ❌ Exception processing assignment {assignment_num}: {e}")

                        pbar.update(1)

    # Summary
    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)
    print(f"Total API calls: {total_calls}")
    print(f"Successful: {successful_calls}")
    print(f"Failed: {failed_calls}")
    print(f"\nResponses saved to: {config.RESPONSES_DIR}")
    print()


if __name__ == "__main__":
    main()
