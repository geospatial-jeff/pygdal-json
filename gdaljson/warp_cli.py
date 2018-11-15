import click
from gdaljson import VRTWarpedDataset


@click.command()
@click.argument("infile", type=click.File("r"), help="Input .VRT file")
@click.argument("outfile", type=click.File("wb"), help="Output .VRT file")
@click.option("--dstsrs", type=int, help="Output EPSG")
@click.option(
    "--cutline",
    type=click.Path(exists=True),
    help="Geojson file containing geojson feature in same SRS as raster")
@click.option(
    "--croptocutline",
    help="Crop the output raster's extent to that of the cutline",
    type=bool,
)
@click.option(
    "--height",
    help="Override height of output raster in # of pixels",
    type=int)
@click.option(
    "--width",
    help="Override width of output raster in # of pixels",
    type=int)
@click.option(
    "--xres",
    help="Override x-resolution of output raster",
    type=(float, int))
@click.option(
    "--yres",
    help="Override y-resolution of output raster",
    type=(float, int))
@click.option(
    "--dstalpha",
    help="Add an alpha band to the output raster",
    type=bool)
@click.option(
    "--resample",
    default="NearestNeighbor",
    help="Choose a resampling algorithm",
    type=str,
)
def cli(
        infile,
        outfile,
        dstsrs,
        cutline,
        croptocutline,
        height,
        width,
        xres,
        yres,
        dstalpha,
        resample,
):
    vrt = VRTWarpedDataset(infile.read())
    vrt.warp(
        dstSRS=dstsrs,
        clipper=cutline,
        cropToCutline=croptocutline,
        height=height,
        width=width,
        xRes=xres,
        yRes=yres,
        dstAlpha=dstalpha,
        resample=resample,
    )
    vrt.to_xml(outfile)
