from gdaljson.projection import wkt
import copy

def warp(in_vrt, dstSRS):
    workingvrt = copy.deepcopy(in_vrt)

    #Convert to warped vrt
    workingvrt.data['VRTDataset']['@subClass'] = "VRTWarpedDataset"

    if dstSRS:
        out_wkt = wkt[str(dstSRS)][0]
        workingvrt.data['VRTDataset']['SRS']['$'] = out_wkt

    return workingvrt
