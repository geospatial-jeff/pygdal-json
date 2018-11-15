import click
from gdaljson import VRTWarpedDataset


@click.command()
@click.argument("infile", type=click.File("r"))
@click.argument("outfile", type=click.File("wb"))
@click.option("--dstsrs", type=int)
@click.option(
    "--croptocutline",
    help="Crop the output raster's extent to that of the cutline (boolean)",
    type=bool,
)
@click.option(
    "--height",
    help="Override height of output raster in # of pixels (int)",
    type=int)
@click.option(
    "--width",
    help="Override width of output raster in # of pixels (int)",
    type=int)
@click.option(
    "--xres",
    help="Override x-resolution of output raster (float)",
    type=(float, int))
@click.option(
    "--yres",
    help="Override y-resolution of output raster (float)",
    type=(float, int))
@click.option(
    "--dstalpha",
    help="Add an alpha band to the output raster (boolean",
    type=bool)
@click.option(
    "--resample",
    default="NearestNeighbor",
    help="Choose a resampling algorithm (string)",
    type=str,
)
def cli(
        infile,
        outfile,
        dstsrs,
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
        cropToCutline=croptocutline,
        height=height,
        width=width,
        xRes=xres,
        yRes=yres,
        dstAlpha=dstalpha,
        resample=resample,
    )
    vrt.to_xml(outfile)


if __name__ == "__main__":
    cli()
