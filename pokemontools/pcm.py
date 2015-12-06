# pcm.py
# Converts between .wav files and 1-bit pcm data. (pcm = pulse-code modulation)

import argparse
import os
import struct
import wave


BASE_SAMPLE_RATE = 22050

def convert_to_wav(filenames=[]):
    """
    Converts a file containing 1-bit pcm data into a .wav file.
    """
    for filename in filenames:
        samples = []
        with open(filename, 'rb') as pcm_file:
            # Generate array of on/off pcm values.
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
        wave_file.setframerate(BASE_SAMPLE_RATE)
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

    This currently works correctly on .wav files with the following attributes:
            1. Sample Width = 1 or 2 bytes (Some wave files use 3 bytes per sample...)
            2. Arbitrary sample sample_rate
            3. Mono or Stereo (1 or 2 channels)
    """
    for filename in filenames:
        samples, average_sample = get_wav_samples(filename)

        # Generate a list of 1-bit pcm samples
        pcm_samples = clamp_samples(samples, average_sample)
        pcm_samples = add_pcm_padding(pcm_samples)

        # Pack the 1-bit samples together.
        packed_samples = pack_pcm_samples(pcm_samples)

        # Write the pcm data to a file.
        name, extension = os.path.splitext(filename)
        pcm_filename = name + '.pcm'
        with open(pcm_filename, 'wb') as out_file:
            out_file.write(packed_samples)


def get_wav_samples(filename):
    """
    Reads the given .wav file and returns a list of its samples after re-sampling
    to BASE_SAMPLE_RATE.
    Also returns the average sample amplitude.
    """
    wav_file = wave.open(filename, 'r')
    sample_width = wav_file.getsampwidth()
    sample_count = wav_file.getnframes()
    sample_rate = wav_file.getframerate()
    num_channels = wav_file.getnchannels()

    raw_frames = bytearray(wav_file.readframes(sample_count))

    # Unpack the samples from the raw frame data based on the file's sample width.
    samples = []
    for i in xrange(0, len(raw_frames), sample_width):
        value_to_unpack = raw_frames[i:i + sample_width]
        sample = unpack_sample(value_to_unpack, sample_width)
        samples.append(sample)

    # Only keep the samples from the first audio channel.
    samples = samples[::num_channels]

    # Resample the raw samples to approximate BASE_SAMPLE_RATE.
    resampled_samples = resample(samples, sample_rate, BASE_SAMPLE_RATE)
    average_sample = float(sum(resampled_samples)) / len(resampled_samples)

    return resampled_samples, average_sample


def unpack_sample(value, sample_width):
    '''
    Unpack the value based on the given sample width.
    '''
    if len(value) != sample_width:
        raise Exception, "Can't unpack sample; Sample width does not match size of raw value: size of value=%d, sample_width=%d" % (len(value), sample_width)

    if sample_width == 1:
        fmt = 'B'
    elif sample_width == 2:
        fmt = 'h'
    else:
        # todo: support 3-byte sample width
        raise Exception, "Unsupported sample width: " + str(sample_width)

    unpacked_sample = struct.unpack(fmt, value)[0]
    return unpacked_sample


def resample(samples, sample_rate, base_sample_rate):
    '''
    Resamples the raw sample list to approximate the given base sample rate.
    This could be improved with a re-sampling heuristic, such as linear 
    interpolation between samples.
    '''
    interval = float(sample_rate) / base_sample_rate
    resampled_samples = []
    index = 0.0
    while index < len(samples):
        sample = samples[int(index)]
        resampled_samples.append(sample)
        index += interval

    return resampled_samples


def clamp_samples(samples, average_sample):
    '''
    Clamps each sample to 0 or 1 base on the given average sample.
    '''
    clamped_samples = []
    for sample in samples:
        # Clamp the raw sample to on/off
        if sample < average_sample:
            clamped_samples.append(0)
        else:
            clamped_samples.append(1)

    return clamped_samples


def add_pcm_padding(pcm_samples):
    '''
    Pads the given pcm samples with 0 so that the number of samples
    is a multiple of 8. This is required, since the pcm samples will
    be packed into bytes, which are defined by 8 bits.
    '''
    while len(pcm_samples) % 8 != 0:
            pcm_samples.append(0)
    return pcm_samples


def pack_pcm_samples(pcm_samples):
    '''
    Packs each chunk of 8 pcm samples into a byte array.
    Samples are interpreted in most-significant order, meaning
    the first sample is the most-significant bit in the first byte.
    '''
    packed_samples = bytearray()
    for i in xrange(0, len(pcm_samples), 8):
        # Read 8 pcm values to pack one byte.
        packed_value = 0
        for j in range(8):
            packed_value <<= 1
            if i + j < len(pcm_samples):            
                packed_value += pcm_samples[i + j]

        packed_samples.append(packed_value)

    return packed_samples


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
