# pcm.py
# Converts between .wav files and 1-bit pcm data. (pcm = pulse-code modulation)

import argparse
import os
import struct
import wave


def convert_to_wav(filenames=[]):
    """
    Converts a file containing 1-bit pcm data into a .wav file.
    """
    for filename in filenames:
        with open(filename, 'rb') as pcm_file:
            # Generate array of on/off pcm values.
            samples = []
            byte = pcm_file.read(1)
            while byte != "":
                byte = struct.unpack('B', byte)[0]
                for i in range(8):
                    bit_index = 7 - i
                    value = (byte >> bit_index) & 1
                    samples.append(value)
                byte = pcm_file.read(1)

        # Write a .wav file using the pcm data.
        name, extension = os.path.splitext(filename)
        wav_filename = name + '.wav'
        wave_file = wave.open(wav_filename, 'w')
        wave_file.setframerate(22050)
        wave_file.setnchannels(1)
        wave_file.setsampwidth(1)

        for value in samples:
            if value > 0:
                value = 0xff

            packed_value = struct.pack('B', value)
            wave_file.writeframesraw(packed_value)

        wave_file.close()


def convert_to_pcm(filenames=[]):
    """
    Converts a .wav file into 1-bit pcm data.
    Samples in the .wav file are simply clamped to on/off.

    TODO: This currently only works correctly on .wav files with the following attributes:
            1. Sample Rate = 22050
            2. Sample Width = 1 byte
            3. 1 Channel
        It can be improved to account for these factors.
    """
    for filename in filenames:
        samples, sample_width = get_wav_samples(filename)
        sample_middle = (sample_width * 0xff) / 2

        # Generate a list of clamped samples
        clamped_samples = []
        for sample in samples:
            # Clamp the raw sample to on/off
            if sample < sample_middle:
                clamped_samples.append(0)
            else:
                clamped_samples.append(1)

        # The pcm data must be a multiple of 8, so pad the clamped samples with 0.
        while len(clamped_samples) % 8 != 0:
            clamped_samples.append(0)

        # Pack the 1-bit samples together.
        packed_samples = bytearray()
        for i in xrange(0, len(clamped_samples), 8):
            # Read 8 pcm values to pack one byte.
            packed_value = 0
            for j in range(8):
                packed_value <<= 1
                packed_value += clamped_samples[i + j]
            packed_samples.append(packed_value)

        # Open the output .pcm file, and write all 1-bit samples.
        name, extension = os.path.splitext(filename)
        pcm_filename = name + '.pcm'
        with open(pcm_filename, 'wb') as out_file:
            out_file.write(packed_samples)


def get_wav_samples(filename):
    """
    Reads the given .wav file and returns a list of its raw samples.
    Also returns the byte width of the samples.
    """
    wav_file = wave.open(filename, 'r')
    sample_width = wav_file.getsampwidth()
    sample_count = wav_file.getnframes()

    samples = bytearray(wav_file.readframes(sample_count))

    return samples, sample_width


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('filenames', nargs='*')
    args = ap.parse_args()

    method = {
        'wav': convert_to_wav,
        'pcm': convert_to_pcm,
    }.get(args.mode, None)

    if method == None:
        raise Exception, "Unknown conversion method!"

    method(args.filenames)

if __name__ == "__main__":
    main()
