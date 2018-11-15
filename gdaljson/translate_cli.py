import click
from gdaljson import VRTDataset

@click.command()
@click.argument('infile', type=click.File('r'))
@click.argument('outfile', type=click.File('wb'))
@click.option("--bandlist", "-b", type=int, multiple=True)
@click.option("--srcwin", type=click.Tuple([int,int,int,int]))
@click.option("--projwin", type=click.Tuple([float,float,float,float]))
@click.option("--height", type=int)
@click.option("--width", type=int)
@click.option("--xres", type=float)
@click.option("--yres", type=float)
@click.option("--nodata", type=float)
@click.option("--resample", type=str)
@click.option("--scale", type=click.Tuple([int,int,int,int]))

def cli(infile, outfile, bandlist, srcwin, projwin, height, width, xres, yres, nodata, resample, scale):
    vrt = VRTDataset(infile.read())
    vrt.translate(bandList=bandlist, srcWin=srcwin, projWin=projwin, height=height, width=width, xRes=xres, yRes=yres,
                  noData=nodata, resampleAlg=resample, scaleParams=scale)
    vrt.to_xml(outfile)

if __name__ == '__main__':
    cli()