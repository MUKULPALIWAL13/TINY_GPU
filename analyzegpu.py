def analyze_gpu_output(data, channels=4):
    print("\nRAW GPU MEMORY:")
    print(data)

    # --- view 1: split by channels (how GPU stores it physically) ---
    lanes = [data[i::channels] for i in range(channels)]
    print("\nBY MEMORY CHANNEL (GPU PHYSICAL LAYOUT):")
    for i, lane in enumerate(lanes):
        print(f"lane{i}: {lane}")

    # --- view 2: reconstruct per-thread order (de-interleave) ---
    reconstructed = []
    for i in range(len(data) // channels):
        for lane in range(channels):
            idx = lane + i * channels
            if idx < len(data):
                reconstructed.append(data[idx])

    print("\nDE-INTERLEAVED (per-thread order guess):")
    print(reconstructed)

    # --- view 3: try showing as 2×4 and 2×2 (for intuition) ---
    print("\nAS 2×4 MATRIX (guess):")
    for i in range(0, len(data), 4):
        print(data[i:i+4])

    print("\nAS 2×2 MATRIX (taking every 2nd element):")
    guess_2x2 = reconstructed[0:4]
    print([guess_2x2[0:2], guess_2x2[2:4]])


# Example:
data =  [2, 2, 2, 2, 2, 2, 2, 2]

analyze_gpu_output(data)
