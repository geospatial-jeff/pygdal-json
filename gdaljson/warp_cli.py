import click
from gdaljson import VRTWarpedDataset

@click.command()
@click.argument('infile', type=click.File('r'))
@click.argument('outfile', type=click.File('wb'))
@click.option("--dstsrs", type=int)
@click.option("--croptocutline", default=None, help="Crop the output raster's extent to that of the cutline (boolean)")
@click.option('--height', default=None, help="Override height of output raster in # of pixels (int)")
@click.option('--width', default=None, help="Override width of output raster in # of pixels (int)")
@click.option('--xres', default=None, help="Override x-resolution of output raster (float)")
@click.option('--yres', default=None, help="Override y-resolution of output raster (float)")
@click.option('--dstalpha', default=None, help="Add an alpha band to the output raster (boolean")
@click.option('--resample', default="NearestNeighbor", help="Choose a resampling algorithm (string)")

def cli(infile, outfile, dstsrs, croptocutline, height, width, xres, yres, dstalpha, resample):
    vrt = VRTWarpedDataset(infile.read())
    vrt.warp(dstSRS=dstsrs, cropToCutline=croptocutline, height=height, width=width, xRes=xres, yRes=yres,
             dstAlpha=dstalpha, resample=resample)
    vrt.to_xml(outfile)

if __name__ == '__main__':
    cli()