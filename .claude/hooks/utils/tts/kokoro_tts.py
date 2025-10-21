#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "mlx-audio",
# ]
# ///

import random
import sys
from datetime import datetime

from mlx_audio.tts.generate import generate_audio  # type: ignore[reportUnknownVariableType]


def main():
    """
    Generate text-to-speech audio using Kokoro-82M model with weighted random voice selection.

    This script performs the following:
    1. Randomly selects a language code with weighted probability:
       - 'a' (American): 50% chance
       - 'b' (British): 30% chance
       - 'j' (Japanese): 15% chance
       - 'z' (Chinese): 5% chance
    2. Selects a random female voice from the corresponding language voice list
    3. Generates audio file with timestamp and voice name in the filename
    4. Saves to: logs/audio/{timestamp}-{voicename}-notification.wav

    Usage:
        python kokoro_tts.py [text to speak]

    If no text is provided, uses default message.
    """

    lang_code = [
        "a",
        "b",
        "j",
        "z",
    ]  # a for America, b For British, j for Japan, z for Mandarin Chinese

    # If a --> then random select a voice from the following list
    america_female_voice = [
        "af_alloy",
        "af_aoede",
        "af_bella",
        "af_heart",
        "af_jessica",
        "af_kore",
        "af_nicole",
        "af_nova",
        "af_river",
        "af_sarah",
        "af_sky",
    ]

    british_female_voice = ["bf_alice", "bf_emma", "bf_isabella", "bf_lily"]

    # If j --> then random select a voice from the following list
    japan_female_voice = ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro"]

    #  If z --> then random select a voice from the following list
    chinese_female_voice = ["zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi"]

    # Weighted random selection: 'a'=50%, 'b'=30%, 'j'=15%, 'z'=5%
    selected_lang_code = random.choices(lang_code, weights=[50, 30, 15, 5], k=1)[0]

    # Map language code to corresponding voice list
    voice_mapping = {
        "a": america_female_voice,
        "b": british_female_voice,
        "j": japan_female_voice,
        "z": chinese_female_voice,
    }

    # Select random voice from the mapped list
    selected_voice = random.choice(voice_mapping[selected_lang_code])

    # Generate timestamp for unique file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        print("🎙️  Kokoro-82M BF16 TTS")
        print("=" * 40)
        print(f"🌍 Language: {selected_lang_code} | Voice: {selected_voice}")

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:])  # Join all arguments as text

        else:
            text = "The first move is what sets everything in motion."

        print(f"🎯 Text: {text}")
        print("🔊 Generating and playing...")

        try:
            # Generate and play audio directly
            generate_audio(
                text=text,
                model_path="prince-canuma/Kokoro-82M",
                voice=selected_voice,
                speed=1.0,
                lang_code=selected_lang_code,
                file_prefix=f"logs/audio/{timestamp}-{selected_voice}-notification",
                audio_format="wav",
                sample_rate=24000,
                join_audio=True,
                verbose=True,  # Set to False to disable print messages
            )

            print("✅ Playback complete!")

        except Exception as e:
            print(f"❌ Error: {e}")

    except ImportError:
        print("❌ Error: mlx-audio package not installed")
        print("This script uses UV to auto-install dependencies.")
        print("Make sure UV is installed: https://docs.astral.sh/uv/")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
