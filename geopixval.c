#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <math.h>

#include "geotiff.h"
#include "xtiffio.h"
#include "geo_normalize.h"
#include "geo_simpletags.h"
#include "geovalues.h"
#include "tiffio.h"

#include "geo_tiffp.h" /* external TIFF interface */
#include "geo_keyp.h" /* private interface */
#include "geokeys.h"

int verbose = 1;
	
// a.out filename lat long

int main(int argc, char *argv[]) {
	char *fname = argv[1];
	float lat 	= atof(argv[2]);
	float lng 	= atof(argv[3]);
	
	int xsize, ysize, dtype, bs;

	TIFF *tif 	= (TIFF *)0;  /* TIFF-level descriptor */
	GTIF *gtif 	= (GTIF *)0; /* GeoKey-level descriptor */

	if( verbose ) printf("%s %f %f\n", fname, lat, lng);

	tif = XTIFFOpen(fname, "r");
	if (!tif) {
		printf("Failed opeing %s\n", fname);
		exit(-1);
	};

	gtif = GTIFNew(tif);
	if (!gtif) {
		fprintf(stderr, "failed in GTIFNew\n");
		exit(-1);
	}

	TIFFGetField(tif, TIFFTAG_IMAGEWIDTH, &xsize);
	TIFFGetField(tif, TIFFTAG_IMAGELENGTH, &ysize);
	TIFFGetField(tif, TIFFTAG_DATATYPE, &dtype);
	TIFFGetField(tif, TIFFTAG_BITSPERSAMPLE, &bs);
 
	if( verbose ) printf("Size %d %d type %d bps %d\n", xsize, ysize, dtype, bs);

  // GTIFPrint(gtif,0,0);

	double *data;
	int count;
	double xmin, ymax, xres, yres;
		
	if ((gtif->gt_methods.get)(tif, GTIFF_TIEPOINTS, &count, &data)) {
		if( verbose ) {
			printf("GTIFF_TIEPOINTS: ");
			for (int i = 0; i < count; i++) {
				printf("%-17.15g ", data[i]);
			}
			printf("\n");
		}
		xmin 	= data[3];	// min long
		ymax	= data[4];	// max lat
		
		_GTIFFree(data);
	}
	
	if ((gtif->gt_methods.get)(tif, GTIFF_PIXELSCALE, &count, &data )) {
		if( verbose ) {
			printf("GTIFF_PIXELSCALE: ");
			for (int i = 0; i < count; i++) {
				printf("%-17.15g ", data[i]);
			}
			printf("\n");
		}	
		
		xres 	= data[0];
		yres 	= data[1];
		_GTIFFree(data);
	}
	
	if ((gtif->gt_methods.get)(tif, GTIFF_TRANSMATRIX, &count, &data )) {
		if( verbose ) {
			printf("GTIFF_TRANSMATRIX: ");
			for (int i = 0; i < count; i++) {
				printf("%-17.15g ", data[i]);
			}
			printf("\n");
		}	
		_GTIFFree(data);
	}

	if( verbose ) printf("%f %f %f %f\n", xmin, ymax, xres, yres);

	// find pixel of interest
	long pixX			= lround((lng - xmin) / xres);
	long pixY			= lround((ymax - lat) / yres);
	
	if( pixX < 0 || pixX > xsize) printf("Invalid pixX %ld\n", pixX);
	if( pixY < 0 || pixY > ysize) printf("Invalid pixY %ld\n", pixY);
	
	// find position in buffer
	long pos			= pixY*xsize + pixX;
	if( pos < 0 || pos > xsize*ysize ) printf("Invalid pos %ld\n", pos);
	
	if( verbose ) printf("pixel x:%ld y:%ld pos:%ld\n", pixX, pixY, pos);
	
	tstrip_t numstrips  		= TIFFNumberOfStrips(tif);
	tstrip_t stripsize  		= TIFFStripSize(tif);
	char* buf         			= malloc(numstrips * stripsize);
    unsigned long imageOffset 	= 0;
	unsigned long result;
	
  	if( verbose ) printf("strips %u size %u\n", numstrips, stripsize);
	
	for(tstrip_t strip=0; strip < numstrips; strip++) {
		TIFFReadEncodedStrip(tif,strip, &buf[strip*stripsize],(tsize_t) -1);
		
		if((result = TIFFReadEncodedStrip (tif, strip, buf + imageOffset, stripsize)) == -1) {
		      fprintf(stderr, "Read error on input strip number %d\n", strip);
		      exit(42);
		}

		imageOffset += result;
	}

	if( bs == 16 ) {
		uint16* ubuf = (uint16*)buf;
		
		if( verbose ) printf("val %d\n", ubuf[pos]);
	
		for( int r=0; r<ysize; r++) {
			printf( "R: %d - ", r );
			for( int c=0; c< ysize; c++) {
				int pos = r*xsize + c;
				printf("%02d ", ubuf[pos]);;
			}
			printf("\n");
		}
	} else if(bs == 8 ) {
		uint8* ubuf = (uint8*)buf;
		
		if( verbose ) printf("val %d\n", ubuf[pos]);
	
		//for( int r=0; r<ysize; r++) {
		//	printf( "R: %d - ", r );
		//	for( int c=0; c< ysize; c++) {
		//		int pos = r*xsize + c;
		//		printf("%02d ", ubuf[pos]);;
		//	}
		//	printf("\n");
		//}
	}
	
	free(buf);
  
	if (tif)	XTIFFClose(tif);
	if (gtif) 	GTIFFree(gtif);
}