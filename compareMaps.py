'''
Compare Maps.
Clips maps to matching extent, generates a difference image, & generates a scatterplot.

Usage:
  compareMaps.py <mappath1> <mappath2> <outputdir> [--map1_band=<b1>] [--map2_band=<b2>] [--map1_scale=<s1>] [--map2_scale=<s2>] [--boundarymap=<bm>] [--meta=<m>]
  compareMaps.py -h | --help

Options:
  -h --help     	  Show this screen.
  --map1_band=<b1> 	  Band of map #1 [default: 1].
  --map2_band=<b2>    Band of map #2 [default: 1].
  --map1_scale=<s1>	  Multiply each pixel in map1 by a scale factor [default: 1].
  --map2_scale=<s2>   Multiply each pixel in map2 by a scale factor [default: 1].
  --boundarymap=<bm>  Map to base boundaries on [default: 1].
  --meta=<meta>  	  Additional notes for meta.txt files.
'''
import docopt, gdal, os, subprocess
from lthacks import *
from intersectMask import *
from gdalconst import *
import matplotlib.pyplot as plt
import pylab


def clipMap(srcMap, mskMap, srcBand, mskBand, outputDir):

	#define output path for clipped map
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)
		print "\nNew directory created: " + outputDir

	srcMapName = os.path.splitext(os.path.basename(srcMap))[0]
	srcMapExt = os.path.splitext(os.path.basename(srcMap))[1]
	maskMapName = os.path.splitext(os.path.basename(mskMap))[0]

	clippedMapPath = os.path.join(outputDir, srcMapName + "_clippedto_" + maskMapName + srcMapExt)
	
	#define intersectMask command
	cmdArgs = [srcMap, mskMap, clippedMapPath, srcBand, mskBand]
	cmdArgsSpaces = [str(i) + " " for i in cmdArgs]
	cmd = "intersectMask {0} {1} {2} --src_band={3} --msk_band={4}".format(*cmdArgsSpaces)
	
	#call intersectMask
	print "\nClipping '" + srcMap + "' to match extent of '" + mskMap + "' ..."
	print "\n"+cmd
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	process.wait()
	print process.returncode
	
	return clippedMapPath


def main(mapPath1, mapPath2, outputDir, band1, band2, scale1, scale2, boundaryMap, metaComment):

	## check projection info & ensure it is matching

	#open maps & read projections
	projections = []
	for i in [mapPath1, mapPath2]:
		if not os.path.exists(i):
			sys.exit("\nMap path does not exist: '", mapPath1, "'")
		else:
			ds = gdal.Open(i, GA_ReadOnly)
			projections.append(ds.GetProjection())

	#if not projections[0] == projections[1]:
	#	print projections[0]
	#	print projections[1]
	#	msg = "\nMaps are not in the same projection. \
	#		   Please reproject before running compareMaps."
	#	sys.exit(msg)

	## clip maps to matching extents

	#determine source & mask maps
	if boundaryMap == 1:
		mskMap = mapPath1
		srcMap = mapPath2

		mskBand = band1
		srcBand = band2

	elif boundaryMap == 2:
		mskMap = mapPath2
		srcMap = mapPath1

		mskBand = band2
		srcBand = band1

	else:
		sys.exit("boundarymap argument can only be 1 or 2.")

	clippedMapPath = clipMap(srcMap, mskMap, srcBand, mskBand, outputDir)

	#define new maps
	if boundaryMap == 1:
		mapPath2 = clippedMapPath
	else:
		mapPath1 = clippedMapPath
		
		
	#check that maps are now of matching extents
	map1 = gdal.Open(mapPath1, GA_ReadOnly)
	map1Band = map1.GetRasterBand(band1)
	map1Data = map1Band.ReadAsArray()
	
	map2 = gdal.Open(mapPath2, GA_ReadOnly)
	map2Band = map2.GetRasterBand(band2)
	map2Data = map2Band.ReadAsArray()
	
	if not map1Data.shape == map2Data.shape:
		
		if map1Data.size > map2Data.size:
			
			srcMap = mapPath1
			mskMap = mapPath2
			
			srcBand = band1
			mskBand = band2
		
		else:
			
			srcMap = mapPath2
			mskMap = mapPath1
			
			srcBand = band2
			mskBand = band1
		
		clippedMapPath = clipMap(srcMap, mskMap, srcBand, mskBand, outputDir)
		
		#define new maps
		if mskMap == mapPath1:
			mapPath2 = clippedMapPath
		else:
			mapPath1 = clippedMapPath
			
		del map1, map1Band, map1Data, map2, map2Band, map2Data

	## generate difference image

	#read map bands as arrays
	map1 = gdal.Open(mapPath1, GA_ReadOnly)
	map1Band = map1.GetRasterBand(band1)
	map1Data = map1Band.ReadAsArray()

	map2 = gdal.Open(mapPath2, GA_ReadOnly)
	map2Band = map2.GetRasterBand(band2)
	map2Data = map2Band.ReadAsArray()

	#get difference of arrays
	print map1Data.shape
	print map2Data.shape
	diffData = (map1Data * scale1) - (map2Data * scale2)

	#get map info
	transform = map1.GetGeoTransform()
	#driver = map1.GetDriver()
	driver = gdal.GetDriverByName("ENVI")
	dt = map1Band.DataType

	#define difference map output path
	map1Name = os.path.splitext(os.path.basename(mapPath1))[0]
	map2Name = os.path.splitext(os.path.basename(mapPath2))[0]

	diffMapPath = os.path.join(outputDir, map1Name + "_minus_" + map2Name + srcMapExt)

	#save difference map w/ metadata
	saveArrayAsRaster(diffData, transform, projections[0], driver, diffMapPath, dt)
	desc = "Difference map of " + map1Name + " and " + map2Name + "."
	createMetadata(sys.argv, diffMapPath, description=desc)


	## generate a scatterplot

	#flatten array data
	x = map2Data.flatten() * scale2 
	y = map1Data.flatten() * scale1

	#plot x vs. y
	plt.scatter(x,y)
	plt.xlabel(os.path.basename(mapPath2))
	plt.ylabel(os.path.basename(mapPath1))
	#plt.show()
	
	scatter_outfile = os.path.splitext(os.path.basename(mapPath1))[0] + "_vs_" + \
					  os.path.splitext(os.path.basename(mapPath2))[0] + "_scatter.png"
	scatter_outpath = os.path.join(outputDir, scatter_outfile)
	
	#save("signal", ext="svg", close=True, verbose=True)
	plt.savefig(scatter_outpath)

if __name__ == '__main__':

	try:
		#parse arguments, use file docstring as parameter definition
		args = docopt.docopt(__doc__)

		#call main function
		main(args['<mappath1>'], args['<mappath2>'], args['<outputdir>'], int(args['--map1_band']), 
			int(args['--map2_band']), float(args['--map1_scale']), float(args['--map2_scale']),
			int(args['--boundarymap']),args['--meta'])
			
	#handle invalid options
	except docopt.DocoptExit as e:
		print e.message