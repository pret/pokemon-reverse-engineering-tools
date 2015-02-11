/*
 * Copyright © 2011, 2014 IIMarckus <iimarckus@gmail.com>
 *
 * Permission to use, copy, modify, and distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

/*
 * This program compresses or decompresses the Town Map tilemap
 * from Pokémon Red, Blue, and Yellow.
 */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void
usage()
{
	fprintf(stderr, "Usage: redrle [-dr] infile outfile\n");
	exit(1);
}

void
squash(int threshold, FILE *f, int lastbyte, int *count, int *xpos)
{
	fputc(lastbyte << 4 | threshold, f);
	*xpos += threshold;
	*xpos %= 20;
	*count -= threshold;
}

int
main(int argc, char *argv[])
{
	FILE *infile, *outfile;
	int ch;
	bool d = false; /* compress or decompress flag */
	bool rows = false; /* compress individual rows or entire file */

	while ((ch = getopt(argc, argv, "dr")) != -1) {
		switch(ch) {
		case 'd':
			d = true;
			break;
		case 'r':
			rows = true;
			break;
		default:
			usage();
			/* NOTREACHED */
		}
	}
	argc -= optind;
	argv += optind;

	if (argc < 2) {
		usage();
	}

	infile = fopen(argv[argc - 2], "rb");
	if (infile == NULL) {
		fprintf(stderr, "Error opening file '%s': ", argv[argc - 2]);
		perror(NULL);
		exit(1);
	}

	outfile = fopen(argv[argc - 1], "wb");
	if (outfile == NULL) {
		fprintf(stderr, "Error opening file '%s': ", argv[argc - 1]);
		perror(NULL);
		exit(1);
	}

	if (d) { /* decompress */
		for (;;) {
			int i, count;
			int byte = fgetc(infile);
			if (byte == 0)
				break;
			count = byte & 0xF;
			byte >>= 4;

			if (feof(infile)) {
				fprintf(stderr, "Decompress error: reached "
				    "end of file without finding terminating "
				    "null byte.\n");
				exit(1);
			}
			for (i = 0; i < count;
			    ++i)
				fputc(byte, outfile);
		}
	} else { /* compress */
		int byte, count = 0, lastbyte = 0, xpos = 0;
		for (;;) {
			byte = fgetc(infile);

			if (feof(infile)) {
				while (count > 0xF) {
					if (rows && 20 - xpos <= 0xF) {
						squash(20 - xpos, outfile,
						    lastbyte, &count, &xpos);
						continue;
					}
					squash(0xF, outfile, lastbyte, &count,
					    &xpos);
				}
				if (count != 0) {
					if (rows && 20 - xpos < count) {
						squash(20 - xpos, outfile,
						    lastbyte, &count, &xpos);
					}
					squash(count, outfile, lastbyte,
					    &count, &xpos);
				}
				break;
			}

			if (byte > 0xF) {
				fprintf(stderr, "Compress error: read a byte "
				    "greater than 0xF.\n");
				exit(1);
			}

			if (byte == lastbyte)
				++count;
			else {
				while (count > 0xF) {
					if (rows && 20 - xpos <= 0xF) {
						squash(20 - xpos, outfile,
						    lastbyte, &count, &xpos);
						continue;
					}
					squash(0xF, outfile, lastbyte, &count,
					    &xpos);
				}
				if (count != 0) {
					if (rows && 20 - xpos < count) {
						squash(20 - xpos, outfile,
						    lastbyte, &count, &xpos);
					}
					squash(count, outfile, lastbyte,
					    &count, &xpos);
				}

				lastbyte = byte;
				count = 1;
			}
		}

		fputc(0, outfile); /* Terminating 0x00 */
	}

	fclose(infile);
	fclose(outfile);

	return 0;
}
